"""Tests for node context and standards node API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.node_context import active_node_context_for_task, node_source_payload, subsection_source_payload
from api.node_display import build_activated_node_blocks
from api.serializers import task_state
from api.workflow_bootstrap import bootstrap_new_task
from config.loader import CLIConfig
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "standards", standard="asme_b31.3")


def test_node_source_payload_includes_body(standards_reader: StandardsReader) -> None:
    payload = node_source_payload(standards_reader, "B313-304.1.1")

    assert payload["node_id"] == "B313-304.1.1"
    assert payload["paragraph"] == "304.1.1"
    assert "304.1.1" in payload["body"]
    assert "t_m = t + c" in payload["body"]
    assert payload["hover_excerpt"]


def test_active_node_context_uses_display_heading(standards_reader: StandardsReader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-ctx01", status=TaskStatus.AWAITING_INPUT)
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=Path("sessions"),
        standards_root=standards_reader.standards_root,
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    bootstrap_new_task(task, "pipe_wall_thickness_design", config)
    manager.replace_task(task.task_id, task)

    context = active_node_context_for_task(task, standards_reader)
    assert context is not None
    assert context["node_id"] == "B313-304.1.1"
    assert "Calculation of Minimum Required Thickness" in context["display_heading"]
    assert "304.1.1" in context["display_heading"]

    state = task_state(task, manager, standards_root=standards_reader.standards_root)
    assert state["active_node_context"]["display_heading"] == context["display_heading"]


def test_get_standards_node_endpoint(tmp_path: Path, project_root: Path) -> None:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    service = DesktopApiService(config=config, session_id="default")
    payload = service.get_standards_node("B313-304.1.1")

    assert payload["node_id"] == "B313-304.1.1"
    assert payload["body"]


def test_subsection_source_payload_for_302_3_3_b(standards_reader: StandardsReader) -> None:
    payload = subsection_source_payload(standards_reader, "B313-302.3.3", "b")

    assert payload["node_id"] == "B313-302.3.3"
    assert payload["subsection_id"] == "b"
    assert payload["subsection_paragraph"] == "302.3.3(b)"
    assert payload["subsection_title"] == "Basic Quality Factors"
    assert "Table A-1A" in payload["body"]
    assert "Increased Quality Factors" not in payload["body"]


def test_node_source_payload_for_302_3_3c_note_1(standards_reader: StandardsReader) -> None:
    payload = node_source_payload(standards_reader, "B313-note-302-3-3C-1")

    assert payload["node_id"] == "B313-note-302-3-3C-1"
    assert payload["paragraph"] == "Table 302.3.3C, Note (1)"
    assert "6.3" in payload["body"]
    assert "ASME B46.1" in payload["body"]
    assert "Table 302.3.3C" in payload["body"]


def test_node_source_payload_for_302_3_3c_note_2a(standards_reader: StandardsReader) -> None:
    payload = node_source_payload(standards_reader, "B313-note-302-3-3C-2a")

    assert payload["node_id"] == "B313-note-302-3-3C-2a"
    assert payload["paragraph"] == "Table 302.3.3C, Note (2)(a)"
    assert "ASTM E709" in payload["body"]
    assert "MSS SP-53" in payload["body"]
    assert "ferromagnetic" in payload["body"]


def test_subsection_source_payload_for_302_3_3_c(standards_reader: StandardsReader) -> None:
    payload = subsection_source_payload(standards_reader, "B313-302.3.3", "c")

    assert payload["subsection_id"] == "c"
    assert "Table 302.3.3C" in payload["body"]
    assert "node:B313-note-302-3-3C-2a" in payload["body"]
    assert "General" not in payload["body"]


def test_302_3_3_nomenclature_links_subsections(standards_reader: StandardsReader) -> None:
    record = standards_reader.load("B313-302.3.3")
    ec = next(
        item
        for item in record.metadata.get("nomenclature", [])
        if isinstance(item, dict) and item.get("symbol") == "E_c"
    )
    subsection_ids = {
        ref.get("subsection")
        for ref in ec.get("references", [])
        if isinstance(ref, dict) and ref.get("subsection")
    }
    assert subsection_ids == {"a", "b", "c"}


def test_subsection_source_payload_for_302_3_5_e(standards_reader: StandardsReader) -> None:
    payload = subsection_source_payload(standards_reader, "B313-302.3.5", "e")

    assert payload["node_id"] == "B313-302.3.5"
    assert payload["subsection_id"] == "e"
    assert payload["subsection_paragraph"] == "302.3.5(e)"
    assert payload["subsection_title"] == "Weld Joint Strength Reduction Factor"
    assert "Weld Joint Strength Reduction Factor" in payload["body"]
    assert "Unlisted Weld Strength Reduction Factors" not in payload["body"]


def test_get_standards_node_subsection_endpoint(tmp_path: Path, project_root: Path) -> None:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    service = DesktopApiService(config=config, session_id="default")
    payload = service.get_standards_node_subsection("B313-302.3.5", "e")

    assert payload["subsection_id"] == "e"
    assert payload["body"]
    assert "Unlisted Weld Strength Reduction Factors" not in payload["body"]


def test_build_activated_node_blocks_omits_reference_header(
    standards_reader: StandardsReader,
) -> None:
    blocks = build_activated_node_blocks(standards_reader, "B313-304.1.1")
    ids = [block["id"] for block in blocks]

    assert not any(block_id.startswith("node-activation-reference-") for block_id in ids)
    equation_blocks = [block for block in blocks if block["type"] == "equation"]
    assert equation_blocks
    assert any(block.get("nomenclature_reference") for block in equation_blocks)
    assert not any(block.get("reference_links") for block in blocks if block["type"] == "text")
