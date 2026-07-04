"""Tests for generic user response extraction."""

from __future__ import annotations

from ai.user_response_extractor import (
    extract_confirmation_intent,
    extract_interaction_responses,
    extract_value_override,
    resolve_pending_value_responses,
)
from engine.graph.node_interaction import InteractionMode, NodeInteractionSpec
from models.input import InputStatus, proposed_default_input


def _pressure_loading_spec() -> NodeInteractionSpec:
    return NodeInteractionSpec(
        variable="pressure_loading",
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
    )


def test_extract_interaction_responses_internal_pressure() -> None:
    extracted = extract_interaction_responses("internal pressure", [_pressure_loading_spec()])

    assert extracted["pressure_loading"].value == "internal_pressure"
    assert extracted["pressure_loading"].status == InputStatus.CONFIRMED


def test_extract_interaction_responses_ignores_design_pressure_phrase() -> None:
    extracted = extract_interaction_responses(
        "design pressure 500 psi",
        [_pressure_loading_spec()],
    )

    assert "pressure_loading" not in extracted


def test_extract_value_override_by_symbol() -> None:
    spec = NodeInteractionSpec(
        variable="weld_joint_efficiency",
        mode=InteractionMode.VALUE_RESOLUTION,
        node_id="n1",
        symbol="E",
        default=1.0,
        confirmation_required=True,
        unit="dimensionless",
    )
    override = extract_value_override("E = 0.85", spec)

    assert override is not None
    assert override.status == InputStatus.USER_OVERRIDE


def test_resolve_pending_value_confirm() -> None:
    spec = NodeInteractionSpec(
        variable="coefficient",
        mode=InteractionMode.VALUE_RESOLUTION,
        node_id="n1",
        default=0.4,
        confirmation_required=True,
        unit="dimensionless",
    )
    proposed = proposed_default_input("coefficient", 0.4)
    resolved = resolve_pending_value_responses("yes", [spec], {"coefficient": proposed})

    assert resolved["coefficient"].status == InputStatus.CONFIRMED


def test_extract_interaction_responses_confirms_proposed_decision_default() -> None:
    spec = NodeInteractionSpec(
        variable="joint_category",
        mode=InteractionMode.DECISION,
        node_id="304.1.2-a",
        required=True,
        options=("seamless", "erw", "forging"),
        default="seamless",
        confirmation_required=True,
    )
    proposed = proposed_default_input("joint_category", "seamless")
    extracted = extract_interaction_responses(
        "confirm",
        [spec],
        existing_inputs={"joint_category": proposed},
    )

    assert extracted["joint_category"].value == "seamless"
    assert extracted["joint_category"].status == InputStatus.CONFIRMED
