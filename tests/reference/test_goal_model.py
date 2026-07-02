"""Tests for runtime Goal model validation per Goal Node template."""

from __future__ import annotations

import pytest

from engine.validation.goal_validator import validate_goal, validate_goal_dict
from models.goal import (
    GoalClass,
    GoalProvenance,
    GoalSatisfaction,
    GoalState,
    RequiredOutput,
    SatisfactionStatus,
    calculation_goal,
    input_goal,
    goal_to_dict,
    goal_from_dict,
    new_goal_id,
)
from models.goal_store import GoalCycleError, GoalStore


def _sample_input_goal(**overrides):
    goal = input_goal(
        key="input-design-pressure",
        name="Design pressure",
        target_parameter="design_pressure",
        task_id="TASK-test",
        prompt="Provide design pressure.",
        workflow_id="WF-pipe-wall-thickness-design",
        phase="parameter_gathering",
        order=1,
    )
    for key, value in overrides.items():
        setattr(goal, key, value)
    return goal


def test_valid_input_goal_passes() -> None:
    goal = _sample_input_goal()
    assert validate_goal(goal) == []


def test_goal_requires_param_reference() -> None:
    goal = _sample_input_goal(target_parameter="design_pressure")
    issues = validate_goal(goal)
    assert any("PARAM-*" in issue for issue in issues)


def test_goal_type_must_be_goal() -> None:
    goal = _sample_input_goal(type="fact")
    assert "type must be 'goal'" in validate_goal(goal)


def test_input_goal_requires_question() -> None:
    goal = _sample_input_goal(question=None)
    assert any("question" in issue for issue in validate_goal(goal))


def test_goal_store_link_child_and_cycle_detection() -> None:
    store = GoalStore()
    parent = calculation_goal(
        key="root",
        name="Root",
        target_parameter="required-wall-thickness",
        task_id="TASK-test",
    )
    child = input_goal(
        key="input-design-pressure",
        name="Design pressure",
        target_parameter="design_pressure",
        task_id="TASK-test",
        prompt="Provide design pressure.",
    )
    store.append_goal(parent, as_root=True)
    store.append_goal(child)
    store.link_child(parent.id, child.id)
    assert child.id in store.get(parent.id).state.child_goals
    with pytest.raises(GoalCycleError):
        store.link_child(child.id, parent.id)


def test_goal_json_round_trip() -> None:
    goal = _sample_input_goal()
    restored = goal_from_dict(goal_to_dict(goal))
    assert restored.id == goal.id
    assert restored.key == goal.key
    assert restored.goal_class == goal.goal_class


def test_validate_goal_dict_round_trip() -> None:
    goal = _sample_input_goal()
    payload = goal_to_dict(goal)
    assert validate_goal_dict(payload) == []


def test_goal_store_serialization_round_trip() -> None:
    store = GoalStore()
    root = calculation_goal(
        key="root",
        name="Verify wall thickness",
        target_parameter="required-wall-thickness",
        task_id="TASK-test",
    )
    store.append_goal(root, as_root=True)
    restored = GoalStore.from_dict(store.to_dict())
    assert list(restored.root_goal_ids) == list(store.root_goal_ids)
    assert restored.get(root.id).name == root.name
