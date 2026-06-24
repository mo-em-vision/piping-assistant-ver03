"""API tests for ASTM material search."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.material_catalog import search_astm_materials


@pytest.fixture
def standards_root(project_root: Path) -> Path:
    return project_root / "standards"


def test_search_requires_three_characters(standards_root: Path) -> None:
    assert search_astm_materials(standards_root, "sa") == []
    assert search_astm_materials(standards_root, "  sa  ") == []


def test_search_finds_a106_grade_b_alias(standards_root: Path) -> None:
    results = search_astm_materials(standards_root, "106")
    labels = {item["label"] for item in results}
    a106 = [item for item in results if item["standard"] == "astm_a106"]

    assert len(a106) == 3
    assert labels == {
        "ASTM A106 Grade A",
        "ASTM A106 Grade B",
        "ASTM A106 Grade C",
    }
    assert {item["value"] for item in a106} == {"A106 Gr A", "A106 Gr B", "A106 Gr C"}


def test_search_finds_stainless_tp316(standards_root: Path) -> None:
    results = search_astm_materials(standards_root, "tp3")
    assert results
    assert any("TP316" in item["value"] or "TP304" in item["value"] for item in results)
    assert all(item["standard"].startswith("astm_") for item in results)
