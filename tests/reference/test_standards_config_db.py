"""Tests for compiled standards configuration database."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.material_catalog_db import load_material_registry, load_supplemental_materials
from engine.reference.pipe_dimensions_registry import load_pipe_dimensions_registry
from engine.reference.standards_config_db import StandardsConfigDatabase, standards_config_db_path
from scripts.build_standards_registry_db import build_all as build_registry


@pytest.fixture
def standards_root(project_root: Path) -> Path:
    return project_root / "knowledge" / "standards"


def test_build_registry_roundtrip(standards_root: Path) -> None:
    build_registry(standards_root=standards_root)
    database = StandardsConfigDatabase(standards_config_db_path(standards_root))
    assert database.exists
    sources = database.load_material_sources()
    assert any(source.standard == "astm_a106" for source in sources)
    supplemental = database.load_supplemental_materials()
    assert supplemental
    default_standard, pipe_sources = database.load_pipe_dimension_sources()
    assert pipe_sources


def test_loaders_prefer_config_db(standards_root: Path) -> None:
    build_registry(standards_root=standards_root)
    sources = load_material_registry(standards_root)
    assert {source.standard for source in sources} >= {
        "astm_a53",
        "astm_a106",
        "astm_a312",
    }
    supplemental = load_supplemental_materials(standards_root)
    assert supplemental
    _, pipe_sources = load_pipe_dimensions_registry(standards_root)
    assert pipe_sources
