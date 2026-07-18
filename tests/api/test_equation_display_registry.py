"""Tests for graph-driven equation display registry."""

from __future__ import annotations

from pathlib import Path

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.api.conftest import api_session_id
from tests.api.test_equation_display_trace import EQ_2_ID, EQ_3A_ID, _apply_simulated_completed_state
from tests.helpers.goals import task_with_planning

EQ_2_BLOCK_ID = f"equation-{EQ_2_ID}"
EQ_3A_BLOCK_ID = f"equation-{EQ_3A_ID}"


def _service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def test_discover_includes_definition_equation_after_execution_trace(standards_reader) -> None:
    from api.equation_display_registry import discover_equation_display_entries

    manager = TaskStateManager()
    task = manager.create_task("eq-registry-def", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "definition_equation_completion",
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    _apply_simulated_completed_state(task, standards_reader)
    trace = task.outputs["_execution_trace"]
    task.outputs["_execution_trace"] = [e for e in trace if e.get("node_id") != EQ_2_ID]

    entries = discover_equation_display_entries(task, standards_reader, planning)
    equation_ids = [item[0] for item in entries]

    assert EQ_2_ID in equation_ids
    assert EQ_3A_ID in equation_ids
    assert len(equation_ids) == len(set(equation_ids))


def test_register_equation_display_key_is_idempotent(standards_reader) -> None:
    from api.display_block_metadata import EQUATION_TRACE_KEYS_OUTPUT
    from api.equation_display_registry import register_equation_display_key

    manager = TaskStateManager()
    task = manager.create_task("eq-registry-key", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    assert register_equation_display_key(task, "pipe_wall_thickness_design", "304.1.1-a", EQ_2_ID)
    assert not register_equation_display_key(task, "pipe_wall_thickness_design", "304.1.1-a", EQ_2_ID)
    assert len(task.outputs[EQUATION_TRACE_KEYS_OUTPUT]) == 1


def test_build_display_outputs_includes_eq2_after_upstream_eval_without_eq2_trace(
    standards_reader,
) -> None:
    from api.output_blocks import build_display_outputs
    from engine.state.fact_migration import fact_from_engineering_input
    from models.input import EngineeringInput, InputSource, InputStatus

    manager = TaskStateManager()
    task = manager.create_task("eq-registry-display", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "definition_equation_completion",
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    _apply_simulated_completed_state(task, standards_reader)
    trace = task.outputs["_execution_trace"]
    task.outputs["_execution_trace"] = [e for e in trace if e.get("node_id") != EQ_2_ID]
    manager.store_fact(
        task.task_id,
        fact_from_engineering_input(
            EngineeringInput(
                input_id="corrosion_allowance",
                value=0.252,
                unit="mm",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = manager.get_task(task.task_id)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    eq2_blocks = [block for block in blocks if block.get("equation_node_id") == EQ_2_ID]
    assert len(eq2_blocks) == 1
    trace_payload = eq2_blocks[0].get("equation_display_trace") or {}
    assert trace_payload.get("status") in {"blocked", "evaluated", "preview"}
    t_row = next(
        row
        for row in (eq2_blocks[0].get("input_table") or {}).get("rows") or []
        if row.get("symbol") == "t"
    )
    assert float(str(t_row.get("value") or "0")) == 2.0


def test_eq2_partial_substitution_keeps_t_m_symbol_on_lhs(standards_reader) -> None:
    from api.output_blocks import build_display_outputs

    manager = TaskStateManager()
    task = manager.create_task("eq-registry-partial-lhs", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "definition_equation_completion",
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    _apply_simulated_completed_state(task, standards_reader)
    trace = task.outputs["_execution_trace"]
    task.outputs["_execution_trace"] = [e for e in trace if e.get("node_id") != EQ_2_ID]
    task.outputs.pop("t_m", None)
    task.outputs.pop("minimum_required_thickness", None)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    eq2_blocks = [block for block in blocks if block.get("equation_node_id") == EQ_2_ID]
    assert len(eq2_blocks) == 1
    trace_payload = eq2_blocks[0].get("equation_display_trace") or {}
    substituted = str(trace_payload.get("substituted_latex") or "")
    assert substituted
    assert substituted.startswith("t_m")
    lhs = substituted.split("=", 1)[0]
    assert "2.252" not in lhs
    assert "2.25" not in lhs


def test_definition_equation_completion_records_display_trace(standards_reader) -> None:
    from engine.graph.definition_equations import try_complete_definition_equations
    from engine.graph.graph_engine import GraphEngine
    from engine.state.fact_migration import fact_from_engineering_input
    from models.input import EngineeringInput, InputSource, InputStatus
    from tests.acceptance.helpers import run_completed_workflow, sample_inputs

    manager = TaskStateManager()
    task_id = "eq-registry-def-complete"
    inputs = sample_inputs()
    inputs["metallurgical_group"] = EngineeringInput(
        input_id="metallurgical_group",
        value="carbon_steel",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    inputs["material_grade"] = EngineeringInput(
        input_id="material_grade",
        value="SA-106B",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    inputs["pipe_construction_type"] = EngineeringInput(
        input_id="pipe_construction_type",
        value="seamless",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    del inputs["corrosion_allowance"]
    run_completed_workflow(manager, standards_reader, task_id, inputs=inputs)
    task = manager.get_task(task_id)
    manager.store_fact(
        task_id,
        fact_from_engineering_input(
            EngineeringInput(
                input_id="corrosion_allowance",
                value=0.5,
                unit="mm",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = manager.get_task(task_id)
    plan = GraphEngine().build_plan(
        task_id=task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
        reader=standards_reader,
    )
    assert try_complete_definition_equations(task, standards_reader, plan.execution_order)

    eq2_trace = None
    for entry in task.outputs.get("_execution_trace") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("node_id")) == EQ_2_ID:
            eq2_trace = (entry.get("trace") or {}).get("equation_display_trace")
    assert isinstance(eq2_trace, dict)
    assert eq2_trace.get("status") == "evaluated"
    assert eq2_trace.get("substituted_latex")
    assert eq2_trace.get("result_latex")


def test_bootstrap_equation_preview_is_not_durable_display(
    tmp_path: Path,
    project_root: Path,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    manager = service._store_for(session_id).load_state_manager()
    task = manager.get_task(task_id)
    assert EQ_2_ID in {
        key.split("|")[2]
        for key in (task.outputs.get("_equation_trace_keys") or [])
        if isinstance(key, str)
    }

    service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    service.submit_input(
        task_id,
        parameter="pressure_design_case",
        value="internal_pressure",
        session_id=session_id,
    )

    state = service.get_task(task_id, session_id)
    equation_ids = [
        str(block.get("id"))
        for block in state.get("display_outputs") or []
        if isinstance(block, dict)
        and (block.get("type") == "equation" or str(block.get("id", "")).startswith("equation-"))
    ]

    assert EQ_2_BLOCK_ID not in equation_ids
    assert equation_ids == [EQ_3A_BLOCK_ID]

    task = manager.get_task(task_id)
    assert EQ_2_ID in {
        key.split("|")[2]
        for key in (task.outputs.get("_equation_trace_keys") or [])
        if isinstance(key, str)
    }


def test_definition_equation_appears_when_prerequisites_available(standards_reader) -> None:
    from api.output_blocks import build_display_outputs

    manager = TaskStateManager()
    task = manager.create_task("eq-registry-prereq-visible", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "definition_equation_completion",
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    _apply_simulated_completed_state(task, standards_reader)
    trace = task.outputs["_execution_trace"]
    task.outputs["_execution_trace"] = [entry for entry in trace if entry.get("node_id") != EQ_2_ID]

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    equation_ids = [
        str(block.get("equation_node_id"))
        for block in blocks
        if str(block.get("type") or "") == "equation"
    ]

    assert EQ_3A_ID in equation_ids
    assert EQ_2_ID in equation_ids
