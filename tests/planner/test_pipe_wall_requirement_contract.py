"""Fresh and gates-open pipe wall plan requirement contract tests."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_validation import validate_engineering_plan
from models.engineering_plan import LEGACY_REQUIREMENT_FIELD_NAMES
from engine.planner.tools import GraphTools
from tests.planner.helpers import _reader, fresh_pipe_wall_task, gates_satisfied_pipe_wall_task

_CANONICAL_REQUIREMENT_FIELDS = (
    "id",
    "key",
    "field",
    "title",
    "requirement_class",
    "status",
    "phase",
    "required_by",
    "depends_on",
)

_LEGACY_FIELDS_FORBIDDEN_ON_REQUIREMENTS = frozenset(
    {
        "satisfaction",
        "state",
        "metadata",
        "edges",
    }
) | LEGACY_REQUIREMENT_FIELD_NAMES

from tests.planner.plan_contract import (
    PIPE_WALL_CONTRACT_REQUIREMENT_IDS,
    PIPE_WALL_LOOKUP_IDS,
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ,
    REQ_REQUIRED_WALL_THICKNESS,
)

_FRESH_GATE_REQUIREMENT_IDS = (
    "REQ-straight_pipe_section",
    "REQ-pressure_design_case",
)

_GATES_OPEN_EXPECTED_REQUIREMENT_CLASSES = {
    req_id: (
        "user_input"
        if req_id
        in {
            "REQ-internal_design_gage_pressure",
            "REQ-diameter_resolution",
            "REQ-nominal_pipe_size",
            "REQ-material_grade",
            "REQ-design_temperature",
            "REQ-pipe_construction_type",
        }
        else "table_lookup"
        if req_id in PIPE_WALL_LOOKUP_IDS or req_id == "REQ-outside_diameter_lookup"
        else "equation_result"
        if req_id in {REQ_REQUIRED_WALL_THICKNESS, REQ_MINIMUM_REQUIRED_THICKNESS_EQ}
        else "report_output"
    )
    for req_id in PIPE_WALL_CONTRACT_REQUIREMENT_IDS
}


def _fresh_plan():
    _, task = fresh_pipe_wall_task(task_id="req-contract-pwt-fresh")
    plan = build_engineering_plan(task, _reader())
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors
    return plan


def _gates_open_plan():
    _, task = gates_satisfied_pipe_wall_task(task_id="req-contract-pwt-gates")
    graph = GraphTools(_reader())
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
    )
    plan = build_engineering_plan(
        task,
        _reader(),
        preview=preview,
        existing_inputs=dict(task.fact_store.active_facts()),
    )
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors
    return plan


def test_fresh_pipe_wall_includes_gate_requirement_ids() -> None:
    plan = _fresh_plan()
    missing = [req_id for req_id in _FRESH_GATE_REQUIREMENT_IDS if req_id not in plan.requirements]
    assert not missing, f"missing fresh gate requirements: {missing}"


def test_gates_open_pipe_wall_includes_contract_requirement_ids() -> None:
    plan = _gates_open_plan()
    missing = [req_id for req_id in PIPE_WALL_CONTRACT_REQUIREMENT_IDS if req_id not in plan.requirements]
    assert not missing, f"missing contract requirements: {missing}"


def test_gates_open_requirements_have_canonical_fields() -> None:
    plan = _gates_open_plan()
    for req_id, req in plan.requirements.items():
        payload = req.to_dict()
        for field_name in _CANONICAL_REQUIREMENT_FIELDS:
            assert field_name in payload, f"{req_id} missing {field_name}"
            value = payload[field_name]
            if field_name in {"required_by", "depends_on"}:
                assert isinstance(value, list), f"{req_id}.{field_name} must be a list"
            else:
                assert value not in (None, ""), f"{req_id}.{field_name} must be populated"


def test_gates_open_requirements_exclude_legacy_fields() -> None:
    plan = _gates_open_plan()
    for req_id, req in plan.requirements.items():
        payload = req.to_dict()
        leaked = _LEGACY_FIELDS_FORBIDDEN_ON_REQUIREMENTS.intersection(payload.keys())
        assert not leaked, f"{req_id} leaked legacy fields: {sorted(leaked)}"


def test_gates_open_contract_requirement_classes() -> None:
    plan = _gates_open_plan()
    for req_id, expected_class in _GATES_OPEN_EXPECTED_REQUIREMENT_CLASSES.items():
        req = plan.requirements[req_id]
        assert req.requirement_class == expected_class, (
            f"{req_id}: expected {expected_class}, got {req.requirement_class}"
        )
