"""Tests for generic node interaction requirements."""

from __future__ import annotations

from pathlib import Path

from engine.graph.node_interaction import (
    InteractionMode,
    NodeInteractionSpec,
    collect_root_interactions,
    evaluate_pending_interactions,
    extract_decision_responses,
    interaction_input_from_response,
    is_interaction_satisfied,
    load_node_interactions,
    match_decision_in_message,
    parse_interactions,
    resolve_interaction_value,
)
from engine.reference.standards_reader import StandardsReader
from models.input import EngineeringInput, InputSource, InputStatus


def _pressure_design_case_spec() -> NodeInteractionSpec:
    return NodeInteractionSpec(
        variable="pressure_design_case",
        mode=InteractionMode.DECISION,
        node_id="pipe_wall_thickness_design",
        required=True,
        options=("internal_pressure", "external_pressure"),
        aliases=(
            ("internal", "internal_pressure"),
            ("internal pressure", "internal_pressure"),
            ("external", "external_pressure"),
            ("external pressure", "external_pressure"),
        ),
        confirmation_required=True,
        question=(
            "Is the pipe subjected to internal or external pressure? "
            "Internal design uses §304.1.1; external design uses §304.3."
        ),
    )


def test_parse_interactions_from_metadata() -> None:
    metadata = {
        "interactions": [
            {
                "variable": "load_case",
                "mode": "decision",
                "options": ["a", "b"],
                "question": "Choose load case",
            }
        ]
    }
    specs = parse_interactions(metadata, "test-node")

    assert len(specs) == 1
    assert specs[0].variable == "load_case"
    assert specs[0].mode == InteractionMode.DECISION
    assert specs[0].options == ("a", "b")


def test_match_decision_internal_pressure() -> None:
    spec = _pressure_design_case_spec()

    assert match_decision_in_message("internal pressure", spec) == "internal_pressure"
    assert match_decision_in_message("internal", spec) == "internal_pressure"
    assert match_decision_in_message("external pressure", spec) == "external_pressure"


def test_ambiguous_decision_returns_none() -> None:
    spec = _pressure_design_case_spec()

    assert match_decision_in_message("internal and external pressure", spec) is None


def test_design_pressure_phrase_does_not_match_pressure_design_case() -> None:
    spec = _pressure_design_case_spec()

    assert match_decision_in_message("design pressure 500 psi", spec) is None


def test_resolve_interaction_value_validates_options() -> None:
    spec = _pressure_design_case_spec()

    assert resolve_interaction_value(spec, "internal") == "internal_pressure"
    assert resolve_interaction_value(spec, "invalid_case") is None


def test_evaluate_pending_interactions_missing_decision() -> None:
    spec = _pressure_design_case_spec()
    result = evaluate_pending_interactions([spec], {}, phase="expansion")

    assert result.missing_fields == ["pressure_design_case"]
    assert "internal or external" in result.field_questions["pressure_design_case"].lower()


def test_evaluate_pending_interactions_satisfied_when_confirmed() -> None:
    spec = _pressure_design_case_spec()
    inputs = {
        "pressure_design_case": EngineeringInput(
            input_id="pressure_design_case",
            value="internal_pressure",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        )
    }
    result = evaluate_pending_interactions([spec], inputs, phase="expansion")

    assert not result.missing_fields


def test_interaction_input_from_response_is_confirmed() -> None:
    spec = _pressure_design_case_spec()
    inp = interaction_input_from_response(spec, "internal_pressure", task_id="test-task")

    assert inp.status == InputStatus.CONFIRMED
    assert inp.value == "internal_pressure"


def test_param_declares_pressure_design_case_path_decision() -> None:
    from engine.reference.parameter_keys import load_parameter_node_metadata
    from engine.reference.parameter_metadata import is_path_decision_parameter

    metadata = load_parameter_node_metadata("PARAM-pressure-design-case")
    assert is_path_decision_parameter(metadata)
    nested = metadata.get("metadata") if isinstance(metadata.get("metadata"), dict) else metadata
    options = [
        str(item.get("value"))
        for item in (nested.get("composer_options") or [])
        if isinstance(item, dict)
    ]
    assert "internal_pressure" in options
    assert "external_pressure" in options


def test_extract_decision_responses_from_message() -> None:
    spec = _pressure_design_case_spec()
    responses = extract_decision_responses("internal pressure", [spec])

    assert responses["pressure_design_case"] == "internal_pressure"


def test_load_node_interactions_bridges_confirmation_inputs() -> None:
    project_root = Path(__file__).resolve().parents[2]
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    record = reader.load("304.1.1-b")
    specs = load_node_interactions(record, reader)
    variables = {spec.variable for spec in specs}

    assert "weld_joint_efficiency" in variables
    assert any(
        spec.variable == "weld_joint_efficiency"
        and spec.mode == InteractionMode.VALUE_RESOLUTION
        for spec in specs
    )


def test_is_interaction_satisfied_requires_confirmation() -> None:
    spec = NodeInteractionSpec(
        variable="coefficient",
        mode=InteractionMode.VALUE_RESOLUTION,
        node_id="n1",
        confirmation_required=True,
        default=0.4,
    )
    inputs = {
        "coefficient": EngineeringInput(
            input_id="coefficient",
            value=0.4,
            unit="dimensionless",
            source=InputSource.DEFAULT,
            status=InputStatus.PENDING,
        )
    }

    assert not is_interaction_satisfied(spec, inputs)

    inputs["coefficient"].status = InputStatus.CONFIRMED
    assert is_interaction_satisfied(spec, inputs)
