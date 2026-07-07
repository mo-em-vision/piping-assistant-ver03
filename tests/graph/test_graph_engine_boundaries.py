"""Graph Engine layer boundary tests."""

from __future__ import annotations

from typing import Any

import pytest

from engine.graph.graph_engine import GraphEngine
from models.execution import ExecutionPlan
from models.planning import WorkflowCandidate
from tests.graph.conftest import PIPE_WALL_ROOT, gate_open_inputs


def _collect_strings(value: Any, *, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for key, item in value.items():
            found.extend(_collect_strings(item, path=f"{path}.{key}"))
    elif isinstance(value, (list, tuple, set)):
        for index, item in enumerate(value):
            found.extend(_collect_strings(item, path=f"{path}[{index}]"))
    return found


def _assert_no_prompt_like_strings(payload: Any) -> None:
    banned_fragments = (
        "please provide",
        "please enter",
        "what is the",
        "confirm whether",
        "traversal narration",
    )
    for text in _collect_strings(payload):
        lowered = text.lower()
        if len(text) < 24:
            continue
        if any(fragment in lowered for fragment in banned_fragments):
            pytest.fail(f"Unexpected prompt-like string in graph output: {text!r}")


def test_build_plan_does_not_execute_formulas(b313_reader, graph_engine) -> None:
    plan = graph_engine.build_plan(
        task_id="no-exec",
        root_id=PIPE_WALL_ROOT,
        inputs=gate_open_inputs(task_id="no-exec"),
        reader=b313_reader,
    )
    assert isinstance(plan, ExecutionPlan)
    assert not hasattr(plan, "outputs")
    plan_dict = plan.__dict__
    assert "required_thickness" not in plan_dict
    assert "minimum_required_thickness" not in plan_dict
    assert "allowable_stress" not in plan_dict


def test_build_plan_does_not_invoke_validation(b313_reader, graph_engine, monkeypatch) -> None:
    def _fail_validate(*_args, **_kwargs):
        raise AssertionError("ValidationEngine must not be called from GraphEngine.build_plan")

    monkeypatch.setattr(
        "engine.validation.validation_engine.ValidationEngine.validate_plan",
        _fail_validate,
    )
    monkeypatch.setattr(
        "engine.validation.validation_engine.ValidationEngine.validate_node",
        _fail_validate,
    )
    graph_engine.build_plan(
        task_id="no-validation",
        root_id=PIPE_WALL_ROOT,
        inputs=gate_open_inputs(task_id="no-validation"),
        reader=b313_reader,
    )


def test_graph_engine_core_outputs_have_no_prompt_copy(b313_reader, graph_engine) -> None:
    plan = graph_engine.build_plan(
        task_id="no-prompt",
        root_id=PIPE_WALL_ROOT,
        inputs=gate_open_inputs(task_id="no-prompt"),
        reader=b313_reader,
    )
    required = graph_engine.required_user_inputs(
        PIPE_WALL_ROOT,
        b313_reader,
        task_inputs=gate_open_inputs(task_id="no-prompt"),
    )
    registry = graph_engine.seed_parameter_registry(
        PIPE_WALL_ROOT,
        b313_reader,
        existing_inputs=gate_open_inputs(task_id="no-prompt"),
    )
    candidates = graph_engine.discover_roots(b313_reader, workflow=PIPE_WALL_ROOT)

    _assert_no_prompt_like_strings(plan.nodes)
    _assert_no_prompt_like_strings(required)
    _assert_no_prompt_like_strings(
        {key: descriptor.__dict__ for key, descriptor in registry.items()}
    )
    assert all(isinstance(candidate, WorkflowCandidate) for candidate in candidates)
