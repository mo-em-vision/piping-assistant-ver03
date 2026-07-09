"""MAWP thickness derivation and trace display tests."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus

from api.output_blocks import build_display_outputs
from tests.helpers.goals import task_with_planning


def test_pressure_design_trace_produces_generic_calculation_blocks(
    standards_reader,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("mawp-trace-test", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "mawp_design"
    task_with_planning(task, {"current_phase": "completed"}, workflow_id="mawp_design")
    task.outputs["_execution_trace"] = [
        {
            "node_id": "asme-b313-pressure-design-thickness",
            "trace": {
                "variables_si": {"t_actual": 6.35, "c": 0.5},
                "calculation": {
                    "final_result": {"value": 5.85, "unit": "mm"},
                    "formula_display": "t = t_actual - c",
                },
            },
            "outputs": {"t": 5.85},
        }
    ]
    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = [block["id"] for block in blocks]
    assert any(block_id.startswith("equation-") for block_id in ids)
    assert not any("minimum-thickness-equation" in block_id for block_id in ids)


def test_pressure_design_trace_legacy_node_id(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("mawp-trace-legacy", status=TaskStatus.COMPLETED)
    task.outputs["workflow"] = "mawp_design"
    task_with_planning(task, {"current_phase": "completed"}, workflow_id="mawp_design")
    task.outputs["_execution_trace"] = [
        {
            "node_id": "B313-MAWP-PRESSURE-DESIGN",
            "trace": {
                "variables_si": {"t_actual": 4.0, "c": 0.25},
                "calculation": {
                    "final_result": {"value": 3.75, "unit": "mm"},
                    "formula_display": "t = t_actual - c",
                },
            },
            "outputs": {"t": 3.75},
        }
    ]
    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    assert len(blocks) >= 1
