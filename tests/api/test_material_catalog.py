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
    values = {item["value"] for item in results}
    labels = {item["label"] for item in results}

    assert any("106" in value.lower() for value in values)
    assert any("A106" in label for label in labels)


def test_search_finds_stainless_tp316(standards_root: Path) -> None:
    results = search_astm_materials(standards_root, "tp3")
    assert results
    assert any("TP316" in item["value"] or "TP304" in item["value"] for item in results)
    assert all(item["standard"].startswith("astm_") for item in results)
