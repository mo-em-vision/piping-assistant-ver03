"""Compatibility tests: nested primary YAML compiles like legacy sidecar merge."""

from __future__ import annotations

from pathlib import Path

import yaml

from engine.graph.graph_builder import _enrich_source_metadata
from engine.reference.node_block_extractor import extract_and_flatten_node_metadata


def test_paragraph_304_1_2_a_execution_block_compiles() -> None:
    path = Path(
        "knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.yaml"
    )
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        import yaml as _yaml

        parts = text.split("---", 2)
        meta = _yaml.safe_load(parts[1]) or {}
    else:
        meta = yaml.safe_load(text) or {}

    enriched = _enrich_source_metadata(path, meta)
    assert enriched.get("applicability")
    assert enriched.get("conditions")
    assert enriched.get("provisional_assumptions")
    assert enriched.get("subsections")


def test_workflow_inline_runtime_compiles() -> None:
    path = Path("workflows/pipe-wall-thickness.yaml")
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    meta = yaml.safe_load(parts[1]) or {}
    enriched = _enrich_source_metadata(path, meta)
    assert enriched.get("navigation")
    assert enriched.get("interactions")
    assert enriched.get("texts")


def test_validation_rule_execution_block_flattens() -> None:
    path = Path(
        "knowledge/standards/asme/asme_b31.3/nodes/validation_rule/"
        "asme-b313-304-1-1-valrule-a.yaml"
    )
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    meta = yaml.safe_load(parts[1]) or {}
    flat = extract_and_flatten_node_metadata(meta, "validation_rule")
    enriched = _enrich_source_metadata(path, meta)
    assert flat.get("variables")
    assert enriched.get("variables")
    assert enriched.get("steps")
