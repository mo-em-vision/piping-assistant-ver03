"""Tests for parameter definitions and input submission."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.parameter_definitions import build_parameter_definitions, submit_task_input
from engine.state.goal_projection import planning_projection
from tests.helpers.facts import fact_get_value, legacy_input, set_fact_from_input
from tests.helpers.goals import task_with_planning
from models.fact import SourceType, ValidationStatus, fact_unit


@pytest.fixture(scope="module")
def standards_root() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge" / "standards"


def test_build_parameter_definitions_includes_revealed_pipe_wall_inputs(project_root: Path) -> None:
    from api.workflow_bootstrap import refresh_task_planning
    from engine.planner.plan_selection import planner_next_field_from_task
    from engine.reference.standards_reader import StandardsReader
    from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
    from tests.graph.conftest import PIPE_WALL_ROOT

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test07", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = PIPE_WALL_ROOT
    task.outputs["selected_root"] = PIPE_WALL_ROOT
    set_fact_from_input(task, legacy_input(input_id="material",
        value="SA-106B",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        set_fact_from_input(task, inp)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)
    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)

    planner_next = planner_next_field_from_task(task)
    assert planner_next is not None

    parameters = build_parameter_definitions(task, reader=reader)
    names = [item["name"] for item in parameters]
    assert names == [planner_next]
    assert parameters[0]["status"] == "pending"


def test_build_parameter_definitions_from_missing_inputs(standards_root: Path) -> None:
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(standards_root, standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test03", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["internal_design_gage_pressure", "material"],
        "missing_assumptions": ["pressure_design_case"],
        "current_phase": "path_decisions",
        "phase_missing": {"path_decisions": ["pressure_design_case"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    parameters = build_parameter_definitions(manager.get_task(task.task_id), reader=reader)
    names = [item["name"] for item in parameters]
    assert "pressure_design_case" in names

    pressure = next(item for item in parameters if item["name"] == "pressure_design_case")
    assert pressure["type"] == "dropdown"
    assert pressure["status"] == "pending"
    assert pressure["submittable"] is True


def test_build_parameter_definitions_includes_expansion_phase_guidance() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-guidance", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_assumptions": ["pressure_design_case"],
        "current_phase": "path_decisions",
        "phase_missing": {"path_decisions": ["pressure_design_case"]},
        "phase_questions": {
            "path_decisions": {
                "pressure_design_case": "Is the pipe subject to internal or external pressure?",
            }
        },
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    parameters = build_parameter_definitions(manager.get_task(task.task_id))
    pressure = next(item for item in parameters if item["name"] == "pressure_design_case")
    assert pressure["guidance"] == "Is the pipe subject to internal or external pressure?"


def test_build_parameter_definitions_marks_only_submittable_fields() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test08", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(task, legacy_input(input_id="pipe_construction_type",
        value="seamless",
        unit="dimensionless",
        source=InputSource.DEFAULT,
        status=InputStatus.PROPOSED_DEFAULT,
        default="seamless",
        requires_confirmation=True,))
    planning = {
        "current_phase": "parameter_gathering",
        "phase_missing": {
            "parameter_gathering": ["internal_design_gage_pressure"],
        },
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    parameters = {item["name"]: item for item in build_parameter_definitions(manager.get_task(task.task_id))}
    assert parameters["internal_design_gage_pressure"]["submittable"] is True
    assert parameters["pipe_construction_type"]["submittable"] is False


def test_submit_task_input_stores_confirmed_value() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test04", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["internal_design_gage_pressure"],
        "missing_assumptions": [],
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    updated = submit_task_input(
        manager,
        task.task_id,
        parameter="internal_design_gage_pressure",
        value=10.0,
        unit="bar",
    )

    stored = updated.fact_store.active_fact("internal_design_gage_pressure")
    assert stored is not None
    assert fact_get_value(updated, "internal_design_gage_pressure") == 10.0
    assert fact_unit(stored) == "bar"
    planning = planning_projection(updated)
    assert "internal_design_gage_pressure" not in planning["missing_inputs"]


def test_submit_task_input_rejects_unknown_parameter() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test05", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(
        task,
        {"missing_inputs": [], "missing_assumptions": []},
        workflow_id="pipe_wall_thickness_design",
    )
    manager.replace_task(task.task_id, task)

    try:
        submit_task_input(
            manager,
            task.task_id,
            parameter="unknown_parameter",
            value=1,
            unit=None,
        )
    except ValueError as exc:
        assert "not currently requested" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown parameter")


def test_build_parameter_definitions_includes_corrosion_after_calc_with_graph_root_workflow() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test11", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(task, legacy_input(input_id="pressure_design_case",
        value="internal_pressure",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="material",
        value="SA-106B",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="internal_design_gage_pressure",
        value=8.0,
        unit="bar",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    planning = {
        "current_phase": "definition_equation_completion",
        "missing_inputs": [],
        "missing_assumptions": [],
        "missing_execution_assumptions": ["corrosion_allowance"],
        "phase_missing": {"definition_equation_completion": ["corrosion_allowance"]},
    }
    task.outputs = {
        "workflow": "B313-PIPE-WALL-THICKNESS-DESIGN",
        "graph_root": "B313-PIPE-WALL-THICKNESS-DESIGN",
        "required_thickness": 0.084,
        "t": 0.084,
        "_execution_trace": [{"node_id": "304.1.2-a", "trace": {"calculation": {"steps": []}}}],
    }
    task_with_planning(task, planning, workflow_id="B313-PIPE-WALL-THICKNESS-DESIGN")
    manager.replace_task(task.task_id, task)

    parameters = build_parameter_definitions(manager.get_task(task.task_id))
    names = [item["name"] for item in parameters]

    assert "corrosion_allowance" in names
    corrosion = next(item for item in parameters if item["name"] == "corrosion_allowance")
    assert corrosion["status"] == "pending"
    assert corrosion["submittable"] is True
    assert len(names) > 1


def test_build_parameter_definitions_material_timeline_row_submittable_when_grade_asked(
    standards_root: Path,
) -> None:
    from engine.reference.standards_reader import StandardsReader
    from tests.helpers.facts import set_fact

    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-material-submittable", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["material_grade"],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["material_grade"]},
        "phase_questions": {
            "parameter_gathering": {
                "material_grade": "Select the pipe material. (start typing to see the available options)",
            }
        },
        "phase_allowed_fields": {
            "parameter_gathering": [
                "internal_design_gage_pressure",
                "nominal_pipe_size",
                "outside_diameter",
                "material_grade",
                "design_temperature",
            ],
        },
        "collection_field_order": [
            "internal_design_gage_pressure",
            "nominal_pipe_size",
            "outside_diameter",
            "material_grade",
            "design_temperature",
        ],
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "phase_allowed_fields": planning["phase_allowed_fields"],
        "collection_field_order": planning["collection_field_order"],
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    set_fact(task, "internal_design_gage_pressure", 10.0, unit="bar")
    set_fact(task, "nominal_pipe_size", 2, unit="NPS")
    set_fact(task, "outside_diameter", 60.33, unit="mm")
    manager.replace_task(task.task_id, task)

    reader = StandardsReader(standards_root, standard="asme_b31.3")
    parameters = {
        item["name"]: item
        for item in build_parameter_definitions(manager.get_task(task.task_id), reader=reader)
    }

    assert "material_grade" in parameters
    assert "material" not in parameters
    assert parameters["material_grade"]["status"] == "pending"
    assert parameters["material_grade"]["submittable"] is True


def test_build_parameter_definitions_material_grade_uses_material_type(
    standards_root: Path,
) -> None:
    from engine.reference.parameter_composer_spec import build_composer_parameter_spec
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(standards_root, standard="asme_b31.3")
    spec = build_composer_parameter_spec("material_grade", reader=reader)
    assert spec["type"] == "material"
    assert spec["label"] == "Material Grade"


def test_submit_task_input_rejects_unknown_material(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-material-invalid", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["material"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["material"]},
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "edit_session": {"parameter": "material"},
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    with pytest.raises(ValueError, match="Select a material from the available options"):
        submit_task_input(
            manager,
            task.task_id,
            parameter="material",
            value="not-a-real-material-grade",
            unit=None,
            standards_root=standards_root,
        )


def test_submit_task_input_rejects_unknown_material_grade(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-material-grade-invalid", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["material_grade"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["material_grade"]},
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "edit_session": {"parameter": "material_grade"},
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    with pytest.raises(ValueError, match="Select a material from the available options"):
        submit_task_input(
            manager,
            task.task_id,
            parameter="material_grade",
            value="not-a-real-material-grade",
            unit=None,
            standards_root=standards_root,
        )


def test_submit_task_input_resolves_catalog_material(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-material-valid", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["material"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["material"]},
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "edit_session": {"parameter": "material"},
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    updated = submit_task_input(
        manager,
        task.task_id,
        parameter="material",
        value="SA-106B",
        unit=None,
        standards_root=standards_root,
    )

    assert fact_get_value(updated, "material_grade") == "astm_a106_gr_b"
    assert fact_get_value(updated, "metallurgical_group") == "ferritic_steels"


def test_submit_task_input_resolves_legacy_material_alias(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-material-legacy", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["material"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["material"]},
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "edit_session": {"parameter": "material"},
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    updated = submit_task_input(
        manager,
        task.task_id,
        parameter="material",
        value="SA-106B",
        unit=None,
        standards_root=standards_root,
    )

    assert fact_get_value(updated, "material_grade") == "astm_a106_gr_b"
    assert fact_get_value(updated, "metallurgical_group") == "ferritic_steels"


def test_submit_task_input_resolves_catalog_material_grade(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-material-grade-valid", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["material_grade"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["material_grade"]},
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "edit_session": {"parameter": "material_grade"},
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    updated = submit_task_input(
        manager,
        task.task_id,
        parameter="material_grade",
        value="SA-106B",
        unit=None,
        standards_root=standards_root,
    )

    assert fact_get_value(updated, "material_grade") == "astm_a106_gr_b"
    assert fact_get_value(updated, "metallurgical_group") == "ferritic_steels"


def test_build_parameter_definitions_includes_pipe_construction_lookup_options(
    standards_root: Path,
) -> None:
    from engine.reference.standards_reader import StandardsReader

    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-construction-type", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(
        task,
        legacy_input(
            input_id="material_grade",
            value="astm_a106_gr_b",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    planning = {
        "missing_inputs": ["pipe_construction_type"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["pipe_construction_type"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    reader = StandardsReader(standards_root)
    parameters = {
        item["name"]: item
        for item in build_parameter_definitions(manager.get_task(task.task_id), reader=reader)
    }

    construction = parameters["pipe_construction_type"]
    assert construction["type"] == "dropdown"
    assert construction["options"] == [{"value": "Seamless pipe", "label": "Seamless pipe"}]


def test_build_parameter_definitions_exposes_structured_user_prompt(standards_root: Path) -> None:
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(standards_root, standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("param-user-prompt-serialization", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["internal_design_gage_pressure"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["internal_design_gage_pressure"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    parameters = build_parameter_definitions(manager.get_task(task.task_id), reader=reader)
    pressure = next(item for item in parameters if item["name"] == "internal_design_gage_pressure")
    assert pressure["prompt"] == "Enter internal design gage pressure P."
    assert pressure["help_text"] is not None
    assert "500 psi" not in pressure["help_text"]
    assert "pressure design thickness" in pressure["help_text"].lower()
    assert pressure["units"]
    assert pressure["guidance"] is not None
    assert "question" not in pressure
    assert "short_question" not in pressure
