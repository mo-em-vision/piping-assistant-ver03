"""Chat startup task-resume tests."""

from __future__ import annotations

from cli.commands.chat import resolve_incomplete_task_choice
from cli.orchestrator import ChatOrchestrator
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.agents.conftest import FakeLLMClient


def _make_manager_with_tasks(*task_ids: str) -> TaskStateManager:
    manager = TaskStateManager()
    for task_id in task_ids:
        manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT, set_active=False)
    if task_ids:
        manager.set_active_task(task_ids[0])
    return manager


def test_decline_resume_clears_active_task() -> None:
    manager = _make_manager_with_tasks("pipe-wall-thickness-desi-a4bf1f")
    incomplete = manager.list_tasks()

    prompts = iter(["no"])
    resolve_incomplete_task_choice(
        manager,
        incomplete,
        prompt_fn=lambda *args, **kwargs: next(prompts),
    )

    assert manager.get_active_task() is None
    assert manager.get_task("pipe-wall-thickness-desi-a4bf1f").status == TaskStatus.AWAITING_INPUT


def test_accept_resume_single_task_sets_active() -> None:
    manager = _make_manager_with_tasks("pipe-wall-thickness-desi-a4bf1f")
    manager.clear_active_task()
    incomplete = manager.list_tasks()

    prompts = iter(["yes"])
    resolve_incomplete_task_choice(
        manager,
        incomplete,
        prompt_fn=lambda *args, **kwargs: next(prompts),
    )

    active = manager.get_active_task()
    assert active is not None
    assert active.task_id == "pipe-wall-thickness-desi-a4bf1f"


def test_accept_resume_multiple_tasks_picks_selected_index() -> None:
    manager = _make_manager_with_tasks("task-one", "task-two")
    incomplete = manager.list_tasks()

    prompts = iter(["yes", "2"])
    resolve_incomplete_task_choice(
        manager,
        incomplete,
        prompt_fn=lambda *args, **kwargs: next(prompts),
        print_fn=lambda _message: None,
    )

    active = manager.get_active_task()
    assert active is not None
    assert active.task_id == "task-two"


def test_decline_resume_then_new_message_creates_fresh_task() -> None:
    manager = _make_manager_with_tasks("pipe-wall-thickness-desi-a4bf1f")
    old_task_id = "pipe-wall-thickness-desi-a4bf1f"
    incomplete = manager.list_tasks()

    prompts = iter(["no"])
    resolve_incomplete_task_choice(
        manager,
        incomplete,
        prompt_fn=lambda *args, **kwargs: next(prompts),
    )

    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))
    response, _ = orchestrator.handle_message("calculate pipe wall thickness")

    assert response.task_id is not None
    assert response.task_id != old_task_id
    assert manager.get_active_task() is not None
    assert manager.get_active_task().task_id == response.task_id


def test_clear_active_task_leaves_tasks_intact() -> None:
    manager = TaskStateManager()
    manager.create_task("task-a", status=TaskStatus.AWAITING_INPUT)
    manager.clear_active_task()

    assert manager.get_active_task() is None
    assert manager.get_task("task-a").status == TaskStatus.AWAITING_INPUT
