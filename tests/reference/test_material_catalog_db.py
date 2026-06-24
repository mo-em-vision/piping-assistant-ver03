"""Tests for global material catalog database."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.material_catalog_db import (
    GlobalMaterialCatalog,
    load_material_registry,
    search_materials,
)
from engine.reference.pack_tables_db import resolve_pack_tables_db


@pytest.fixture
def standards_root(project_root: Path) -> Path:
    return project_root / "standards"


def test_resolve_pack_tables_db_prefers_slug_named_file(project_root: Path) -> None:
    pack = project_root / "standards" / "astm" / "astm_a106"
    assert resolve_pack_tables_db(pack).name == "astm_a106.db"


def test_load_material_registry_includes_astm_sources(standards_root: Path) -> None:
    sources = load_material_registry(standards_root)
    slugs = {source.standard for source in sources}
    assert "astm_a106" in slugs
    assert "astm_a312" in slugs


def test_global_catalog_search_finds_a106_alias(standards_root: Path) -> None:
    results = search_materials(standards_root, "106")
    a106 = [item for item in results if item["standard"] == "astm_a106"]

    assert len(a106) == 3
    assert {item["label"] for item in a106} == {
        "ASTM A106 Grade A",
        "ASTM A106 Grade B",
        "ASTM A106 Grade C",
    }


def test_global_catalog_search_finds_tp316(standards_root: Path) -> None:
    results = search_materials(standards_root, "tp3")
    assert results
    assert any("TP316" in item["value"] or "TP304" in item["value"] for item in results)


def test_rebuild_global_catalog(tmp_path: Path, project_root: Path) -> None:
    import shutil

    root = tmp_path / "standards"
    shutil.copytree(project_root / "standards" / "astm", root / "astm")
    shutil.copytree(project_root / "standards" / "materials", root / "materials")

    catalog = GlobalMaterialCatalog(root)
    count = catalog.rebuild()
    assert count > 0
    assert catalog.exists
    assert search_materials(root, "sa-106")
