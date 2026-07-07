"""Pipe wall diameter resolution: alternatives model and direct-OD vs NPS branch paths."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.plan_phases import _askable_fields_for_phase
from engine.planner.plan_validation import validate_engineering_plan
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import RequirementAlternative
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption

_EXPECTED_DIRECT_ALT = RequirementAlternative(
    id="ALT-direct-outside-diameter",
    label="Provide outside diameter directly",
    fields=["outside_diameter"],
    resolves="outside_diameter",
    method="direct_input",
)

_EXPECTED_NPS_ALT = RequirementAlternative(
    id="ALT-nps-lookup",
    label="Provide NPS and look up outside diameter",
    fields=["nominal_pipe_size"],
    resolves="outside_diameter",
    method="lookup",
)

_DIAMETER_ROOT_BLOCKER_IDS = frozenset(
    {
        "REQ-outside_diameter",
        "REQ-nominal_pipe_size",
        "REQ-outside_diameter_lookup",
    }
)


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("diameter-alt-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def _confirmed_input(input_id: str, value, unit: str = "dimensionless") -> EngineeringInput:
    return EngineeringInput(
        input_id=input_id,
        value=value,
        unit=unit,
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )


def _build_plan(*inputs: EngineeringInput):
    manager, task = _fresh_pipe_wall_task()
    for inp in inputs:
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    task = manager.get_task(task.task_id)
    existing = dict(task.fact_store.active_facts())
    return build_pipe_wall_engineering_plan(task, existing_inputs=existing)


def _alternatives_by_id(plan) -> dict[str, RequirementAlternative]:
    diameter = plan.requirements["REQ-diameter_resolution"]
    return {alt.id: alt for alt in diameter.alternatives or []}


def test_diameter_resolution_exposes_direct_and_nps_lookup_alternatives() -> None:
    plan = _build_plan(straight_section_assumption(), internal_pressure_assumption())
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    by_id = _alternatives_by_id(plan)
    assert set(by_id) == {"ALT-direct-outside-diameter", "ALT-nps-lookup"}

    direct = by_id["ALT-direct-outside-diameter"]
    assert direct.fields == _EXPECTED_DIRECT_ALT.fields
    assert direct.resolves == _EXPECTED_DIRECT_ALT.resolves
    assert direct.method == _EXPECTED_DIRECT_ALT.method

    nps = by_id["ALT-nps-lookup"]
    assert nps.fields == _EXPECTED_NPS_ALT.fields
    assert nps.resolves == _EXPECTED_NPS_ALT.resolves
    assert nps.method == _EXPECTED_NPS_ALT.method


def test_diameter_resolution_not_dual_top_level_blockers_before_mode_selection() -> None:
    """Diameter is one parent requirement; NPS and OD lookup are not both root blockers yet."""
    plan = _build_plan(straight_section_assumption(), internal_pressure_assumption())
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    blocked = set(plan.root_goal.blocked_by)
    assert "REQ-diameter_resolution" in blocked
    assert blocked.isdisjoint(_DIAMETER_ROOT_BLOCKER_IDS)


def test_direct_od_mode_keeps_nps_chain_not_applicable_and_diameter_unresolved() -> None:
    """Runtime fact d_input_mode=direct_od matches UI direct_outside_diameter branch."""
    plan = _build_plan(
        straight_section_assumption(),
        internal_pressure_assumption(),
        _confirmed_input("d_input_mode", "direct_od"),
    )
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    nps = plan.requirements["REQ-nominal_pipe_size"]
    od_lookup = plan.requirements["REQ-outside_diameter_lookup"]
    diameter = plan.requirements["REQ-diameter_resolution"]

    assert nps.status == "not_applicable"
    assert od_lookup.status == "not_applicable"
    assert diameter.status == "missing"
    assert diameter.field == "outside_diameter"
    assert _alternatives_by_id(plan)["ALT-direct-outside-diameter"].fields == ["outside_diameter"]

    assert plan.input_strategy is not None
    assert "outside_diameter" not in plan.input_strategy.next_fields
    assert "nominal_pipe_size" not in plan.input_strategy.next_fields
    assert "REQ-nominal_pipe_size" not in plan.root_goal.blocked_by
    assert "REQ-outside_diameter_lookup" not in plan.root_goal.blocked_by
    assert "REQ-diameter_resolution" in plan.root_goal.blocked_by


def test_direct_od_mode_requires_outside_diameter_before_diameter_resolves() -> None:
    plan = _build_plan(
        straight_section_assumption(),
        internal_pressure_assumption(),
        _confirmed_input("d_input_mode", "direct_od"),
        _confirmed_input("internal_design_gage_pressure", 500, unit="psi"),
    )
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    diameter = plan.requirements["REQ-diameter_resolution"]
    assert diameter.status == "missing"

    resolved_plan = _build_plan(
        straight_section_assumption(),
        internal_pressure_assumption(),
        _confirmed_input("d_input_mode", "direct_od"),
        _confirmed_input("internal_design_gage_pressure", 500, unit="psi"),
        _confirmed_input("outside_diameter", 10.0, unit="in"),
    )
    resolved_validation = validate_engineering_plan(resolved_plan)
    assert resolved_validation.valid, resolved_validation.errors
    assert resolved_plan.requirements["REQ-diameter_resolution"].status == "resolved"


def test_nps_lookup_mode_requires_nps_and_blocks_lookup_until_nps_supplied() -> None:
    """Runtime fact d_input_mode=nps_lookup matches UI nps_lookup branch."""
    plan = _build_plan(
        straight_section_assumption(),
        internal_pressure_assumption(),
        _confirmed_input("d_input_mode", "nps_lookup"),
    )
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    nps = plan.requirements["REQ-nominal_pipe_size"]
    od_lookup = plan.requirements["REQ-outside_diameter_lookup"]
    diameter = plan.requirements["REQ-diameter_resolution"]

    assert nps.status == "missing"
    assert od_lookup.status == "blocked"
    assert diameter.status == "missing"
    assert _alternatives_by_id(plan)["ALT-nps-lookup"].fields == ["nominal_pipe_size"]

    assert plan.input_strategy is not None
    assert "outside_diameter" not in plan.input_strategy.next_fields
    assert "REQ-nominal_pipe_size" in plan.root_goal.blocked_by
    assert "REQ-outside_diameter_lookup" in plan.root_goal.blocked_by


def test_nps_lookup_mode_does_not_require_direct_outside_diameter_user_input() -> None:
    plan = _build_plan(
        straight_section_assumption(),
        internal_pressure_assumption(),
        _confirmed_input("d_input_mode", "nps_lookup"),
        _confirmed_input("internal_design_gage_pressure", 500, unit="psi"),
    )
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    assert plan.input_strategy is not None
    assert "outside_diameter" not in plan.input_strategy.next_fields

    parameter_gathering_askable = [
        field for _, field in _askable_fields_for_phase(plan.requirements, "parameter_gathering")
    ]
    assert "outside_diameter" not in parameter_gathering_askable

    direct_od_user_inputs = [
        req
        for req in plan.requirements.values()
        if req.requirement_class == "user_input"
        and req.field == "outside_diameter"
        and req.id != "REQ-diameter_resolution"
    ]
    assert not direct_od_user_inputs
