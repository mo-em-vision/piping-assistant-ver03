"""Tests for declarative workflow navigation config and graph-driven phases."""

from __future__ import annotations

from engine.graph.assumption_checker import AssumptionEvaluation
from engine.graph.navigation_phases import build_workflow_phased_navigation
from engine.graph.workflow_navigation import load_workflow_navigation
from engine.reference.standards_reader import StandardsReader
from engine.validation.workflow_node_validator import validate_workflow_node
from models.planning import NavigationPhase


def test_load_navigation_from_workflow_yaml_has_no_field_lists() -> None:
    reader = StandardsReader(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    config = load_workflow_navigation(reader, "pipe_wall_thickness_design")
    assert config.assumption_gate_fields == frozenset()
    assert config.fields_for_phase(NavigationPhase.PARAMETER_GATHERING) == frozenset()
    assert config.fields_for_phase(NavigationPhase.PATH_DECISIONS) == frozenset()


def test_mawp_navigation_has_no_workflow_conditionals() -> None:
    reader = StandardsReader(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    config = load_workflow_navigation(reader, "mawp_design")
    assert config.assumption_gate_fields == frozenset()
    assert config.fields_for_phase(NavigationPhase.PATH_DECISIONS) == frozenset()


def test_phased_navigation_uses_graph_metadata_for_path_decisions() -> None:
    reader = StandardsReader(
        __import__("pathlib").Path(__file__).resolve().parents[2] / "knowledge" / "standards",
        standard="asme_b31.3",
    )
    config = load_workflow_navigation(reader, "pipe_wall_thickness_design")
    expansion_eval = AssumptionEvaluation(
        missing_fields=["straight_pipe_section", "pressure_design_case"],
    )
    phased = build_workflow_phased_navigation(
        config=config,
        assumption_eval=AssumptionEvaluation(),
        expansion_eval=expansion_eval,
        user_inputs=["internal_design_gage_pressure", "outside_diameter"],
        execution_eval=AssumptionEvaluation(),
        question_map={},
    )
    assert phased.phase_missing["expansion_assumptions"] == ["straight_pipe_section"]
    assert phased.phase_missing["path_decisions"] == ["pressure_design_case"]


def test_workflow_validator_rejects_conditionals() -> None:
    issues = validate_workflow_node(
        {
            "id": "WF-BAD",
            "type": "workflow",
            "key": "bad",
            "name": "Bad",
            "workflow_class": "design_calculation",
            "description": "bad",
            "metadata": {"status": "draft", "last_revision": "2026-07-18", "edited_by": "admin"},
            "runtime": {
                "interactions": [{"variable": "pressure_design_case", "mode": "decision"}],
                "navigation": {
                    "assumption_gate_fields": ["straight_pipe_section"],
                    "phases": {"path_decisions": ["pressure_design_case"]},
                },
            },
        }
    )
    assert any("interactions" in issue for issue in issues)
    assert any("assumption_gate_fields" in issue for issue in issues)
    assert any("path_decisions" in issue for issue in issues)
