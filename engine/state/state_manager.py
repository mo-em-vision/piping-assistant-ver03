"""Task lifecycle state management — CRUD only, no workflow logic."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from engine.reference.standards_reader import StandardsReader

from models.input import EngineeringInput, InputStatus, input_is_expansion_ready
from models.task import InputConflict, Task, TaskStatus
from models.workflow_state import WorkflowState


class TaskNotFoundError(KeyError):
    """Raised when a task_id does not exist in the manager."""


class TaskAlreadyExistsError(ValueError):
    """Raised when creating a task with a duplicate task_id."""


@dataclass
class StepProgress:
    step_id: str
    status: str
    result: Any | None = None


@dataclass
class TaskStateManager:
    """Maintains engineering task lifecycle for a single session."""

    _tasks: dict[str, Task] = field(default_factory=dict)
    _step_progress: dict[str, dict[str, StepProgress]] = field(default_factory=dict)
    _active_task_id: str | None = None

    def create_task(
        self,
        task_id: str,
        *,
        status: TaskStatus = TaskStatus.ACTIVE,
        set_active: bool = True,
    ) -> Task:
        if task_id in self._tasks:
            raise TaskAlreadyExistsError(f"Task already exists: {task_id}")

        task = Task(task_id=task_id, status=status)
        self._tasks[task_id] = task
        self._step_progress[task_id] = {}

        if set_active:
            self._active_task_id = task_id

        return task

    def get_task(self, task_id: str) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise TaskNotFoundError(f"Task not found: {task_id}") from exc

    def list_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    def list_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        return [task for task in self._tasks.values() if task.status == status]

    def get_active_task(self) -> Task | None:
        if self._active_task_id is None:
            return None
        return self._tasks.get(self._active_task_id)

    def set_active_task(self, task_id: str) -> Task:
        task = self.get_task(task_id)
        self._active_task_id = task_id
        return task

    def clear_active_task(self) -> None:
        self._active_task_id = None

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        task = self.get_task(task_id)
        task.status = status
        return task

    def pause_task(self, task_id: str) -> Task:
        return self.update_task_status(task_id, TaskStatus.PAUSED)

    def resume_task(self, task_id: str) -> Task:
        task = self.get_task(task_id)
        if task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.ACTIVE
        return task

    def complete_task(self, task_id: str) -> Task:
        return self.update_task_status(task_id, TaskStatus.COMPLETED)

    def invalidate_task(self, task_id: str) -> Task:
        return self.update_task_status(task_id, TaskStatus.INVALIDATED)

    def delete_task(self, task_id: str) -> None:
        self.get_task(task_id)
        del self._tasks[task_id]
        self._step_progress.pop(task_id, None)
        if self._active_task_id == task_id:
            self._active_task_id = None

    def set_active_nodes(self, task_id: str, active_nodes: list[str]) -> Task:
        task = self.get_task(task_id)
        task.active_nodes = list(active_nodes)
        return task

    def store_input(self, task_id: str, engineering_input: EngineeringInput) -> Task:
        task = self.get_task(task_id)
        existing = task.inputs.get(engineering_input.input_id)

        if existing is not None and existing.value != engineering_input.value:
            if (
                existing.status == InputStatus.PROPOSED_DEFAULT
                and input_is_expansion_ready(engineering_input)
            ):
                pass
            else:
                task.conflicts.append(
                    InputConflict(
                        previous_calculation_invalid=True,
                        reason="input changed",
                        input_id=engineering_input.input_id,
                        previous_value=existing.value,
                        new_value=engineering_input.value,
                    )
                )
        elif (
            existing is not None
            and existing.value == engineering_input.value
            and existing.status == InputStatus.PROPOSED_DEFAULT
            and input_is_expansion_ready(engineering_input)
        ):
            pass

        task.inputs[engineering_input.input_id] = engineering_input
        return task

    def store_parameter_registry(
        self,
        task_id: str,
        registry: dict[str, Any],
    ) -> Task:
        task = self.get_task(task_id)
        task.parameter_registry = dict(registry)
        return task

    def store_output(self, task_id: str, key: str, value: Any) -> Task:
        task = self.get_task(task_id)
        task.outputs[key] = value
        return task

    def add_warning(self, task_id: str, warning: str) -> Task:
        task = self.get_task(task_id)
        task.warnings.append(warning)
        return task

    def record_conflict(self, task_id: str, conflict: InputConflict) -> Task:
        task = self.get_task(task_id)
        task.conflicts.append(conflict)
        return task

    def store_step_progress(
        self,
        task_id: str,
        step_id: str,
        status: str,
        *,
        result: Any | None = None,
    ) -> StepProgress:
        self.get_task(task_id)
        progress = StepProgress(step_id=step_id, status=status, result=result)
        self._step_progress[task_id][step_id] = progress
        return progress

    def get_step_progress(self, task_id: str, step_id: str) -> StepProgress | None:
        self.get_task(task_id)
        return self._step_progress[task_id].get(step_id)

    def list_step_progress(self, task_id: str) -> list[StepProgress]:
        self.get_task(task_id)
        return list(self._step_progress[task_id].values())

    def get_workflow_state(
        self,
        task_id: str,
        *,
        reader: StandardsReader | None = None,
    ) -> WorkflowState:
        from engine.state.workflow_state import build_workflow_state

        task = self.get_task(task_id)
        resolved_reader = reader
        if resolved_reader is None:
            root = Path(__file__).resolve().parents[2] / "standards"
            resolved_reader = StandardsReader(root, standard="asme_b31.3")
        return build_workflow_state(
            task,
            step_progress=self.list_step_progress(task_id),
            reader=resolved_reader,
        )

    def compare_inputs(self, task_id: str, other_task_id: str) -> list[InputConflict]:
        task = self.get_task(task_id)
        other = self.get_task(other_task_id)
        conflicts: list[InputConflict] = []

        shared_keys = set(task.inputs) & set(other.inputs)
        for input_id in shared_keys:
            left = task.inputs[input_id]
            right = other.inputs[input_id]
            if left.value != right.value:
                conflicts.append(
                    InputConflict(
                        previous_calculation_invalid=True,
                        reason="input changed",
                        input_id=input_id,
                        previous_value=left.value,
                        new_value=right.value,
                    )
                )

        return conflicts

    def replace_task(self, task_id: str, task: Task) -> Task:
        if task.task_id != task_id:
            raise ValueError("task.task_id must match task_id argument")
        self.get_task(task_id)
        self._tasks[task_id] = replace(task)
        return self._tasks[task_id]
