"""Contract tests for models.display_role authority module."""

from __future__ import annotations

import json
from pathlib import Path

from models.display_role import (
    DISPLAY_ROLE_ORDER,
    DisplayRole,
    DisplayState,
    EquationContent,
    infer_display_fields_from_block,
    infer_display_state,
    is_canonical_display_role,
    lifecycle_for_equation_state,
    report_role_index,
    resolve_display_block,
    sort_blocks_by_report_role,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_JSON = ROOT / "contracts" / "center_panel_report_role_order.json"


def test_display_role_order_matches_contract_json() -> None:
    payload = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    assert [role.value for role in DISPLAY_ROLE_ORDER] == payload


def test_canonical_roles_only() -> None:
    for role in DisplayRole:
        assert is_canonical_display_role(role.value)
    assert not is_canonical_display_role("equation_trace")
    assert not is_canonical_display_role("calculation_trace")


def test_equation_lifecycle_from_display_state() -> None:
    assert lifecycle_for_equation_state(DisplayState.preview.value) == "preview"
    assert lifecycle_for_equation_state(DisplayState.active.value) == "preview"
    assert lifecycle_for_equation_state(DisplayState.evaluated.value) == "durable"


def test_infer_equation_block_from_stable_id() -> None:
    block = infer_display_fields_from_block(
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display": "t_m = t + c",
        }
    )
    assert block["display_role"] == DisplayRole.equation.value
    assert block["display_state"] == DisplayState.preview.value
    assert block["lifecycle"] == "preview"


def test_resolve_strips_internal_display_role() -> None:
    resolved = resolve_display_block(
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.evaluated.value,
            "equation_content": EquationContent.symbolic.value,
            "internal_display_role": "equation_trace",
        }
    )
    assert "internal_display_role" not in resolved


def test_sort_blocks_single_equation_slot() -> None:
    blocks = [
        {"id": "equation-b", "display_role": "equation", "display_state": "evaluated"},
        {"id": "guidance-1", "display_role": "branch_narration"},
        {"id": "equation-a", "display_role": "equation", "display_state": "preview"},
    ]
    ordered = sort_blocks_by_report_role(blocks)
    assert [block["id"] for block in ordered] == ["guidance-1", "equation-a", "equation-b"]


def test_report_role_index_unknown_is_last() -> None:
    assert report_role_index("equation") < report_role_index("not_a_role")
    assert report_role_index("branch_narration") < report_role_index("equation")


def test_infer_preview_equation_from_path_preview_id() -> None:
    block = infer_display_fields_from_block(
        {
            "id": "path-preview-equation-304.1.2-a",
            "type": "equation",
            "display": "t = PD / 2(SEW + PY)",
        }
    )
    assert block["display_role"] == DisplayRole.equation.value
    assert infer_display_state(block) == DisplayState.preview.value
