"""Tests for global material catalog database."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.material_catalog_db import (
    GlobalMaterialCatalog,
    load_material_registry,
    search_materials,
)


@pytest.fixture
def standards_root(project_root: Path) -> Path:
    return project_root / "knowledge" / "standards"


def test_astm_pack_has_material_table_dbs(project_root: Path) -> None:
    pack = project_root / "knowledge" / "standards" / "astm"
    assert (pack / "astm_a106.db").is_file()
    assert (pack / "astm_a53_tables.db").is_file()


def test_material_registry_db_path_for_astm_a106(project_root: Path) -> None:
    sources = load_material_registry(project_root / "knowledge" / "standards")
    a106 = next(source for source in sources if source.standard == "astm_a106")
    assert a106.db_relative_path == "astm/astm_a106.db"


def test_load_material_registry_includes_astm_sources(standards_root: Path) -> None:
    sources = load_material_registry(standards_root)
    slugs = {source.standard for source in sources}
    assert "astm_a53" in slugs
    assert "astm_a106" in slugs
    assert "astm_a312" in slugs


def test_global_catalog_search_finds_a53_and_api_5l(standards_root: Path) -> None:
    a53 = search_materials(standards_root, "a53")
    assert any(item["value"] == "astm_a53" for item in a53)
    api = search_materials(standards_root, "api 5")
    assert any(item["value"] == "api_5l" for item in api)


def test_global_catalog_search_finds_a106_alias(standards_root: Path) -> None:
    results = search_materials(standards_root, "106")
    a106 = [item for item in results if item["standard"] == "astm_a106"]

    assert len(a106) == 3
    assert {item["label"] for item in a106} == {
        "ASTM A106 Grade A",
        "ASTM A106 Grade B",
        "ASTM A106 Grade C",
    }


def test_global_catalog_search_finds_a312(standards_root: Path) -> None:
    results = search_materials(standards_root, "a312")
    assert any(item["value"].startswith("astm_a312") for item in results)


def test_global_catalog_search_finds_tp316(standards_root: Path) -> None:
    results = search_materials(standards_root, "tp3")
    assert results
    assert any(
        "tp316" in item["value"] or "tp304" in item["value"] for item in results
    )


def test_rebuild_global_catalog(tmp_path: Path, project_root: Path) -> None:
    import shutil

    root = tmp_path / "standards"
    global_root = tmp_path / "global"
    shutil.copytree(project_root / "knowledge" / "standards" / "astm", root / "astm")
    shutil.copytree(project_root / "knowledge" / "global" / "materials", global_root / "materials")

    catalog = GlobalMaterialCatalog(root)
    count = catalog.rebuild()
    assert count > 0
    assert catalog.exists
    assert search_materials(root, "sa-106")
