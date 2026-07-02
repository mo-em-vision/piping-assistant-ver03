"""Tests for node calculation summaries in task state."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.node_calculation_summaries import build_node_calculation_summaries
from api.serializers import task_state
from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from tests.acceptance.helpers import (
    WALL_THICKNESS_NODE,
    confirmed_default_inputs,
    internal_pressure_assumption,
    run_completed_workflow,
    straight_section_assumption,
)
from tests.helpers.facts import fact_get_value, populate_task_facts
from tests.helpers.goals import task_with_planning
from models.fact import SourceType, ValidationStatus

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _standards_db_available(project_root: Path | None = None) -> bool:
    root = project_root or _REPO_ROOT
    return resolve_pack_tables_db(root / "knowledge" / "standards" / "asme" / "asme_b31.3").exists()


@pytest.mark.skipif(
    not _standards_db_available(),
    reason="standards_tables.db must be built for end-to-end thickness execution",
)
def test_build_node_calculation_summaries_includes_thickness_result(
    standards_reader: StandardsReader,
    state_manager: TaskStateManager,
) -> None:
    task_id = "node-calc-summary-test"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)

    summaries = build_node_calculation_summaries(task, standards_reader)
    thickness = next(item for item in summaries if item["node_id"] == WALL_THICKNESS_NODE)

    assert thickness["paragraph"] in {"304.1.2", "304.1.1", None} or thickness.get("title")
    assert thickness["primary_result"]["symbol"] == "t"
    assert thickness["primary_result"]["value"]
    assert any(row["symbol"] == "P" for row in thickness["inputs"])
    assert any(row["symbol"] == "D" for row in thickness["inputs"])


def test_task_state_includes_node_calculations(
    standards_reader: StandardsReader,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("node-calc-summary-test02", status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(task, {
            "pressure_loading": internal_pressure_assumption(),
            "straight_pipe_section": straight_section_assumption(),
            **confirmed_default_inputs(),
            "material": EngineeringInput(
                input_id="material",
                value="SA-106B",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "design_pressure": EngineeringInput(
                input_id="design_pressure",
                value=8.0,
                unit="bar",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "design_temperature": EngineeringInput(
                input_id="design_temperature",
                value=38.0,
                unit="C",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "nominal_pipe_size": EngineeringInput(
                input_id="nominal_pipe_size",
                value="6",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "joint_category": EngineeringInput(
                input_id="joint_category",
                value="seamless",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        })
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "required_thickness": 0.084,
        "_execution_trace": [
            {
                "node_id": WALL_THICKNESS_NODE,
                "outputs": {"required_thickness": 0.084, "required_thickness_unit": "mm"},
                "trace": {
                    "calculation": {"steps": []},
                    "variables_si": {
                        "P": 800000.0,
                        "D": 0.1683,
                        "S": 138000000.0,
                        "E": 1.0,
                        "W": 1.0,
                        "Y": 0.4,
                    },
                },
            }
        ],
    }
    task_with_planning(task, {}, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager, reader=standards_reader)
    assert len(state["node_calculations"]) == 1
    assert state["node_calculations"][0]["primary_result"]["symbol"] == "t"
