"""Tests for display block lifecycle metadata and preview dedupe."""

from __future__ import annotations

from api.display_block_metadata import (
    DISPLAY_CHANNEL_CURRENT_EQUATION_PREVIEW,
    LIFECYCLE_DURABLE,
    LIFECYCLE_PREVIEW,
    dedupe_preview_tier_equations,
    infer_lifecycle,
    tag_display_block,
)


def test_dedupe_competing_activation_when_path_preview_exists() -> None:
    from api.display_block_metadata import dedupe_competing_equation_preview_blocks, tag_display_block

    activation = tag_display_block(
        {
            "id": "node-activation-equation-304.1.2-a-fallback",
            "type": "equation",
            "display": "t = PD / 2(SEW + PY)",
        },
        display_role="activation",
        equation_node_id="asme-b313-304-1-2-eq-3a",
        source_node_id="304.1.2-a",
    )
    preview = tag_display_block(
        {
            "id": "path-preview-equation-304.1.2-a",
            "type": "equation",
            "display": "t = PD / 2(SEW + PY)",
        },
        display_role="preview",
        equation_node_id="asme-b313-304-1-2-eq-3a",
        source_node_id="304.1.2-a",
    )
    result = dedupe_competing_equation_preview_blocks([activation, preview])
    assert [block["id"] for block in result] == ["path-preview-equation-304.1.2-a"]


def test_stable_equation_block_lifecycle() -> None:
    block = tag_display_block(
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display": "t_m = t + c",
        },
        display_role="equation_trace",
        equation_node_id="asme-b313-304-1-1-eq-2",
        source_node_id="304.1.1-a",
    )

    assert block["lifecycle"] == LIFECYCLE_DURABLE
    assert block["history_eligible"] is True
    assert block.get("display_channel") is None
    assert block["equation_node_id"] == "asme-b313-304-1-1-eq-2"


def test_path_preview_intro_is_preview_not_durable_intro() -> None:
    block = tag_display_block(
        {
            "id": "path-preview-intro-304.1.2-a",
            "type": "text",
            "content": "Minimum required wall thickness based on",
        },
        display_role="intro",
        source_node_id="304.1.2-a",
    )

    assert block["lifecycle"] == LIFECYCLE_PREVIEW
    assert block["display_channel"] == "current_node_intro"


def test_conclusion_block_stays_durable() -> None:
    block = tag_display_block(
        {
            "id": "minimum-thickness-conclusion",
            "type": "text",
            "content": "Minimum required pipe wall thickness is 2.252 mm.",
        },
        display_role="conclusion",
    )

    assert block["lifecycle"] == LIFECYCLE_DURABLE
    assert block["history_eligible"] is True


def test_dedupe_preview_vs_activation_keeps_input_table() -> None:
    blocks = [
        {
            "id": "node-activation-equation-304.1.1-a-fallback",
            "type": "equation",
            "display_role": "activation",
            "lifecycle": "preview",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "variables": [{"symbol": "t"}, {"symbol": "c"}],
        },
        {
            "id": "path-preview-equation-304.1.1-a",
            "type": "equation",
            "display_role": "preview",
            "lifecycle": "preview",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "input_table": {"columns": [], "rows": [{"symbol": "t"}, {"symbol": "c"}]},
        },
    ]

    deduped = dedupe_preview_tier_equations(blocks)
    ids = [block["id"] for block in deduped]

    assert ids == ["path-preview-equation-304.1.1-a"]
    winner = deduped[0]
    assert "input_table" in winner
    assert "variables" not in winner


def test_dedupe_blocks_by_id_prefers_evaluated_equation() -> None:
    from api.display_block_metadata import dedupe_blocks_by_id_prefer_richer

    blocks = [
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display_role": "equation_trace",
            "lifecycle": "durable",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "input_table": {"columns": [], "rows": []},
        },
        {
            "id": "equation-asme-b313-304-1-1-eq-2",
            "type": "equation",
            "display_role": "equation_trace",
            "lifecycle": "durable",
            "equation_node_id": "asme-b313-304-1-1-eq-2",
            "display": "t_m = 2.252",
            "equation_display_trace": {
                "status": "evaluated",
                "result_latex": "2.252\\ \\mathrm{mm}",
            },
        },
    ]

    deduped = dedupe_blocks_by_id_prefer_richer(blocks)
    assert len(deduped) == 1
    assert deduped[0]["display"] == "t_m = 2.252"


def test_infer_lifecycle_legacy_preview_ids_without_metadata() -> None:
    legacy = {
        "id": "node-activation-equation-B313-304.1.1-0",
        "type": "equation",
        "display": "t_m = t + c",
    }

    assert infer_lifecycle(legacy) == LIFECYCLE_PREVIEW
