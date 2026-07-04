"""Tests for standards pack metadata inheritance."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_builder import GraphBuilder
from engine.reference.pack_metadata import apply_pack_metadata, load_pack_metadata


def test_load_pack_metadata_for_asme_b31_3() -> None:
    pack_root = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
    )
    pack = load_pack_metadata(pack_root)
    assert pack.get("source_language") == "en"
    assert pack.get("authority") == "AUTH-ASME-B31.3"


def test_apply_pack_metadata_sets_text_source_language() -> None:
    pack = {"source_language": "en"}
    metadata = {"text": {"original": "sample"}}
    merged = apply_pack_metadata(metadata, pack)
    assert merged["text"]["source_language"] == "en"


def test_graph_builder_inherits_pack_source_language() -> None:
    pack_root = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
    )
    graph = GraphBuilder(pack_root).build()
    meta = graph.nodes["302.3.3-a"].metadata
    assert meta["text"]["source_language"] == "en"
