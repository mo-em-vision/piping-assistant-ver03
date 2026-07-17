"""Tests for engine-owned planning refresh entry point."""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from typing import Any

import pytest

from api.workflow_bootstrap import _finalize_planning_state, refresh_task_planning
from api.workflow_timeline import submittable_parameter_ids
from engine.planning.planning_refresh import refresh_task_planning_state
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from models.input import InputSource, InputStatus
from models.task import Task, TaskStatus
from storage.session_store import _task_from_dict, _task_to_dict
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from models.fact import fact_scalar_value
from tests.helpers.facts import legacy_input, set_fact_from_input

_PLANNING_OUTPUT_KEYS = (
    "selected_nodes",
    "path_decision",
    "active_definition_node",
    "phase_allowed_fields",
    "planning_structure_signature",
    "engineering_plan",
)

_DEPRECATED_NAVIGATION_CACHE_KEYS = (
    "engineering_plan_view",
    "graph_navigation",
    "planner_inspector_summary",
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENGINE_PLANNING_ROOT = _REPO_ROOT / "engine" / "planning"


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _clone_task(task: Task) -> Task:
    return _task_from_dict(_task_to_dict(task))


def _pipe_wall_task(project_root: Path, *, task_id: str = "planning-refresh-entry") -> tuple[TaskStateManager, Task, StandardsReader]:
    manager = TaskStateManager()
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    reader = _reader(project_root)
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        set_fact_from_input(task, inp)
    return manager, task, reader


def _run_engine_refresh(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
    allow_lightweight_refresh: bool = True,
) -> None:
    ctx = refresh_task_planning_state(
        task,
        reader,
        propose_defaults=propose_defaults,
        allow_lightweight_refresh=allow_lightweight_refresh,
    )
    if ctx is not None:
        _finalize_planning_state(
            task,
            reader,
            workflow_id=ctx.workflow_id,
            root_slug=ctx.root_slug,
            preview=ctx.preview,
            graph=ctx.graph,
            engine=ctx.engine,
            active_nodes=ctx.active_nodes,
            uses_micro=ctx.uses_micro,
        )


def _run_api_refresh(
    task: Task,
    reader: StandardsReader,
    *,
    propose_defaults: bool = True,
    allow_lightweight_refresh: bool = True,
) -> None:
    refresh_task_planning(
        task,
        reader,
        propose_defaults=propose_defaults,
        allow_lightweight_refresh=allow_lightweight_refresh,
    )


_ISO_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


def _normalize_planning_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"plan_id", "traversal_id"}:
                continue
            if key == "timestamp" and isinstance(item, str) and _ISO_TIMESTAMP_RE.match(item):
                continue
            normalized[key] = _normalize_planning_value(item)
        return normalized
    if isinstance(value, list):
        return [_normalize_planning_value(item) for item in value]
    return value


