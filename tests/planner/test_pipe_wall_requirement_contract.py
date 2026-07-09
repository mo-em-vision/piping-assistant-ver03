"""Fresh pipe wall plan requirement contract: shape, legacy exclusion, classifications."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.plan_validation import validate_engineering_plan
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import LEGACY_REQUIREMENT_FIELD_NAMES
from models.task import TaskStatus
from tests.planner.helpers import _reader

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

_EXPECTED_REQUIREMENT_CLASSES = {
    req_id: (
        "user_input"
        if req_id
        in {
            "REQ-straight_pipe_section",
            "REQ-internal_design_gage_pressure",
            "REQ-diameter_resolution",
            "REQ-material_grade",
            "REQ-design_temperature",
            "REQ-corrosion_allowance",
            "REQ-pipe_construction_type",
        }
        else "branch_decision"
        if req_id == "REQ-pressure_loading"
        else "table_lookup"
        if req_id in PIPE_WALL_LOOKUP_IDS
        else "equation_result"
        if req_id in {REQ_REQUIRED_WALL_THICKNESS, REQ_MINIMUM_REQUIRED_THICKNESS_EQ}
        else "report_output"
    )
    for req_id in PIPE_WALL_CONTRACT_REQUIREMENT_IDS
}


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("req-contract-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def _fresh_plan():
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors
    return plan


def test_fresh_pipe_wall_includes_contract_requirement_ids() -> None:
    plan = _fresh_plan()
    missing = [req_id for req_id in PIPE_WALL_CONTRACT_REQUIREMENT_IDS if req_id not in plan.requirements]
    assert not missing, f"missing contract requirements: {missing}"


def test_fresh_pipe_wall_requirements_have_canonical_fields() -> None:
    plan = _fresh_plan()
    for req_id, req in plan.requirements.items():
        payload = req.to_dict()
        for field_name in _CANONICAL_REQUIREMENT_FIELDS:
            assert field_name in payload, f"{req_id} missing {field_name}"
            value = payload[field_name]
            if field_name in {"required_by", "depends_on"}:
                assert isinstance(value, list), f"{req_id}.{field_name} must be a list"
            else:
                assert value not in (None, ""), f"{req_id}.{field_name} must be populated"


def test_fresh_pipe_wall_requirements_exclude_legacy_fields() -> None:
    plan = _fresh_plan()
    for req_id, req in plan.requirements.items():
        payload = req.to_dict()
        leaked = _LEGACY_FIELDS_FORBIDDEN_ON_REQUIREMENTS.intersection(payload.keys())
        assert not leaked, f"{req_id} leaked legacy fields: {sorted(leaked)}"


def test_fresh_pipe_wall_contract_requirement_classes() -> None:
    plan = _fresh_plan()
    for req_id, expected_class in _EXPECTED_REQUIREMENT_CLASSES.items():
        req = plan.requirements[req_id]
        assert req.requirement_class == expected_class, (
            f"{req_id}: expected {expected_class}, got {req.requirement_class}"
        )
