"""A session can carry its own kanban home (the office sidecar's board root). ``kanban_home()`` reads the
session's value first, then HERMES_KANBAN_HOME, then the default; a session that sets nothing is unchanged."""
from pathlib import Path

import pytest

from hermes_cli import kanban_db as kb


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("HERMES_KANBAN_HOME", raising=False)


def test_a_bound_session_home_wins_over_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path / "env"))
    with kb.bound_kanban_home(tmp_path / "office"):
        assert kb.kanban_home() == tmp_path / "office"


def test_outside_a_session_the_environment_still_decides(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path / "env"))
    assert kb.kanban_home() == tmp_path / "env"


def test_with_nothing_set_the_default_root_is_used(monkeypatch):
    from hermes_constants import get_default_hermes_root
    assert kb.kanban_home() == get_default_hermes_root()


def test_the_binding_ends_with_its_scope(tmp_path):
    with kb.bound_kanban_home(tmp_path / "office"):
        pass
    assert kb.kanban_home() != tmp_path / "office"
