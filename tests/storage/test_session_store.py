"""Session persistence tests."""

from __future__ import annotations

from storage.session_store import SessionStore
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.helpers.facts import fact_get_value, legacy_input


def test_session_store_round_trips_tasks(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions", session_id="test")
    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-design-abc123"
    manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    manager.store_input(
        task_id,
        fact_from_engineering_input(
            legacy_input("design_pressure", 500, "psi"),
            task_id=task_id,
        ),
    )
    store.save_state_manager(manager)

    loaded = store.load_state_manager()
    task = loaded.get_task(task_id)
    assert task.status == TaskStatus.AWAITING_INPUT
    assert fact_get_value(task, "design_pressure") == 500


def test_session_store_migrates_v4_stub_authority(tmp_path) -> None:
    from storage.session_store import _task_from_dict, _task_to_dict

    v4_payload = {
        "task_id": "pipe-wall-v4",
        "active_nodes": [],
        "execution_context": {
            "id": "EXEC-v4test",
            "type": "execution_context",
            "task_id": "pipe-wall-v4",
            "workflow_id": "pipe_wall_thickness_design",
            "status": "active",
            "authority_context_id": "AUTHCTX-asme-b31.3",
            "active_goals": [],
            "fact_store": {"facts": {}},
            "goal_store": {"goals": {}},
            "facts_index": {"active": [], "superseded": [], "conflicting": []},
            "state": {
                "current_phase": "ready",
                "blocked_by": [],
                "ready_goals": [],
                "blocked_goals": [],
                "completed_goals": [],
            },
            "decisions": [],
            "assumptions": [],
            "validation": {"status": "incomplete", "warnings": [], "errors": [], "overrides": []},
            "execution_trace": {"events": []},
            "warnings": [],
            "conflicts": [],
            "metadata": {"created": None, "modified": None, "version": 1},
        },
        "outputs": {"workflow": "pipe_wall_thickness_design"},
        "parameter_registry": {},
        "payload_version": 4,
    }
    task = _task_from_dict(v4_payload)
    assert task.payload_version == 5
    assert task.authority_context is not None
    assert task.authority_context.id == "AUTHCTX-asme-b31.3"
    assert task.authority_context.active_authorities[0].authority_id == "AUTH-ASME-B31.3"

    round_trip = _task_to_dict(task)
    assert round_trip["payload_version"] == 5
    assert "authority_context" in round_trip