def _normalize_engineering_plan(plan: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(plan, dict):
        return plan
    return _normalize_planning_value(plan)


def _goal_store_snapshot(task: Task) -> list[dict[str, Any]]:
    roots = task.goal_store.roots()
    root_id = roots[0].id if roots else None
    children = task.goal_store.children(root_id) if root_id else []
    ordered = list(children)
    snapshot: list[dict[str, Any]] = []
    for index, goal in enumerate(ordered):
        snapshot.append(
            {
                "id": goal.id,
                "parent_goal": goal.state.parent_goal,
                "status": goal.satisfaction.status.value,
                "order": goal.metadata.get("order", index),
            }
        )
    return snapshot


def _planning_owned_snapshot(task: Task) -> dict[str, Any]:
    outputs = task.outputs
    return {
        "selected_nodes": list(outputs.get("selected_nodes") or []),
        "path_decision": outputs.get("path_decision"),
        "active_definition_node": outputs.get("active_definition_node"),
        "phase_allowed_fields": outputs.get("phase_allowed_fields"),
        "planning_structure_signature": outputs.get("planning_structure_signature"),
        "engineering_plan": _normalize_engineering_plan(outputs.get("engineering_plan")),
        "active_nodes": list(task.active_nodes),
        "goal_store": _goal_store_snapshot(task),
    }


def _assert_navigation_caches_not_persisted(task: Task) -> None:
    for key in _DEPRECATED_NAVIGATION_CACHE_KEYS:
        assert key not in task.outputs, f"deprecated cache {key!r} must not be persisted"


def _facts_snapshot(task: Task) -> dict[str, Any]:
    return {
        key: fact_scalar_value(fact)
        for key, fact in sorted(task.fact_store.active_facts().items())
    }


def test_api_wrapper_and_engine_entry_planning_parity(project_root: Path) -> None:
    _, base_task, reader = _pipe_wall_task(project_root)
    engine_task = _clone_task(base_task)
    api_task = _clone_task(base_task)

    _run_engine_refresh(engine_task, reader, propose_defaults=False, allow_lightweight_refresh=False)
    _run_api_refresh(api_task, reader, propose_defaults=False, allow_lightweight_refresh=False)

    _assert_navigation_caches_not_persisted(engine_task)
    _assert_navigation_caches_not_persisted(api_task)
    assert _planning_owned_snapshot(engine_task) == _planning_owned_snapshot(api_task)


def test_lightweight_refresh_parity(project_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _, base_task, reader = _pipe_wall_task(project_root)

    seed_task = _clone_task(base_task)
    _run_api_refresh(seed_task, reader, propose_defaults=False, allow_lightweight_refresh=False)
    signature = seed_task.outputs.get("planning_structure_signature")
    assert isinstance(signature, dict)

    engine_task = _clone_task(seed_task)
    api_task = _clone_task(seed_task)

    engine_calls: list[int] = []
    api_calls: list[int] = []
    import engine.planner.goal_builder as goal_builder

    original_refresh = goal_builder.refresh_goal_tree

    def track_engine(*args, **kwargs):
        engine_calls.append(1)
        return original_refresh(*args, **kwargs)

    def track_api(*args, **kwargs):
        api_calls.append(1)
        return original_refresh(*args, **kwargs)

    monkeypatch.setattr(
        "engine.planning.planning_refresh.refresh_goal_tree",
        track_engine,
    )
    _run_engine_refresh(engine_task, reader, propose_defaults=False, allow_lightweight_refresh=True)

    monkeypatch.setattr(
        "engine.planning.planning_refresh.refresh_goal_tree",
        track_api,
    )
    _run_api_refresh(api_task, reader, propose_defaults=False, allow_lightweight_refresh=True)

    assert engine_calls == []
    assert api_calls == []
    assert _planning_owned_snapshot(engine_task) == _planning_owned_snapshot(api_task)


def test_proposed_default_parity(project_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("planning-refresh-propose", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    reader = _reader(project_root)
    set_fact_from_input(task, straight_section_assumption())
    set_fact_from_input(task, internal_pressure_assumption())
    set_fact_from_input(task, legacy_input("internal_design_gage_pressure", 8.0, "bar"))

    engine_task = _clone_task(task)
    api_task = _clone_task(task)

    _run_engine_refresh(engine_task, reader, propose_defaults=True, allow_lightweight_refresh=True)
    _run_api_refresh(api_task, reader, propose_defaults=True, allow_lightweight_refresh=True)

    assert _facts_snapshot(engine_task) == _facts_snapshot(api_task)
    assert _planning_owned_snapshot(engine_task) == _planning_owned_snapshot(api_task)


def test_engine_planning_module_has_no_api_imports() -> None:
    violations: list[str] = []
    for path in sorted(_ENGINE_PLANNING_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(_REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "api" or alias.name.startswith("api."):
                        violations.append(f"{rel}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "api" or node.module.startswith("api.")):
                    violations.append(f"{rel}: from {node.module}")
    assert violations == []


def test_planning_refresh_state_has_no_submittable_callback() -> None:
    signature = inspect.signature(refresh_task_planning_state)
    assert "resolve_submittable_fields" not in signature.parameters


def _iter_output_values(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _iter_output_values(item)
    elif isinstance(value, (list, tuple, set)):
        yield value
        for item in value:
            yield from _iter_output_values(item)
    else:
        yield value


def _assert_no_runtime_dependencies_in_outputs(task: Task) -> None:
    for value in _iter_output_values(task.outputs):
        assert not callable(value), f"callable found in task.outputs: {value!r}"


def test_planning_refresh_does_not_store_runtime_dependencies_in_task_outputs(
    project_root: Path,
) -> None:
    _, base_task, reader = _pipe_wall_task(project_root)
    engine_task = _clone_task(base_task)
    api_task = _clone_task(base_task)

    _run_engine_refresh(engine_task, reader, propose_defaults=False, allow_lightweight_refresh=False)
    _run_api_refresh(api_task, reader, propose_defaults=False, allow_lightweight_refresh=False)

    _assert_no_runtime_dependencies_in_outputs(engine_task)
    _assert_no_runtime_dependencies_in_outputs(api_task)

    restored_engine = _task_from_dict(_task_to_dict(engine_task))
    restored_api = _task_from_dict(_task_to_dict(api_task))
    assert restored_engine.task_id == engine_task.task_id
    assert restored_api.task_id == api_task.task_id
    _assert_no_runtime_dependencies_in_outputs(restored_engine)
    _assert_no_runtime_dependencies_in_outputs(restored_api)
