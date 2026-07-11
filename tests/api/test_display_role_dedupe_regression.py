"""Regression tests for equation display_state dedupe and update-in-place."""

from __future__ import annotations

from api.display_block_metadata import (
    dedupe_blocks_by_id_prefer_richer,
    dedupe_competing_equation_preview_blocks,
    dedupe_equation_blocks_by_node_id,
    tag_equation_block,
)
from models.display_role import DisplayRole, DisplayState, EquationContent


def test_active_dropped_when_preview_exists_for_same_equation_node_id() -> None:
    activation = tag_equation_block(
        {
            "id": "node-activation-equation-304.1.2-a-fallback",
            "type": "equation",
            "display": "t = PD / 2(SEW + PY)",
        },
        display_state=DisplayState.active.value,
        equation_node_id="asme-b313-304-1-2-eq-3a",
        source_node_id="304.1.2-a",
    )
    preview = tag_equation_block(
        {
            "id": "path-preview-equation-304.1.2-a",
            "type": "equation",
            "display": "t = PD / 2(SEW + PY)",
        },
        display_state=DisplayState.preview.value,
        equation_node_id="asme-b313-304-1-2-eq-3a",
        source_node_id="304.1.2-a",
    )
    result = dedupe_competing_equation_preview_blocks([activation, preview])
    assert [block["id"] for block in result] == ["path-preview-equation-304.1.2-a"]


def test_preview_tier_dedupe_prefers_richer_input_table() -> None:
    blocks = [
        {
            "id": "node-activation-equation-304.1.1-a-fallback",
            "type": "equation",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.active.value,
            "lifecycle": "preview",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "variables": [{"symbol": "t"}, {"symbol": "c"}],
        },
        {
            "id": "path-preview-equation-304.1.1-a",
            "type": "equation",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.preview.value,
            "lifecycle": "preview",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "input_table": {"columns": [], "rows": [{"symbol": "t"}, {"symbol": "c"}]},
        },
    ]

    deduped = dedupe_equation_blocks_by_node_id(blocks)
    assert [block["id"] for block in deduped] == ["path-preview-equation-304.1.1-a"]
    assert "input_table" in deduped[0]
    assert "variables" not in deduped[0]


def test_same_stable_id_prefers_evaluated_richer_payload() -> None:
    blocks = [
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.evaluated.value,
            "lifecycle": "durable",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "input_table": {"columns": [], "rows": []},
        },
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display_role": DisplayRole.equation.value,
            "display_state": DisplayState.evaluated.value,
            "lifecycle": "durable",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display": "t_m = 2.252",
            "equation_content": EquationContent.evaluated.value,
            "equation_display_trace": {
                "status": "evaluated",
                "result_latex": "2.252\\ \\mathrm{mm}",
            },
        },
    ]

    deduped = dedupe_blocks_by_id_prefer_richer(blocks)
    assert len(deduped) == 1
    assert deduped[0]["display"] == "t_m = 2.252"
