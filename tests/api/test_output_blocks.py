"""Tests for desktop display output blocks."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus

from api.output_blocks import build_display_outputs
from engine.reference.parameter_keys import parameter_node_description
from api.serializers import task_state
from tests.acceptance.helpers import run_completed_workflow
from engine.state.task_facts import deactivate_fact
from tests.helpers.facts import fact_get_value, legacy_input, set_fact_from_input
from tests.helpers.goals import task_with_planning


def _apply_post_calculation_outputs(task, *, t_m: float = 2.252, standards_root=None) -> None:
    """Simulate completed thickness outputs for display-output regression tests."""
    from engine.executor.pipe_schedule_recommendation import (
        build_b36_10_schedule_lookup_trace_entry,
    )
    from engine.equation.equation_display_trace_builder import build_equation_display_trace
    from models.calculation import CalculationResult, CalculationStatus, QuantityResult

    task.outputs.setdefault("workflow", "pipe_wall_thickness_design")
    t_value = t_m - 0.252
    task.outputs["t"] = t_value
    task.outputs["required_thickness"] = t_value
    task.outputs["minimum_required_thickness"] = t_m
    task.outputs["t_m"] = t_m
    task.outputs["thin_wall"] = True

    eq_3a_trace = None
    if standards_root is not None:
        from engine.reference.standards_reader import StandardsReader

        reader = StandardsReader(standards_root, standard="asme_b31.3")
        eq_3a_id = "asme-b313-304-1-2-eq-3a"
        eq_3a = reader.load(eq_3a_id)
        variables = {
            "P": 3_450_000.0,
            "D": 0.254,
            "S": 138_000_000.0,
            "E_j": 1.0,
            "W": 1.0,
            "Y": 0.4,
            "t": t_value,
        }
        eq_3a_trace = build_equation_display_trace(
            reader=reader,
            equation_id=eq_3a_id,
            equation_metadata=eq_3a.metadata,
            symbol_values=variables,
            source_node_id="304.1.2-a",
            dependency_outputs={},
            task_inputs=task.fact_store.active_facts(),
            calculation=CalculationResult(
                calculation_id=eq_3a_id,
                final_result=QuantityResult(symbol="t", value=t_value, unit="mm"),
                status=CalculationStatus.PASS,
            ),
            task=task,
        )

    trace_entry: dict = {
        "node_id": "304.1.2-a",
        "trace": {
            "calculation": {"final_result": {"value": t_value, "unit": "mm"}},
            "variables_si": {
                "P": 3_450_000.0,
                "D": 0.254,
                "S": 138_000_000.0,
                "E_j": 1.0,
                "W": 1.0,
                "Y": 0.4,
            },
        },
    }
    if eq_3a_trace is not None:
        trace_entry["trace"]["equation_display_trace"] = eq_3a_trace.to_dict()

    trace: list[dict] = [trace_entry]
    if standards_root is not None:
        schedule_entry = build_b36_10_schedule_lookup_trace_entry(task, standards_root)
        if schedule_entry is not None:
            trace.append(schedule_entry)
    task.outputs["_execution_trace"] = trace


def test_preview_outputs_for_awaiting_input_task(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test06", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "goal": "pipe wall thickness design",
        "action": "request_input",
        "active_definition_node": "B313-304.1.1",
        "missing_inputs": ["material", "internal_design_gage_pressure"],
        "missing_assumptions": ["straight_pipe_section"],
        "current_phase": "expansion_assumptions",
        "phase_missing": {"expansion_assumptions": ["straight_pipe_section"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    task.active_nodes = ["B313-304.1.1"]
    manager.replace_task(task.task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    types = {block["type"] for block in blocks}

    assert "equation" in types
    assert "table" not in types
    assert not any(block["id"].startswith("node-activation-") for block in blocks)


def test_new_pipe_wall_task_single_eq_2_preview_block(standards_reader) -> None:
    from api.desktop_service import DesktopApiService
    from config.loader import CLIConfig
    from pathlib import Path
    import tempfile

    project_root = Path(__file__).resolve().parents[2]
    tmpdir = tempfile.mkdtemp()
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=Path(tmpdir),
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    service = DesktopApiService(config=config, session_id="default")
    from tests.api.conftest import api_session_id

    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)

    eq_blocks = [
        block
        for block in state["display_outputs"]
        if block.get("equation_node_id") == "asme-b313-304-1-1-eq-2"
    ]
    assert len(eq_blocks) >= 1
    preview_blocks = [
        block
        for block in eq_blocks
        if block.get("id") == "equation-asme-b313-304-1-1-eq-2"
    ]
    assert len(preview_blocks) >= 1
    equation = preview_blocks[0]
    assert equation.get("lifecycle") in {"durable", "preview", None}
    assert "input_table" in equation
    assert "variables" not in equation
    symbols = [row["symbol"] for row in equation["input_table"]["rows"]]
    assert len(symbols) == len(set(symbols))
    assert "planning-status" not in {block["id"] for block in state["display_outputs"]}
    assert state.get("workflow_display", {}).get("display_title") == "Pipe Wall Thickness Design"
    assert "pipe_wall_thickness_design" not in state.get("name", "")


def test_preview_dedupe_preserves_evaluated_equation_block() -> None:
    from api.display_block_metadata import dedupe_equation_blocks_by_node_id
    from models.display_role import DisplayRole, DisplayState

    blocks = [
        {
            "id": "node-activation-equation-304.1.1-a-fallback",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.active.value,
            "variables": [{"symbol": "t"}, {"symbol": "c"}],
        },
        {
            "id": "path-preview-equation-304.1.1-a",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.preview.value,
            "input_table": {"columns": [], "rows": [{"symbol": "t"}, {"symbol": "c"}]},
        },
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.evaluated.value,
            "display": "t = 1.23 mm",
        },
    ]
    deduped = dedupe_equation_blocks_by_node_id(blocks)
    ids = [block["id"] for block in deduped]
    assert "path-preview-equation-304.1.1-a" in ids
    assert "equation-asme-b313-304-1-1-eq-2" in ids
    assert "node-activation-equation-304.1.1-a-fallback" not in ids


def test_completed_workflow_outputs_include_results_and_equation(
    standards_reader,
    state_manager,
) -> None:
    task_id = "pipe-wall-thickness-desi-test07"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    _apply_post_calculation_outputs(task, standards_root=standards_reader.standards_root)
    state_manager.replace_task(task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    types = [block["type"] for block in blocks]
    ids = [block["id"] for block in blocks]

    assert not any(block_id.startswith("node-activation-") for block_id in ids)
    assert types.count("equation") >= 1
    assert any(block_id.startswith("equation-asme-b313-") for block_id in ids)
    assert any(block_id.startswith("table-lookup-") for block_id in ids)
    assert any(block_id.startswith("result-summary-") for block_id in ids)
    assert "planning-status" not in ids


def test_completed_workflow_with_nps_includes_schedule_recommendation(
    standards_reader,
    state_manager,
) -> None:
    from models.input import EngineeringInput, InputSource, InputStatus
    from tests.acceptance.helpers import run_completed_workflow

    task_id = "pipe-wall-thickness-desi-test13"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    set_fact_from_input(task, legacy_input(input_id="d_input_mode",
        value="nps_lookup",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="nominal_pipe_size",
        value="2",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    task.outputs["outside_diameter_lookup"] = {
        "nps": "2",
        "outside_diameter_mm": 60.325,
        "standard": "asme_b36.10",
        "table_id": "table-2-1",
    }
    _apply_post_calculation_outputs(task, standards_root=standards_reader.standards_root)
    state_manager.replace_task(task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    schedule = next(block for block in blocks if block["id"] == "table-lookup-B3610-table-2-1")
    assert schedule["type"] == "table"
    assert schedule.get("summary_text") and "Schedule 10" in schedule["summary_text"]
    assert schedule.get("highlight_row") == {"column": "schedule", "value": "10"}


def test_task_state_includes_display_outputs(
    standards_reader,
    state_manager,
) -> None:
    task_id = "pipe-wall-thickness-desi-test08"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    _apply_post_calculation_outputs(task, standards_root=standards_reader.standards_root)
    state_manager.replace_task(task_id, task)

    state = task_state(task, state_manager)
    assert isinstance(state["display_outputs"], list)
    assert len(state["display_outputs"]) > 0


def test_path_preview_equation_resolves_variable_descriptions(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test09", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "goal": "pipe wall thickness design",
        "action": "request_input",
        "active_definition_node": "B313-304.1.1",
        "path_decision": {
            "pressure_loading": "internal_pressure",
            "selected_node": "304.1.2-a",
        },
        "missing_inputs": ["material", "internal_design_gage_pressure"],
        "current_phase": "formula_parameters",
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    task.active_nodes = ["B313-304.1.1", "304.1.2-a"]

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    equation_blocks = [
        block
        for block in blocks
        if block["type"] == "equation" and block.get("equation_node_id") == "asme-b313-304-1-2-eq-3a"
    ]
    assert len(equation_blocks) == 1
    assert equation_blocks[0]["id"] == "equation-asme-b313-304-1-2-eq-3a"
    assert not any(
        block.get("equation_node_id") == "asme-b313-304-1-1-eq-2" for block in equation_blocks
    )

    paragraph_blocks = [block for block in blocks if block["id"] == "paragraph-304.1.2-a"]
    assert len(paragraph_blocks) == 1

    equation = equation_blocks[0]
    assert equation.get("title") == "Internal Pressure Wall Thickness — Eq. (3a)"
    assert "internal pressure design thickness" in str(equation.get("context_intro") or "").lower()
    assert equation.get("lifecycle") == "preview"
    assert "variables" not in equation
    assert "input_table" in equation
    pressure_row = next(row for row in equation["input_table"]["rows"] if row["symbol"] == "P")
    assert pressure_row["description"] == parameter_node_description(input_id="internal_design_gage_pressure")
    assert pressure_row["value"] == "Awaiting user input"
    pressure_reference = pressure_row.get("definition_reference")
    assert pressure_reference is not None
    assert pressure_reference["node_id"] in {"304.1.1-b", "B313-304.1.1", "asme-b313-304-1-1-b"}


def test_post_calculation_outputs_before_corrosion_allowance(standards_reader, state_manager) -> None:
    from tests.acceptance.helpers import run_completed_workflow

    task_id = "pipe-wall-thickness-desi-test12"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    _apply_post_calculation_outputs(task, standards_root=standards_reader.standards_root)
    deactivate_fact(task, "corrosion_allowance")
    task.outputs.pop("minimum_required_thickness", None)
    task.outputs.pop("t_m", None)
    task.status = TaskStatus.AWAITING_INPUT
    state_manager.replace_task(task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = [block["id"] for block in blocks]

    assert "equation-asme-b313-304-1-2-eq-3a" in ids
    assert not any(block_id.startswith("node-activation-") for block_id in ids)


def test_execution_trace_keeps_definition_node_outputs(standards_reader) -> None:
    from tests.acceptance.helpers import run_completed_workflow

    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-desi-test11"
    run_completed_workflow(manager, standards_reader, task_id)
    task = manager.get_task(task_id)
    task.outputs.pop("required_thickness", None)
    task.outputs.pop("t", None)
    task.outputs.pop("minimum_required_thickness", None)
    task.outputs.pop("t_m", None)
    task.outputs.pop("_execution_trace", None)
    from tests.helpers.goals import task_with_planning

    task_with_planning(
        task,
        {
            "path_decision": {"selected_node": "304.1.2-a"},
            "current_phase": "definition_equation_completion",
        },
        workflow_id="pipe_wall_thickness_design",
    )

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = [block["id"] for block in blocks]

    assert any(block_id.startswith("equation-asme-b313-") for block_id in ids)


def test_thin_wall_applicability_block_when_check_fails(state_manager, standards_reader) -> None:
    task = state_manager.create_task("thin-wall-fail-display", status=TaskStatus.COMPLETED)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "t": 5.0,
        "thin_wall": False,
        "_execution_trace": [{"node_id": "304.1.2-a", "trace": {"calculation": {"final_result": {"value": 5.0}}}}],
    }
    state_manager.replace_task(task.task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    applicability = next(
        block for block in blocks if block["id"] == "validation-thin-wall-criterion"
    )
    assert "not satisfied" in applicability["content"].lower()


def _pipe_wall_service():
    from api.desktop_service import DesktopApiService
    from config.loader import CLIConfig
    from pathlib import Path
    import tempfile

    project_root = Path(__file__).resolve().parents[2]
    tmpdir = tempfile.mkdtemp()
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=Path(tmpdir),
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def _eq2_trace_block(blocks: list[dict]) -> dict:
    return next(
        block
        for block in blocks
        if block.get("id") == "equation-asme-b313-304-1-1-eq-2"
    )


def test_eq2_trace_shows_derived_reference_for_t_before_eq3a_evaluation(standards_reader) -> None:
    from api.equation_inputs_display import AWAITING_USER_INPUT
    from tests.api.test_equation_display_trace import _apply_simulated_completed_state

    manager = TaskStateManager()
    task = manager.create_task("eq2-derived-ref", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {
            "pressure_loading": "internal_pressure",
            "selected_node": "304.1.2-a",
        },
        "current_phase": "formula_parameters",
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]
    _apply_simulated_completed_state(task, standards_reader)
    task.outputs.pop("t", None)
    task.outputs.pop("required_thickness", None)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    trace = _eq2_trace_block(blocks)
    t_row = next(row for row in trace["input_table"]["rows"] if row["symbol"] == "t")
    assert t_row.get("value_reference") is not None or t_row.get("value_provenance")
    assert t_row["value"] != AWAITING_USER_INPUT or t_row.get("value_provenance", {}).get("status") == "pending_derived"


def test_eq2_trace_updates_t_value_after_eq3a_evaluation(standards_reader) -> None:
    from api.equation_inputs_display import AWAITING_USER_INPUT
    from api.output_blocks import build_display_outputs

    manager = TaskStateManager()
    task = manager.create_task("eq-trace-live-t", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {
            "pressure_loading": "internal_pressure",
            "selected_node": "304.1.2-a",
        },
        "current_phase": "formula_parameters",
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "t": 2.0,
        "required_thickness": 2.0,
        "_equation_trace_keys": [
            "pipe_wall_thickness_design|304.1.1-a|asme-b313-304-1-1-eq-2|equation"
        ],
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    trace = _eq2_trace_block(blocks)
    t_row = next(row for row in trace["input_table"]["rows"] if row["symbol"] == "t")
    assert t_row["value"] != AWAITING_USER_INPUT
    assert "2.000" in t_row["value"]
    assert t_row.get("value_reference") is not None
    assert t_row.get("value_status") == "equation_derived"


def test_equation_trace_not_duplicated_on_repeated_task_state(standards_reader) -> None:
    from tests.api.conftest import api_session_id

    service = _pipe_wall_service()
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    first_traces = [
        block
        for block in state["display_outputs"]
        if str(block.get("id", "")).startswith("equation-asme-b313-")
    ]
    second = service.get_task(state["task_id"], session_id=session_id)
    second_traces = [
        block
        for block in second["display_outputs"]
        if str(block.get("id", "")).startswith("equation-asme-b313-")
    ]
    assert len(first_traces) == len(second_traces)


def test_pressure_loading_internal_keeps_eq2_trace_and_adds_eq3a_preview(standards_reader) -> None:
    from tests.api.conftest import api_session_id

    service = _pipe_wall_service()
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    state = service.submit_input(
        state["task_id"],
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    state = service.submit_input(
        state["task_id"],
        parameter="pressure_loading",
        value="internal_pressure",
        session_id=session_id,
    )

    eq3a_blocks = [
        block
        for block in state["display_outputs"]
        if block.get("equation_node_id") == "asme-b313-304-1-2-eq-3a"
    ]
    assert len(eq3a_blocks) == 1
    assert "planning-status" not in {block["id"] for block in state["display_outputs"]}


def test_finalize_display_blocks_dedupes_preview_equation_by_node_id(standards_reader) -> None:
    from api.output_blocks import _finalize_display_blocks
    from models.display_role import DisplayRole, DisplayState

    blocks = [
        {
            "id": "node-activation-equation-304.1.1-a-fallback",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.active.value,
            "lifecycle": "preview",
            "variables": [{"symbol": "t"}],
        },
        {
            "id": "path-preview-equation-304.1.1-a",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.preview.value,
            "lifecycle": "preview",
            "input_table": {"columns": [], "rows": [{"symbol": "t"}]},
        },
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.evaluated.value,
            "lifecycle": "durable",
            "display": "t = 1.23 mm",
        },
    ]
    result = _finalize_display_blocks(blocks, standards_reader)
    result_ids = {block["id"] for block in result}
    assert "node-activation-equation-304.1.1-a-fallback" not in result_ids
    assert "equation-asme-b313-304-1-1-eq-2" in result_ids


def test_warning_block_id_stable_across_calls() -> None:
    from api.output_blocks import _warning_block, _warning_block_id

    message = "Example validation warning"
    assert _warning_block_id(message) == _warning_block_id(message)
    assert _warning_block(message)["id"] == _warning_block_id(message)
