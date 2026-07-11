"""Phase 4 tests: value_provenance on equation input table rows."""

from __future__ import annotations

import inspect

from api.desktop_service import DesktopApiService
from api.equation_evaluation_display import _definition_reference_for_parameter
from api.equation_inputs_display import AWAITING_USER_INPUT
from api.output_blocks import build_display_outputs
from api.reference_links import enrich_display_output_dict
from config.loader import CLIConfig
from engine.reference import parameter_value_source
from engine.reference.parameter_value_source import build_value_provenance
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from pathlib import Path
import tempfile

from tests.api.conftest import api_session_id
from tests.helpers.goals import task_with_planning


def _pipe_wall_service() -> DesktopApiService:
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


def _task_with_eq2_trace_key(task, *, include_t: bool = True) -> None:
    planning = {
        "path_decision": {
            "pressure_loading": "internal_pressure",
            "selected_node": "304.1.2-a",
        },
        "current_phase": "formula_parameters",
    }
    task.outputs.setdefault("workflow", "pipe_wall_thickness_design")
    if include_t:
        task.outputs["t"] = 2.0
        task.outputs["required_thickness"] = 2.0
    task.outputs["_equation_trace_keys"] = [
        "pipe_wall_thickness_design|304.1.1-a|asme-b313-304-1-1-eq-2|equation"
    ]
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]


def _enriched_eq2_trace(task, reader) -> dict:
    blocks = build_display_outputs(task, standards_root=reader.standards_root, reader=reader)
    trace = _eq2_trace_block(blocks)
    return enrich_display_output_dict(trace, reader, task=task)


def test_unresolved_equation_output_row_has_equation_provenance(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("prov-eq2-t", status=TaskStatus.AWAITING_INPUT)
    _task_with_eq2_trace_key(task, include_t=False)

    trace = _eq2_trace_block(
        build_display_outputs(task, standards_root=standards_reader.standards_root)
    )
    t_row = next(row for row in trace["input_table"]["rows"] if row["symbol"] == "t")
    provenance = t_row.get("value_provenance") or {}
    assert provenance.get("source_type") == "equation_output"
    assert provenance.get("status") == "pending_derived"
    assert t_row.get("value") != AWAITING_USER_INPUT
    assert AWAITING_USER_INPUT not in str(provenance.get("label") or "")


def test_unresolved_lookup_row_has_table_lookup_provenance(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("prov-s", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["asme-b313-table-A-1", "304.1.2-a"]

    provenance = build_value_provenance(
        standards_reader,
        "PARAM-allowable-stress",
        task,
        display_value="",
    )
    assert provenance["source_type"] == "table_lookup"
    assert provenance["status"] == "pending_derived"
    assert "Table" in provenance["label"] or "table" in provenance["label"].lower()


def test_unresolved_user_input_row_awaits_user(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("prov-p", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["304.1.2-a"]

    provenance = build_value_provenance(
        standards_reader,
        "PARAM-internal-design-gage-pressure",
        task,
        display_value="",
    )
    assert provenance["source_type"] == "user_input"
    assert provenance["status"] == "awaiting_user_input"
    assert provenance["label"] == AWAITING_USER_INPUT


def test_lookup_symbols_not_in_current_ask_when_keys_missing(standards_reader) -> None:
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

    current_ask = state.get("current_ask") or {}
    parameter_id = str(current_ask.get("parameter_id") or "")
    assert parameter_id not in {
        "allowable_stress",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
    }


def test_parameter_value_source_has_no_hardcoded_pipe_wall_ids() -> None:
    source = inspect.getsource(parameter_value_source)
    assert "304.1.2-a" not in source
    assert "pipe_wall_thickness_design" not in source


def test_mawp_formula_row_provenance_is_generic(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("prov-mawp", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {
            "pressure_loading": "internal_pressure",
            "selected_node": "304.1.2-a",
        },
        "current_phase": "formula_parameters",
    }
    task.outputs = {"workflow": "mawp_design"}
    task_with_planning(task, planning, workflow_id="mawp_design")
    task.active_nodes = ["304.1.2-a"]

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root, reader=standards_reader)
    equation_blocks = [block for block in blocks if block.get("type") == "equation" and block.get("input_table")]
    assert equation_blocks, "expected at least one MAWP equation preview with input table"
    rows = equation_blocks[0]["input_table"]["rows"]
    assert rows
    for row in rows:
        if row.get("value_provenance"):
            assert row["value_provenance"]["source_type"] in {
                "user_input",
                "equation_output",
                "table_lookup",
                "default",
                "unknown",
            }


def test_api_projection_adds_reference_chips_to_value_provenance(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("prov-chips", status=TaskStatus.AWAITING_INPUT)
    _task_with_eq2_trace_key(task)

    trace_block = _eq2_trace_block(
        build_display_outputs(task, standards_root=standards_reader.standards_root)
    )
    enriched = enrich_display_output_dict(trace_block, standards_reader, task=task)
    t_row = next(row for row in enriched["input_table"]["rows"] if row["symbol"] == "t")
    provenance = t_row.get("value_provenance") or {}
    chips = provenance.get("reference_chips") or []
    assert chips
    labels = [str(chip.get("label") or "") for chip in chips]
    assert any(label and label != str(chip.get("id") or "") for label, chip in zip(labels, chips))


def test_api_projection_keeps_definition_reference_separate_from_row_chips(standards_reader) -> None:
    from api.reference_links import enrich_row_provenance_dict

    manager = TaskStateManager()
    task = manager.create_task("prov-s-chips", status=TaskStatus.AWAITING_INPUT)
    task.active_nodes = ["asme-b313-table-A-1", "304.1.2-a"]

    row = enrich_row_provenance_dict(
        {
            "symbol": "S",
            "definition": "stress value for material",
            "value": "",
            "parameter_id": "PARAM-allowable-stress",
            "definition_reference": _definition_reference_for_parameter(
                standards_reader,
                "PARAM-allowable-stress",
            ),
            "value_provenance": build_value_provenance(
                standards_reader,
                "PARAM-allowable-stress",
                task,
                display_value="",
            ),
        },
        standards_reader,
        task=task,
    )
    definition_reference = row.get("definition_reference") or {}
    assert definition_reference.get("label") == "§304.1.1"
    def_node_id = str(definition_reference.get("node_id") or "")
    provenance = row.get("value_provenance") or {}
    row_chips = provenance.get("reference_chips") or []
    assert row_chips, "expected value-side reference chips on the row"
    for chip in row_chips:
        assert chip.get("id") != def_node_id
        assert str(chip.get("label") or "") != "§304.1.1"


def test_phase1_through_phase3_guards_still_pass() -> None:
    """Ensure Phase 4 work does not drop Phase 1–3 guard modules from the suite."""
    import tests.api.test_flow_guidance_phase1a  # noqa: F401
    import tests.api.test_flow_guidance_phase2  # noqa: F401
    import tests.api.test_flow_guidance_phase3  # noqa: F401


def test_select_primary_reference_chip_collapses_multiple_chips() -> None:
    from api.reference_links import select_primary_reference_chip

    chips = [
        {"ref_type": "paragraph", "id": "304.1.1-b", "label": "§304.1.1"},
        {"ref_type": "table", "id": "asme_b31.3_A-1", "label": "Table A-1"},
    ]
    primary = select_primary_reference_chip(chips)
    assert len(primary) == 1
    assert primary[0]["ref_type"] == "table"
