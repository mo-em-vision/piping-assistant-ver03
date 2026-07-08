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


def _apply_post_calculation_outputs(task, *, t_m: float = 2.252) -> None:
    """Simulate completed thickness outputs for display-output regression tests."""
    task.outputs.setdefault("workflow", "pipe_wall_thickness_design")
    task.outputs["t"] = t_m - 0.252
    task.outputs["required_thickness"] = t_m - 0.252
    task.outputs["minimum_required_thickness"] = t_m
    task.outputs["t_m"] = t_m
    task.outputs["thin_wall"] = True
    task.outputs["_execution_trace"] = [
        {
            "node_id": "304.1.2-a",
            "trace": {
                "calculation": {"final_result": {"value": t_m - 0.252, "unit": "mm"}},
                "variables_si": {
                    "P": 3_450_000.0,
                    "D": 0.254,
                    "S": 138_000_000.0,
                    "E": 1.0,
                    "W": 1.0,
                    "Y": 0.4,
                },
            },
        }
    ]


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
    assert len(eq_blocks) == 2
    preview_blocks = [block for block in eq_blocks if block.get("display_role") == "preview"]
    trace_blocks = [block for block in eq_blocks if block.get("display_role") == "equation_trace"]
    assert len(preview_blocks) == 1
    assert len(trace_blocks) == 1
    equation = preview_blocks[0]
    trace = trace_blocks[0]
    assert equation.get("lifecycle") == "preview"
    assert equation.get("display_channel") == "current_equation_preview"
    assert trace.get("lifecycle") == "durable"
    assert trace["id"] == "equation-trace-304.1.1-a-asme-b313-304-1-1-eq-2"
    assert "input_table" in equation
    assert "input_table" in trace
    assert "variables" not in equation
    assert "variables" not in trace
    symbols = [row["symbol"] for row in equation["input_table"]["rows"]]
    assert len(symbols) == len(set(symbols))
    assert "planning-status" not in {block["id"] for block in state["display_outputs"]}
    assert state.get("workflow_display", {}).get("display_title") == "Pipe Wall Thickness Design"
    assert "pipe_wall_thickness_design" not in state.get("name", "")


def test_preview_dedupe_preserves_substituted_equation_block() -> None:
    from api.display_block_metadata import dedupe_preview_tier_equations

    blocks = [
        {
            "id": "node-activation-equation-304.1.1-a-fallback",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": "activation",
            "variables": [{"symbol": "t"}, {"symbol": "c"}],
        },
        {
            "id": "path-preview-equation-304.1.1-a",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": "preview",
            "input_table": {"columns": [], "rows": [{"symbol": "t"}, {"symbol": "c"}]},
        },
        {
            "id": "path-calculation-substituted-equation",
            "type": "equation",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display_role": "substituted",
            "display": "t = 1.23 mm",
        },
    ]
    deduped = dedupe_preview_tier_equations(blocks)
    ids = [block["id"] for block in deduped]
    assert "path-preview-equation-304.1.1-a" in ids
    assert "path-calculation-substituted-equation" in ids
    assert "node-activation-equation-304.1.1-a-fallback" not in ids


