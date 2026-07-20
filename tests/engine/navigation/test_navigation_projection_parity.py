"""Parity tests for engine navigation projection vs pre-extraction behavior."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from api.workflow_display import task_display_title
from engine.navigation import (
    collect_all_missing,
    composer_parameter_id,
    composer_parameter_ids,
    step_applies_for_timeline,
    submittable_parameter_ids,
    timeline_step_id_for_parameter,
)
from engine.router import is_supported_planning_workflow
from engine.navigation.missing_inputs import collect_all_missing as engine_collect_all_missing
from engine.planner.goal_navigation import build_current_ask
from engine.planner.workflow_goal_metadata import workflow_display_title_from_node
from engine.reference.standards_reader import StandardsReader
from engine.router import MAWP_DESIGN, PIPE_WALL_THICKNESS_DESIGN
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from engine.state.task_state_canonical import build_canonical_task_state
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.graph.conftest import PIPE_WALL_ROOT
from tests.helpers.facts import legacy_input

_REPO_ROOT = Path(__file__).resolve().parents[3]

_COLLECT_ALL_MISSING_FIXTURE = {
    "missing_inputs": ["internal_design_gage_pressure"],
    "missing_assumptions": ["pressure_design_case"],
    "missing_execution_assumptions": ["corrosion_allowance"],
    "phase_missing": {
        "parameter_gathering": ["material_grade", "internal_design_gage_pressure"],
    },
}

_COLLECT_ALL_MISSING_EXPECTED = sorted(
    [
        "corrosion_allowance",
        "internal_design_gage_pressure",
        "material_grade",
        "pressure_design_case",
    ]
)

_FRESH_PWT_SUBMITTABLE = ["internal_design_gage_pressure"]
_NPS_BRANCH_SUBMITTABLE = ["nominal_pipe_size"]
_DIRECT_OD_SUBMITTABLE = ["internal_design_gage_pressure"]
_MAWP_FRESH_SUBMITTABLE = ["straight_pipe_section"]
_UNSUPPORTED_SUBMITTABLE = ["nominal_size"]


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _refresh(task, reader: StandardsReader) -> None:
    from api.workflow_bootstrap import refresh_task_planning

    refresh_task_planning(task, reader, propose_defaults=False)


def _pipe_wall_task(
    project_root: Path,
    *,
    task_id: str,
    extra_inputs: tuple = (),
):
    manager = TaskStateManager()
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    reader = _reader(project_root)
    for inp in (straight_section_assumption(), internal_pressure_assumption(), *extra_inputs):
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id=PIPE_WALL_ROOT,
            ),
        )
    task = manager.get_task(task.task_id)
    _refresh(task, reader)
    manager.replace_task(task.task_id, task)
    return manager, manager.get_task(task.task_id), reader


def test_collect_all_missing_matches_fixed_fixture() -> None:
    result = sorted(collect_all_missing(_COLLECT_ALL_MISSING_FIXTURE))
    assert result == _COLLECT_ALL_MISSING_EXPECTED
    assert result == sorted(engine_collect_all_missing(_COLLECT_ALL_MISSING_FIXTURE))


def test_collect_all_missing_empty_planning() -> None:
    assert collect_all_missing({}) == set()
    assert engine_collect_all_missing({}) == set()


def test_collect_all_missing_deduplicates_phase_overlap() -> None:
    planning = {
        "missing_inputs": ["material_grade"],
        "phase_missing": {"parameter_gathering": ["material_grade", "design_temperature"]},
    }
    assert collect_all_missing(planning) == {"material_grade", "design_temperature"}


def test_composer_mapping_identity_and_aliases(project_root: Path) -> None:
    manager, task, _reader = _pipe_wall_task(project_root, task_id="composer-pwt")
    assert composer_parameter_id(task, "pressure_design_case") == "pressure_design_case"
    assert composer_parameter_ids(task, ["pressure_design_case", "pressure_design_case"]) == ["pressure_design_case"]
    assert timeline_step_id_for_parameter(task, "outside_diameter") == "outside_diameter"

    task.outputs["workflow"] = MAWP_DESIGN
    assert composer_parameter_id(task, "actual_wall_thickness") == "actual_wall_thickness"

    task.outputs["workflow"] = "unknown_workflow_xyz"
    assert composer_parameter_id(task, "custom_param") == "custom_param"


def test_path_filters_pipe_wall_branches(project_root: Path) -> None:
    manager, task, _reader = _pipe_wall_task(
        project_root,
        task_id="path-nps",
        extra_inputs=(
            legacy_input(
                "outside_diameter__resolution_branch",
                "nps_lookup",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        ),
    )
    assert is_supported_planning_workflow(PIPE_WALL_ROOT)
    assert step_applies_for_timeline(task, "nominal_pipe_size") is True
    assert step_applies_for_timeline(task, "inside_diameter") is False

    _, direct_task, _ = _pipe_wall_task(
        project_root,
        task_id="path-direct-od",
        extra_inputs=(
            legacy_input(
                "outside_diameter__resolution_branch",
                "direct_od",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        ),
    )
    assert step_applies_for_timeline(direct_task, "inside_diameter") is False
    assert step_applies_for_timeline(direct_task, "outside_diameter") is True

    manager = TaskStateManager()
    unsupported = manager.create_task("path-unsupported", status=TaskStatus.AWAITING_INPUT)
    unsupported.outputs["workflow"] = "flange_selection"
    assert not is_supported_planning_workflow("flange_selection")
    assert step_applies_for_timeline(unsupported, "nominal_pipe_size") is True


def test_submittable_projection_fresh_pipe_wall(project_root: Path) -> None:
    _, task, reader = _pipe_wall_task(project_root, task_id="sub-fresh-pwt")
    planning = planning_projection(task)
    assert submittable_parameter_ids(task, planning) == _FRESH_PWT_SUBMITTABLE


def test_submittable_projection_nps_branch(project_root: Path) -> None:
    _, task, _reader = _pipe_wall_task(
        project_root,
        task_id="sub-nps",
        extra_inputs=(
            legacy_input("internal_design_gage_pressure", 8.0, "bar"),
            legacy_input(
                "outside_diameter__resolution_branch",
                "nps_lookup",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        ),
    )
    planning = planning_projection(task)
    assert submittable_parameter_ids(task, planning) == _NPS_BRANCH_SUBMITTABLE


def test_submittable_projection_direct_od_branch(project_root: Path) -> None:
    _, task, _reader = _pipe_wall_task(
        project_root,
        task_id="sub-direct-od",
        extra_inputs=(
            legacy_input(
                "outside_diameter__resolution_branch",
                "direct_od",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        ),
    )
    planning = planning_projection(task)
    assert submittable_parameter_ids(task, planning) == _DIRECT_OD_SUBMITTABLE


def test_submittable_projection_fresh_mawp(project_root: Path) -> None:
    reader = _reader(project_root)
    manager = TaskStateManager()
    task = manager.create_task("sub-mawp-fresh", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = MAWP_DESIGN
    task.outputs["selected_root"] = MAWP_DESIGN
    _refresh(task, reader)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    planning = planning_projection(task)
    assert submittable_parameter_ids(task, planning) == _MAWP_FRESH_SUBMITTABLE


def test_submittable_projection_unsupported_workflow() -> None:
    manager = TaskStateManager()
    task = manager.create_task("sub-unsupported", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "flange_selection"
    planning = {
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["nominal_size"]},
        "missing_inputs": ["nominal_size"],
    }
    assert submittable_parameter_ids(task, planning) == _UNSUPPORTED_SUBMITTABLE


def test_canonical_task_state_submittable_and_blocker_unchanged(project_root: Path) -> None:
    manager, task, reader = _pipe_wall_task(project_root, task_id="canonical-parity")
    planning = planning_projection(task)
    canonical = build_canonical_task_state(task, manager, planning=planning, reader=reader)
    progress = canonical.get("progress") or {}
    execution = canonical.get("execution") or {}
    assert progress.get("submittable_parameters") == _FRESH_PWT_SUBMITTABLE
    blocker = execution.get("current_blocker") or {}
    assert blocker.get("type") == "missing_input"
    assert blocker.get("field") == "internal_design_gage_pressure"
    ask = build_current_ask(task, planning, reader=reader)
    assert ask is not None
    assert ask.get("parameter_id") == "internal_design_gage_pressure"
    assert "internal_design_gage_pressure" in (progress.get("missing_inputs") or [])


def test_workflow_display_title_parity_pipe_wall(project_root: Path) -> None:
    reader = _reader(project_root)
    api_title = task_display_title(PIPE_WALL_THICKNESS_DESIGN, reader=reader)
    engine_title = workflow_display_title_from_node(reader, PIPE_WALL_THICKNESS_DESIGN)
    assert engine_title == "Pipe Wall Thickness Design"
    assert api_title == engine_title


def test_workflow_display_title_parity_mawp(project_root: Path) -> None:
    reader = _reader(project_root)
    api_title = task_display_title(MAWP_DESIGN, reader=reader)
    engine_title = workflow_display_title_from_node(reader, MAWP_DESIGN)
    assert engine_title == "Maximum Allowable Working Pressure (MAWP)"
    assert api_title == engine_title


def test_workflow_display_title_unknown_workflow_fallback() -> None:
    unknown = "custom_unknown_workflow"
    api_title = task_display_title(unknown)
    assert api_title == "Custom Unknown Workflow"
    assert unknown.replace("_", " ").title() == api_title


def test_navigation_import_boundary_engine_layers() -> None:
    forbidden = (
        "api.workflow_timeline",
        "api.workflow_display",
        "api.workflow_bootstrap",
        "api.workflow_execution",
    )
    violations: list[str] = []
    for relative_root in ("engine/planner", "engine/state", "engine/navigation"):
        root = _REPO_ROOT / relative_root
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            rel = path.relative_to(_REPO_ROOT).as_posix()
            for module_name in imports:
                for rule in forbidden:
                    if module_name == rule or module_name.startswith(f"{rule}."):
                        violations.append(f"{rel}: {module_name}")
    assert violations == [], "Forbidden API navigation imports:\n" + "\n".join(violations)
