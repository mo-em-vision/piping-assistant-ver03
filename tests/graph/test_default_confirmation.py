"""Tests for default coefficient proposal and confirmation at expansion."""

from __future__ import annotations

from pathlib import Path

from ai.user_response_extractor import (
    confirm_proposed_input,
    extract_confirmation_intent,
    extract_value_override,
    resolve_pending_value_responses,
)
from engine.graph.graph_engine import GraphEngine
from engine.graph.node_interaction import (
    InteractionMode,
    NodeInteractionSpec,
    load_node_interactions,
    propose_default_values,
    question_for_interaction,
)
from engine.planner.planner import Planner
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.agent import AgentAction, IntentResult
from models.input import EngineeringInput, InputSource, InputStatus, proposed_default_input
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.helpers.facts import fact_get_value, legacy_input
from models.fact import SourceType, ValidationStatus, fact_scalar_value
from engine.state.fact_migration import fact_from_engineering_input


def _reader() -> StandardsReader:
    project_root = Path(__file__).resolve().parents[2]
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _coefficient_spec(
    variable: str = "coefficient",
    *,
    default: float = 1.0,
    symbol: str = "C",
) -> NodeInteractionSpec:
    return NodeInteractionSpec(
        variable=variable,
        mode=InteractionMode.VALUE_RESOLUTION,
        node_id="test-node",
        sources=("user", "default"),
        default=default,
        confirmation_required=True,
        unit="dimensionless",
        symbol=symbol,
    )


def test_propose_default_values_creates_proposed_default() -> None:
    spec = _coefficient_spec(default=0.4)
    proposed = propose_default_values([spec], {})

    assert "coefficient" in proposed
    assert proposed["coefficient"].status == ValidationStatus.PENDING
    assert proposed["coefficient"].value == 0.4


def test_extract_confirmation_intent() -> None:
    assert extract_confirmation_intent("confirm")
    assert extract_confirmation_intent("yes")
    assert extract_confirmation_intent("use default")
    assert not extract_confirmation_intent("design pressure 500 psi")


def test_confirm_upgrades_proposed_default() -> None:
    spec = _coefficient_spec(symbol="E")
    proposed = proposed_default_input("weld_joint_efficiency", 1.0, unit="dimensionless")
    confirmed = confirm_proposed_input(spec, proposed)

    assert confirmed.status == ValidationStatus.CONFIRMED
    assert confirmed.value == 1.0


def test_override_stores_user_override() -> None:
    spec = _coefficient_spec(variable="weld_joint_efficiency", symbol="E", default=1.0)
    override = extract_value_override("E = 0.85", spec)

    assert override is not None
    assert override.status == InputStatus.USER_OVERRIDE
    assert override.value == 0.85


def test_resolve_confirm_for_first_pending_proposed() -> None:
    spec = _coefficient_spec(variable="weld_joint_efficiency", symbol="E", default=1.0)
    proposed = proposed_default_input("weld_joint_efficiency", 1.0, unit="dimensionless")
    resolved = resolve_pending_value_responses(
        "confirm",
        [spec],
        {"weld_joint_efficiency": proposed},
    )

    assert resolved["weld_joint_efficiency"].status == ValidationStatus.CONFIRMED


def test_no_default_remains_missing() -> None:
    spec = NodeInteractionSpec(
        variable="custom_input",
        mode=InteractionMode.VALUE_RESOLUTION,
        node_id="test-node",
        sources=("user",),
        confirmation_required=True,
    )
    proposed = propose_default_values([spec], {})

    assert proposed == {}