def test_completed_workflow_outputs_include_results_and_equation(
    standards_reader,
    state_manager,
) -> None:
    task_id = "pipe-wall-thickness-desi-test07"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    _apply_post_calculation_outputs(task)
    state_manager.replace_task(task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    types = [block["type"] for block in blocks]
    ids = [block["id"] for block in blocks]

    assert not any(block_id.startswith("node-activation-") for block_id in ids)
    assert types.count("equation") >= 1
    assert any("equation" in block_id for block_id in ids) or "path-calculation-substituted-equation" in ids
    assert "result" not in types
    assert "minimum-thickness-equation" in ids
    assert "table" not in types
    assert "graph" not in types
    assert "reference" not in types
    assert "planning-status" not in ids

    preview_id = "path-preview-equation-304.1.2-a"
    if preview_id not in ids:
        preview_id = "path-preview-equation-B313-eq-wall-thickness"
    assert preview_id in ids or any("path-preview-equation" in block_id for block_id in ids)

    if "path-calculation-substituted-equation" in ids:
        substituted = next(
            block for block in blocks if block["id"] == "path-calculation-substituted-equation"
        )
        assert "t" in substituted["display"].lower()
    assert "minimum-thickness-equation" in ids


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
    _apply_post_calculation_outputs(task)
    state_manager.replace_task(task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    schedule = next(block for block in blocks if block["id"] == "pipe-schedule-recommendation")
    assert schedule["type"] == "text"
    assert "Schedule 10" in schedule["content"]
    assert "ASME B36.10M" in schedule["content"]
    assert schedule["pipe_schedule_recommendation"]["schedule"] == "10"


def test_task_state_includes_display_outputs(
    standards_reader,
    state_manager,
) -> None:
    task_id = "pipe-wall-thickness-desi-test08"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    _apply_post_calculation_outputs(task)
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
        if block["type"] == "equation" and block["id"].startswith("path-preview-equation-")
    ]
    assert len(equation_blocks) == 1
    assert equation_blocks[0]["id"] == "path-preview-equation-304.1.2-a"
    assert not any(
        block.get("equation_node_id") == "asme-b313-304-1-1-eq-2" for block in equation_blocks
    )

    intro_blocks = [block for block in blocks if block["id"] == "path-preview-intro-304.1.2-a"]
    assert len(intro_blocks) == 1
    intro = intro_blocks[0]
    assert intro["type"] == "text"
    assert "minimum required wall thickness" in intro["content"].lower()
    assert intro["content_suffix"] == " with the following equation:"
    assert intro["reference_links"][0]["node_id"] == "304.1.2-a"
    assert intro["reference_links"][0]["label"] == "§304.1.2"
    assert not any(block["type"] == "reference" for block in blocks if block["id"].startswith("path-preview-"))

    equation = equation_blocks[0]
    assert equation.get("title") is None
    assert equation.get("lifecycle") == "preview"
    assert "variables" not in equation
    assert "input_table" in equation
    pressure_row = next(row for row in equation["input_table"]["rows"] if row["symbol"] == "P")
    assert pressure_row["definition"] == parameter_node_description(input_id="internal_design_gage_pressure")
    assert pressure_row["value"] == "Awaiting user input"
    pressure_reference = pressure_row.get("definition_reference")
    assert pressure_reference is not None
    assert pressure_reference["node_id"] in {"304.1.1-b", "B313-304.1.1", "asme-b313-304-1-1-b"}


def test_post_calculation_outputs_before_corrosion_allowance(standards_reader, state_manager) -> None:
    from tests.acceptance.helpers import run_completed_workflow

    task_id = "pipe-wall-thickness-desi-test12"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    _apply_post_calculation_outputs(task)
    deactivate_fact(task, "corrosion_allowance")
    task.outputs.pop("minimum_required_thickness", None)
    task.outputs.pop("t_m", None)
    task.status = TaskStatus.AWAITING_INPUT
    state_manager.replace_task(task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = [block["id"] for block in blocks]

    assert "path-preview-equation-304.1.2-a" in ids
    assert "path-calculation-substituted-equation" in ids or any(
        "substitut" in str(block.get("display", "")).lower() for block in blocks
    )
    assert "minimum-thickness-equation" in ids
    assert "minimum-thickness-equation" in ids
    assert "required-thickness-summary" not in ids
    assert "minimum-thickness-conclusion" not in ids
    assert not any(block_id.startswith("node-activation-") for block_id in ids)

    minimum = next(block for block in blocks if block["id"] == "minimum-thickness-equation")
    assert minimum["display"].endswith("+ c")
    assert "2.000" in minimum["display"]


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

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = [block["id"] for block in blocks]

    assert any(block_id.startswith("path-preview-equation-") for block_id in ids)
    assert "equation-304.1.2-a" not in ids


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
        block for block in blocks if block["id"] == "thin-wall-applicability-check"
    )
    assert applicability["content"] == (
        "ASME B31.3 paragraph §304.1.2 condition (t < D/6) is NOT valid. "
        "continuing with thick wall condition (t > D/6)"
    )


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
        if block.get("id") == "equation-trace-304.1.1-a-asme-b313-304-1-1-eq-2"
    )


def test_eq2_trace_shows_derived_reference_for_t_before_eq3a_evaluation(standards_reader) -> None:
    from tests.api.conftest import api_session_id
    from api.equation_inputs_display import AWAITING_USER_INPUT

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

    trace = _eq2_trace_block(state["display_outputs"])
    t_row = next(row for row in trace["input_table"]["rows"] if row["symbol"] == "t")
    assert t_row.get("value_reference") is not None
    assert t_row["value_reference"]["node_id"] == "304.1.2-a"
    assert t_row["value"] != AWAITING_USER_INPUT
    assert t_row.get("value_status") in {"unresolved_derived", "equation_derived"}


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
            "pipe_wall_thickness_design|304.1.1-a|asme-b313-304-1-1-eq-2|equation_trace"
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
        if block.get("display_role") == "equation_trace"
    ]
    second = service.get_task(state["task_id"], session_id=session_id)
    second_traces = [
        block
        for block in second["display_outputs"]
        if block.get("display_role") == "equation_trace"
    ]
    assert len(first_traces) == len(second_traces) == 1


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

    eq2_traces = [
        block
        for block in state["display_outputs"]
        if block.get("equation_node_id") == "asme-b313-304-1-1-eq-2"
        and block.get("display_role") == "equation_trace"
    ]
    eq3a_previews = [
        block
        for block in state["display_outputs"]
        if block.get("equation_node_id") == "asme-b313-304-1-2-eq-3a"
        and block.get("display_role") == "preview"
    ]
    assert len(eq2_traces) == 1
    assert len(eq3a_previews) == 1
    assert "planning-status" not in {block["id"] for block in state["display_outputs"]}
