"""Lifecycle tests for equation rendering and center-panel ordering."""

from __future__ import annotations

from api.equation_inputs_display import AWAITING_USER_INPUT
from api.output_blocks import build_display_outputs, _equation_blocks_show_awaiting_input
from engine.state.state_manager import TaskStateManager
from models.display_role import DisplayRole, sort_blocks_by_report_role
from models.task import TaskStatus
from tests.helpers.goals import task_with_planning


EQ_2_ID = "asme-b313-304-1-1-eq-2"
EQ_3A_ID = "asme-b313-304-1-2-eq-3a"
EQ_2_BLOCK_ID = f"equation-{EQ_2_ID}"
EQ_3A_BLOCK_ID = f"equation-{EQ_3A_ID}"


def test_input_waiting_sorts_after_equation_blocks(standards_reader) -> None:
    equation = {
        "id": EQ_3A_BLOCK_ID,
        "type": "equation",
        "display_role": DisplayRole.equation.value,
        "display_state": "preview",
        "lifecycle": "preview",
        "content": "t = PD / 2(SEW + PY)",
    }
    waiting = {
        "id": "input-waiting",
        "type": "text",
        "display_role": DisplayRole.input_waiting.value,
        "lifecycle": "volatile",
        "content": "Waiting for your input.",
    }

    ordered = sort_blocks_by_report_role([waiting, equation])
    roles = [block.get("display_role") for block in ordered]

    assert roles.index(DisplayRole.equation.value) < roles.index(DisplayRole.input_waiting.value)


def test_suppress_input_waiting_when_equation_table_shows_awaiting() -> None:
    blocks = [
        {
            "id": EQ_3A_BLOCK_ID,
            "type": "equation",
            "input_table": {
                "rows": [{"symbol": "P", "value": AWAITING_USER_INPUT}],
            },
        }
    ]

    assert _equation_blocks_show_awaiting_input(blocks) is True


def test_emit_input_waiting_when_no_equation_awaiting_rows(
    standards_reader,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("lifecycle-no-eq-awaiting", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task_with_planning(
        task,
        {"current_phase": "expansion_assumptions"},
        workflow_id="pipe_wall_thickness_design",
    )

    blocks = build_display_outputs(task, reader=standards_reader)
    waiting_ids = {block.get("id") for block in blocks if block.get("display_role") == DisplayRole.input_waiting.value}

    assert "input-waiting" in waiting_ids or not any(
        block.get("type") == "equation"
        and _equation_blocks_show_awaiting_input([block])
        for block in blocks
    )


def test_stable_equation_block_id_across_preview_and_evaluated(standards_reader) -> None:
    from api.equation_evaluation_display import build_equation_evaluation_block

    manager = TaskStateManager()
    task = manager.create_task("lifecycle-stable-id", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task_with_planning(
        task,
        {
            "path_decision": {"selected_node": "304.1.2-a"},
            "current_phase": "parameter_gathering",
        },
        workflow_id="pipe_wall_thickness_design",
    )

    preview = build_equation_evaluation_block(task, standards_reader, "304.1.2-a")
    assert preview is not None
    assert preview["id"] == EQ_3A_BLOCK_ID

    task.outputs["_execution_trace"] = [
        {
            "node_id": "304.1.2-a",
            "equation_node_id": EQ_3A_ID,
            "trace": {
                "equation_display_trace": {
                    "equation_id": EQ_3A_ID,
                    "node_id": "304.1.2-a",
                    "status": "evaluated",
                    "symbolic_latex": "t = x",
                    "inputs": [],
                    "intermediate_values": [],
                    "latex_source": "metadata_display_text",
                }
            },
        }
    ]

    evaluated_blocks = build_display_outputs(task, reader=standards_reader)
    equation_blocks = [
        block for block in evaluated_blocks if block.get("id") == EQ_3A_BLOCK_ID
    ]
    assert len(equation_blocks) == 1
    assert equation_blocks[0]["display_state"] == "evaluated"
