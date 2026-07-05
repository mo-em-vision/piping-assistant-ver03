"""Tests for declarative workflow navigation config."""

from __future__ import annotations

from engine.graph.navigation_phases import build_workflow_phased_navigation
from engine.graph.workflow_navigation import load_workflow_navigation
from engine.graph.assumption_checker import AssumptionEvaluation
from engine.reference.standards_reader import StandardsReader
from models.planning import NavigationPhase


def test_load_navigation_from_workflow_yaml() -> None:
    reader = StandardsReader(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    config = load_workflow_navigation(reader, "pipe_wall_thickness_design")
    assert "design_pressure" in config.fields_for_phase(NavigationPhase.PARAMETER_GATHERING)
    assert "pressure_loading" in config.assumption_gate_fields


def test_mawp_navigation_geometry_mode_in_path_decisions() -> None:
    reader = StandardsReader(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    config = load_workflow_navigation(reader, "mawp_design")
    assert "geometry_input_mode" in config.fields_for_phase(NavigationPhase.PATH_DECISIONS)
    assert "pressure_loading" not in config.fields_for_phase(NavigationPhase.PATH_DECISIONS)


def test_phased_navigation_uses_config_order() -> None:
    reader = StandardsReader(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    config = load_workflow_navigation(reader, "pipe_wall_thickness_design")
    phased = build_workflow_phased_navigation(
        config=config,
        assumption_eval=AssumptionEvaluation(),
        expansion_eval=AssumptionEvaluation(),
        user_inputs=["outside_diameter", "design_pressure"],
        execution_eval=AssumptionEvaluation(),
        question_map={},
    )
    gathering = phased.phase_missing[NavigationPhase.PARAMETER_GATHERING.value]
    assert gathering.index("design_pressure") < gathering.index("outside_diameter")


def test_phase_allowlists_serializable() -> None:
    reader = StandardsReader(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    config = load_workflow_navigation(reader, "mawp_design")
    allowlists = config.phase_allowlists()
    assert isinstance(allowlists["parameter_gathering"], list)
    assert "nominal_pipe_size" in allowlists["parameter_gathering"]
