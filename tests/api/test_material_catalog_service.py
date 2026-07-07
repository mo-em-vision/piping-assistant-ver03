"""Tests for cached material catalog warm-up."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from api.material_catalog_service import (
    _cache_lock,
    _catalog_cache,
    _warm_cache,
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


def test_warm_rebuilds_missing_material_catalog(
    tmp_path: Path, project_root: Path
) -> None:
    standards_root = tmp_path / "knowledge" / "standards"
    materials_dir = tmp_path / "knowledge" / "global" / "materials"
    shutil.copytree(project_root / "knowledge" / "standards" / "astm", standards_root / "astm")
    shutil.copytree(project_root / "knowledge" / "global" / "materials", materials_dir)
    (materials_dir / "materials.db").unlink(missing_ok=True)

    with _cache_lock:
        _catalog_cache.clear()
        _warm_cache.clear()

    payload = warm_material_catalog(standards_root)
    assert payload["ready"] is True
    results = search_material_catalog(standards_root, "106")
    assert len(results) == 3
    assert {item["value"] for item in results} == {
        "astm_a106_gr_a",
        "astm_a106_gr_b",
        "astm_a106_gr_c",
    }
