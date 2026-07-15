"""Tests for MAWP required user inputs from graph expansion."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from tests.graph.conftest import MAWP_ROOT, mawp_gate_open_inputs


def _missing_inputs(project_root: Path, *, inputs: dict | None = None) -> list[str]:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    engine = GraphEngine()
    task_inputs = inputs if inputs is not None else mawp_gate_open_inputs()
    return engine.required_user_inputs(
        MAWP_ROOT,
        reader,
        existing_inputs=set(task_inputs.keys()),
        task_inputs=task_inputs,
    )


def test_mawp_required_inputs_include_wall_thickness_basis_in_navigation(
    project_root: Path,
) -> None:
    from engine.graph.navigation_phases import build_workflow_phased_navigation
    from engine.graph.workflow_navigation import load_workflow_navigation
    from engine.graph.assumption_checker import AssumptionEvaluation
    from models.planning import NavigationPhase

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    config = load_workflow_navigation(reader, MAWP_ROOT)
    assert "wall_thickness_basis" in config.fields_for_phase(NavigationPhase.PATH_DECISIONS)
    phased = build_workflow_phased_navigation(
        config=config,
        assumption_eval=AssumptionEvaluation(),
        expansion_eval=AssumptionEvaluation(),
        user_inputs=[],
        execution_eval=AssumptionEvaluation(),
        question_map={},
        existing_inputs=mawp_gate_open_inputs(),
    )
    path_missing = phased.phase_missing.get(NavigationPhase.PATH_DECISIONS.value) or []
    assert "wall_thickness_basis" not in path_missing


def test_mawp_geometry_mode_nps_requires_nps_before_schedule_when_gates_open(
    project_root: Path,
) -> None:
    missing = _missing_inputs(project_root)
    assert "internal_design_gage_pressure" not in missing
    assert "design_pressure" not in missing
    assert "nominal_pipe_size" in missing
    assert "pipe_schedule" not in missing
    assert "outside_diameter" not in missing
    assert "actual_wall_thickness" not in missing
    assert "basic_quality_factors_for_longitudinal_weld_joints_in_pipes_and_tubes" not in missing


def test_mawp_geometry_mode_nps_requires_schedule_after_nominal_pipe_size(
    project_root: Path,
) -> None:
    from models.input import InputSource, InputStatus
    from tests.helpers.facts import facts_from_inputs, legacy_input

    inputs = mawp_gate_open_inputs()
    inputs.update(
        facts_from_inputs(
            {
                "nominal_pipe_size": legacy_input(
                    "nominal_pipe_size",
                    "6",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            },
            task_id="mawp-schedule-after-nps",
        )
    )
    missing = _missing_inputs(project_root, inputs=inputs)
    assert "pipe_schedule" in missing
    assert "outside_diameter" not in missing
    assert "actual_wall_thickness" not in missing


def test_mawp_lookup_derived_coefficients_not_in_missing(project_root: Path) -> None:
    missing = _missing_inputs(project_root)
    assert "allowable_stress" not in missing or "material_grade" in missing


def test_mawp_direct_geometry_requires_outside_diameter_user_input(
    project_root: Path,
) -> None:
    from models.input import InputSource, InputStatus
    from tests.helpers.facts import facts_from_inputs, legacy_input

    inputs = mawp_gate_open_inputs()
    inputs.update(
        facts_from_inputs(
            {
                "outside_diameter__resolution_branch": legacy_input(
                    "outside_diameter__resolution_branch",
                    "direct_od",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            },
            task_id="mawp-direct-od",
        )
    )
    missing = _missing_inputs(project_root, inputs=inputs)
    assert "outside_diameter" in missing
    assert "nominal_pipe_size" not in missing
    assert "pipe_schedule" not in missing
