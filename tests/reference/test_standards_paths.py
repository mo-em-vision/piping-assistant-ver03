"""Tests for standards pack path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_paths import list_standard_packs, resolve_standard_pack


def test_resolve_grouped_asme_b31_3() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    pack = resolve_standard_pack(root, "asme_b31.3")
    assert pack.name == "asme_b31.3"
    assert pack.parent.name == "asme"
    assert (pack / "nodes" / "B313-304.1.1" / "node.md").exists()
    assert (pack / "nodes" / "B313-304.1.2" / "node.md").exists()


def test_resolve_grouped_asme_b36_10() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    pack = resolve_standard_pack(root, "asme_b36.10")
    assert pack.name == "asme_b36.10"
    assert (pack / "tables" / "welded_seamless_pipe_dimensions.yaml").exists()


def test_resolve_explicit_group_path() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    pack = resolve_standard_pack(root, "asme/asme_b31.3")
    assert pack.name == "asme_b31.3"


def test_resolve_unknown_raises() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    with pytest.raises(FileNotFoundError):
        resolve_standard_pack(root, "nonexistent_standard")


def test_list_standard_packs_includes_asme_samples() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    slugs = {slug for slug, _ in list_standard_packs(root)}
    assert "asme_b31.3" in slugs
    assert "asme_b36.10" in slugs
    assert "astm_a106" in slugs
    assert "astm_a312" in slugs


def test_resolve_grouped_astm_a106() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    pack = resolve_standard_pack(root, "astm_a106")
    assert pack.parent.name == "astm"
    assert (pack / "tables" / "material_properties.yaml").exists()
