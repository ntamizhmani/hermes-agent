"""A chat session may name its own kanban home (the office's board root). The home is validated and stored
on the session policy like client_env, so a later turn reads the same home; a relative path is refused."""
import json
from types import SimpleNamespace

import pytest

_CONFIG = 'platform_toolsets: {cli: []}\nmodel: {provider: custom, default: m, base_url: http://x.invalid/v1}\n'


async def _owner(home, monkeypatch):
    from gateway import run
    from gateway.config import GatewayConfig
    from gateway.session import SessionStore
    from gateway.session_authority import initialize_session_authority
    from gateway.session_controls import AuthorityConnection
    monkeypatch.setattr(run, '_hermes_home', home)
    monkeypatch.setenv('HERMES_HOME', str(home))
    store = SessionStore(home / 'sessions', GatewayConfig())
    runner = SimpleNamespace(session_store=store, _session_db=store._db, adapters={}, _draining=False,
                             _cached_agent_for=lambda route: None, _adapter_for_source=lambda source: None,
                             _evict_cached_agent=lambda route: None)
    owner = await initialize_session_authority(runner, profile_id=str(home), instance_id='fixture')
    return owner, AuthorityConnection(owner, object(), {'user_id': 'owner'})


def _home(tmp_path):
    home = tmp_path / 'home'
    home.mkdir()
    (home / 'config.yaml').write_text(_CONFIG)
    return home


def _create(owner, actor, home, request_id, **extra):
    from gateway.session_local import create_local_session
    from gateway.session_policy import restore_policy
    from hermes_state_local import local_receipt
    ref = create_local_session(owner, actor, {'request_id': request_id, 'source': 'cli', 'cwd': str(home),
                                              'toolsets': [], **extra}, client_local=True)
    return ref, restore_policy(local_receipt(owner.db, ref.session_id)['policy'])


@pytest.mark.asyncio
async def test_a_session_stores_its_kanban_home_and_refuses_a_relative_one(tmp_path, monkeypatch):
    from hermes_state_runtime import RuntimeStoreError
    home = _home(tmp_path)
    owner, connection = await _owner(home, monkeypatch)
    office = tmp_path / 'office-hermes'
    try:
        _, policy = _create(owner, connection.actor, home, 'k1', kanban_home=str(office))
        assert policy.kanban_home == str(office)
        with pytest.raises(RuntimeStoreError) as exc:
            _create(owner, connection.actor, home, 'k2', kanban_home='relative/path')
        assert exc.value.reason == 'invalid_params'
    finally:
        await connection.close()
        owner.db.close()


@pytest.mark.asyncio
async def test_a_session_without_a_kanban_home_stores_none(tmp_path, monkeypatch):
    home = _home(tmp_path)
    owner, connection = await _owner(home, monkeypatch)
    try:
        _, policy = _create(owner, connection.actor, home, 'k3')
        assert policy.kanban_home is None
    finally:
        await connection.close()
        owner.db.close()
