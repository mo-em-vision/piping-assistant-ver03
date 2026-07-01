"""Tests for cached material catalog warm-up."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.material_catalog_service import (
    get_material_catalog,
    search_material_catalog,
    warm_material_catalog,
)


@pytest.fixture
def standards_root(project_root: Path) -> Path:
    return project_root / "knowledge" / "standards"


def test_warm_material_catalog_marks_catalog_ready(standards_root: Path) -> None:
    first = warm_material_catalog(standards_root)
    second = warm_material_catalog(standards_root)

    assert first["ready"] is True
    assert second["ready"] is True
    assert second["cached"] is True


def test_search_material_catalog_uses_cached_catalog(standards_root: Path) -> None:
    warm_material_catalog(standards_root)
    cached = get_material_catalog(standards_root)
    results = search_material_catalog(standards_root, "106")

    assert results
    assert cached.exists
