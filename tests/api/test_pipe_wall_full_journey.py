"""Full API journey regression for pipe_wall_thickness_design."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.material_catalog_service import search_material_catalog, warm_material_catalog
from config.loader import CLIConfig
from engine.executor.unit_manager import convert_to_si
from engine.reference.pack_tables_db import resolve_pack_tables_db
from tests.api.conftest import api_session_id
from tests.helpers.lookup_resolution_contract import (
    assert_pipe_wall_lookup_resolution_in_final_state,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXPECTED_DIR = _REPO_ROOT / "tests" / "data" / "expected"

_PIPE_WALL_USER_SUBMISSIONS: list[tuple[str, object, str | None]] = [
    ("internal_design_gage_pressure", 8.0, "bar"),
    ("nominal_pipe_size", "6", None),
    ("material_grade", "SA-106B", None),
    ("design_temperature", 38.0, "C"),
    ("pipe_construction_type", "Seamless pipe", None),
]

_CORROSION_ALLOWANCE_SUBMISSION: tuple[str, object, str | None] = (
    "corrosion_allowance",
    0.0,
    "mm",
)


def _standards_db_available(project_root: Path | None = None) -> bool:
    root = project_root or _REPO_ROOT
    return resolve_pack_tables_db(root / "knowledge" / "standards" / "asme" / "asme_b31.3").exists()


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


def _submit_while_requested(
    service: DesktopApiService,
    task_id: str,
    session_id: str,
    submissions: list[tuple[str, object, str | None]],
) -> dict:
    state: dict = service.get_task(task_id, session_id)
    remaining = list(submissions)
    max_passes = max(len(remaining) * 4, 1)

    for _ in range(max_passes):
        if not remaining:
            break
        state = service.get_task(task_id, session_id)
        submittable = set(state.get("progress", {}).get("submittable_parameters") or [])
        still_remaining: list[tuple[str, object, str | None]] = []
        progressed = False
        for parameter, value, unit in remaining:
            if parameter not in submittable:
                still_remaining.append((parameter, value, unit))
                continue
            state = service.submit_input(
                task_id,
                parameter=parameter,
                value=value,
                unit=unit,
                session_id=session_id,
            )
            progressed = True
        remaining = still_remaining
        if not progressed:
            break
    return state


def _timeline_step(state: dict, step_id: str) -> dict | None:
    timeline = state.get("progress", {}).get("timeline") or []
    return next((step for step in timeline if step.get("id") == step_id), None)


def _api_fact_normalized_key(state: dict, key: str) -> str | None:
    fact = (state.get("facts") or {}).get(key)
    if not isinstance(fact, dict):
        return None
    value = fact.get("value")
    if isinstance(value, dict):
        normalized = value.get("normalized_key")
        if normalized:
            return str(normalized)
        label = value.get("label")
        if label:
            return str(label)
    if value is not None:
        return str(value)
    return None


def _api_fact_label(state: dict, key: str) -> str | None:
    fact = (state.get("facts") or {}).get(key)
    if not isinstance(fact, dict):
        return None
    value = fact.get("value")
    if isinstance(value, dict) and value.get("label"):
        return str(value["label"])
    display = fact.get("display_value")
    return str(display) if display else None


def _transcript_block_ids(state: dict) -> list[str]:
    blocks = state.get("flow_guidance", {}).get("transcript_blocks") or []
    return [str(block.get("block_id")) for block in blocks if isinstance(block, dict) and block.get("block_id")]


def _expected_thickness_m(
  *,
  pressure_bar: float,
  outside_diameter_mm: float,
  allowable_stress_pa: float,
  weld_efficiency: float = 1.0,
  w_factor: float = 1.0,
  y_coefficient: float = 0.4,
) -> float:
    p_pa, _ = convert_to_si(pressure_bar, "bar")
    d_m, _ = convert_to_si(outside_diameter_mm, "mm")
    sew = allowable_stress_pa * weld_efficiency * w_factor
    py = p_pa * y_coefficient
    return p_pa * d_m / (2.0 * (sew + py))


def test_material_catalog_warm_and_search(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    warm = warm_material_catalog(standards_root)
    assert warm["ready"] is True

    results = search_material_catalog(standards_root, "106", limit=5)
    assert results
    values = {item["value"] for item in results}
    assert "astm_a106_gr_b" in values


@pytest.mark.skipif(
    not _standards_db_available(),
    reason="standards_tables.db must be built for end-to-end pipe wall API journey",
)
def test_pipe_wall_full_api_journey(tmp_path: Path, project_root: Path) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id=session_id)
    task_id = created["task_id"]

    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        session_id=session_id,
    )
    straight = _timeline_step(state, "straight_pipe_section")
    assert straight is not None
    assert straight["status"] == "done"

    transcript_after_straight = _transcript_block_ids(state)

    state = service.submit_input(
        task_id,
        parameter="pressure_loading",
        value="internal_pressure",
        session_id=session_id,
    )
    pressure = _timeline_step(state, "pressure_loading")
    assert pressure is not None
    assert pressure["status"] == "done"
    assert pressure.get("display_value")

    transcript_after_pressure = _transcript_block_ids(state)
    assert transcript_after_pressure
    guidance_blocks = [
        block
        for block in state.get("flow_guidance", {}).get("transcript_blocks") or []
        if isinstance(block, dict) and block.get("kind") == "guidance"
    ]
    assert guidance_blocks

    state = _submit_while_requested(service, task_id, session_id, _PIPE_WALL_USER_SUBMISSIONS)

    material_step = _timeline_step(state, "material_grade")
    assert material_step is not None
    assert material_step["status"] == "done"
    assert material_step.get("display_value")

    assert _api_fact_normalized_key(state, "material_grade") == "astm_a106_gr_b"
    assert _api_fact_label(state, "metallurgical_group") == "ferritic_steels"

    allowable_stress = state.get("outputs", {}).get("allowable_stress")
    assert allowable_stress is not None
    assert float(allowable_stress) > 0.0

    assert "corrosion_allowance" in (state.get("progress", {}).get("submittable_parameters") or [])

    state = service.submit_input(
        task_id,
        parameter=_CORROSION_ALLOWANCE_SUBMISSION[0],
        value=_CORROSION_ALLOWANCE_SUBMISSION[1],
        unit=_CORROSION_ALLOWANCE_SUBMISSION[2],
        session_id=session_id,
    )

    assert state["status"] == "completed"
    assert_pipe_wall_lookup_resolution_in_final_state(state)

    required_thickness = state.get("outputs", {}).get("required_thickness")
    thickness_t = state.get("outputs", {}).get("t")
    t_m = state.get("outputs", {}).get("t_m")
    minimum_required_thickness = state.get("outputs", {}).get("minimum_required_thickness")

    assert required_thickness is not None
    assert thickness_t is not None
    assert t_m is not None
    assert minimum_required_thickness is not None

    expected_t = _expected_thickness_m(
        pressure_bar=8.0,
        outside_diameter_mm=168.3,
        allowable_stress_pa=float(allowable_stress),
    )
    assert abs(float(required_thickness) - expected_t) <= 1e-3
    assert abs(float(thickness_t) - expected_t) <= 1e-3
    assert abs(float(t_m) - expected_t) <= 1e-3
    assert abs(float(minimum_required_thickness) - expected_t) <= 1e-3

    thickness_step = _timeline_step(state, "thickness")
    assert thickness_step is not None
    assert thickness_step["status"] == "done"

    display_outputs = state.get("display_outputs") or []
    assert display_outputs
    assert any(
        block.get("display_role") == "equation" or block.get("kind") == "equation"
        for block in display_outputs
        if isinstance(block, dict)
    )

    result_summary_blocks = [
        block
        for block in display_outputs
        if isinstance(block, dict) and block.get("display_role") == "result_summary"
    ]
    assert len(result_summary_blocks) == 1
    summary = result_summary_blocks[0]
    summary_content = str(summary.get("content") or "")
    assert "t_m =" in summary_content
    assert "Applied standard:" in summary_content
    assert "ASME B31.3 §304.1.1" in summary_content
    assert "ASME B31.3 §304.1.2" in summary_content
    assert "The following assumptions have been made in the calculation:" in summary_content
    assert "Applied conditions:" not in summary_content
    summary_payload = summary.get("payload") or {}
    assert summary_payload.get("documentation_summary")
    assert summary_payload.get("applied_paragraphs")
    assert summary_payload.get("assumptions")

    transcript_after_inputs = _transcript_block_ids(state)
    assert transcript_after_inputs
    for block_id in transcript_after_straight:
        assert block_id in transcript_after_inputs
    for block_id in transcript_after_pressure:
        assert block_id in transcript_after_inputs

    reloaded = service.get_task(task_id, session_id=session_id)
    assert _transcript_block_ids(reloaded) == transcript_after_inputs
    assert reloaded.get("display_outputs") is not reloaded.get("flow_guidance", {}).get("transcript_blocks")

    report_step = _timeline_step(state, "report")
    assert report_step is not None
    assert report_step["status"] == "done"

    report_structure = json.loads(
        (_EXPECTED_DIR / "pipe_wall_thickness_report_structure.json").read_text(encoding="utf-8")
    )
    generated = service.generate_task_report(task_id, report_format="html", session_id=session_id)
    assert generated["generation_status"] == "ready"
    assert generated["files"]["html"]["available"] is True

    preview = service.preview_task_report(task_id, preview_format="html", session_id=session_id)
    content = preview.get("content") or ""
    for section in report_structure["required_sections"]:
        assert section in content
