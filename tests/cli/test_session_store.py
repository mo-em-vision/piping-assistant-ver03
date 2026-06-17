"""Session persistence tests."""

from __future__ import annotations

from cli.session_store import SessionStore
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource
from models.task import TaskStatus


def test_session_store_round_trips_tasks(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions", session_id="test")
    manager = TaskStateManager()
    manager.create_task("pipe-wall-thickness-design-abc123", status=TaskStatus.AWAITING_INPUT)
    manager.store_input(
        "pipe-wall-thickness-design-abc123",
        EngineeringInput(
            input_id="design_pressure",
            value=500,
            unit="psi",
            source=InputSource.USER,
        ),
    )
    store.save_state_manager(manager)

    loaded = store.load_state_manager()
    task = loaded.get_task("pipe-wall-thickness-design-abc123")
    assert task.status == TaskStatus.AWAITING_INPUT
    assert task.inputs["design_pressure"].value == 500