def test_planner_proposes_defaults_for_internal_path() -> None:
    reader = _reader()
    state = TaskStateManager()
    task = state.create_task("pipe-wall-defaults", status=TaskStatus.AWAITING_INPUT)
    state.store_input("pipe-wall-defaults", fact_from_engineering_input(straight_section_assumption(), task_id="pipe-wall-defaults"))
    state.store_input("pipe-wall-defaults", fact_from_engineering_input(internal_pressure_assumption(), task_id="pipe-wall-defaults"))
    state.store_input(
        "pipe-wall-defaults",
        fact_from_engineering_input(
            legacy_input("internal_design_gage_pressure", 500, "psi", InputSource.USER),
            task_id="pipe-wall-defaults",
        ),
    )
    state.store_input(
        "pipe-wall-defaults",
        fact_from_engineering_input(
            legacy_input(
                "outside_diameter__resolution_branch",
                "direct_od",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id="pipe-wall-defaults",
        ),
    )
    state.store_input(
        "pipe-wall-defaults",
        EngineeringInput("outside_diameter", 10, "in", InputSource.USER),
    )
    state.store_input(
        "pipe-wall-defaults",
        EngineeringInput("material", "SA-106B", "dimensionless", InputSource.USER),
    )
    state.store_input(
        "pipe-wall-defaults",
        EngineeringInput("design_temperature", 200, "F", InputSource.USER),
    )
    task = state.get_task("pipe-wall-defaults")
    planner = Planner(reader, state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    plan = planner.plan(intent, task)
    task = state.get_task("pipe-wall-defaults")

    assert "weld_joint_efficiency" not in (plan.missing_execution_assumptions or [])
    assert plan.action == AgentAction.REQUEST_INPUT
    assert plan.questions
    assert any(
        "pipe construction" in question.lower()
        or "joint" in question.lower()
        or "joint category" in question.lower()
        for question in plan.questions
    )


def test_planner_expands_after_all_defaults_confirmed() -> None:
    reader = _reader()
    state = TaskStateManager()
    task = state.create_task("pipe-wall-ready", status=TaskStatus.AWAITING_INPUT)
    state.store_input(
        "pipe-wall-ready",
        fact_from_engineering_input(straight_section_assumption(), task_id="pipe-wall-ready"),
    )
    state.store_input(
        "pipe-wall-ready",
        fact_from_engineering_input(internal_pressure_assumption(), task_id="pipe-wall-ready"),
    )
    state.store_input(
        "pipe-wall-ready",
        fact_from_engineering_input(
            legacy_input("internal_design_gage_pressure", 500, "psi", InputSource.USER),
            task_id="pipe-wall-ready",
        ),
    )
    state.store_input(
        "pipe-wall-ready",
        fact_from_engineering_input(
            legacy_input(
                "outside_diameter__resolution_branch",
                "direct_od",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id="pipe-wall-ready",
        ),
    )
    state.store_input(
        "pipe-wall-ready",
        EngineeringInput("outside_diameter", 10, "in", InputSource.USER),
    )
    state.store_input(
        "pipe-wall-ready",
        EngineeringInput("material", "SA-106B", "dimensionless", InputSource.USER),
    )
    state.store_input(
        "pipe-wall-ready",
        EngineeringInput("design_temperature", 200, "F", InputSource.USER),
    )
    state.store_input(
        "pipe-wall-ready",
        EngineeringInput(
            input_id="joint_category",
            value="seamless",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    state.store_input(
        "pipe-wall-ready",
        EngineeringInput(
            input_id="corrosion_allowance",
            value=0.5,
            unit="mm",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    planner = Planner(reader, state=state)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    first = planner.plan(intent, state.get_task("pipe-wall-ready"))
    assert first.action == AgentAction.REQUEST_INPUT

    task = state.get_task("pipe-wall-ready")
    for input_id in ("weld_joint_efficiency", "weld_joint_strength_reduction_factor_W"):
        proposed = task.fact_store.active_fact(input_id)
        state.store_input(
            "pipe-wall-ready",
            fact_from_engineering_input(
                legacy_input(
                    input_id=proposed.input_id,
                    value=fact_scalar_value(proposed),
                    unit=proposed.unit,
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
                task_id="pipe-wall-ready",
            ),
        )

    second = planner.plan(intent, state.get_task("pipe-wall-ready"))
    assert second.action == AgentAction.PROPOSE_PATH
    assert "304.1.2-a" in second.selected_nodes or "B313-eq-wall-thickness" in second.selected_nodes


def test_multiple_coefficients_require_sequential_confirmation() -> None:
    reader = _reader()
    record = reader.load("304.1.2-a")
    specs = [
        spec
        for spec in load_node_interactions(record, reader)
        if spec.mode == InteractionMode.VALUE_RESOLUTION
    ]
    inputs: dict[str, EngineeringInput] = {}
    proposed = propose_default_values(specs, inputs)
    inputs.update(proposed)

    pending = [spec for spec in specs if spec.variable in proposed]
    assert len(pending) == 2

    first = resolve_pending_value_responses("confirm", pending, inputs)
    inputs.update(first)
    assert len(first) == 1

    second = resolve_pending_value_responses("confirm", pending, inputs)
    inputs.update(second)
    assert len(second) == 1

    engine = GraphEngine()
    ready = engine.expansion_ready_nodes(
        ["304.1.2-a"],
        reader,
        existing_inputs=inputs,
    )
    assert ready == ["304.1.2-a"]


def test_proposed_default_question_includes_condition() -> None:
    spec = NodeInteractionSpec(
        variable="corrosion_allowance",
        mode=InteractionMode.VALUE_RESOLUTION,
        node_id="304.1.2-a",
        sources=("default",),
        default=0.5,
        confirmation_required=True,
        unit="mm",
        symbol="c",
        default_condition="machined surfaces or grooves where tolerance is not specified",
    )
    proposed = propose_default_values([spec], {})
    question = question_for_interaction(spec, proposed)
    assert "0.5" in question
    assert "machined" in question.lower()
    assert proposed["corrosion_allowance"].default_condition == spec.default_condition
