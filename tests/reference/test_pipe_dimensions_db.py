"""Tests for pipe dimension SQLite databases and registry."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.pipe_dimension_lookup import PipeDimensionLookup
from engine.reference.pipe_dimensions_db import PipeDimensionsDatabase
from engine.reference.pipe_dimensions_registry import (
    load_pipe_dimensions_registry,
    resolve_pipe_dimension_db_path,
)
from scripts.build_pipe_dimensions_db import build_all


@pytest.fixture(scope="module")
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def built_db(project_root: Path) -> Path:
    build_all(standards_root=project_root / "standards")
    return project_root / "standards" / "asme" / "asme_b36.10" / "pipe_dimensions.db"


def test_registry_lists_asme_b36_10(project_root: Path) -> None:
    default_standard, sources = load_pipe_dimensions_registry(project_root / "standards")
    assert default_standard == "asme_b36.10"
    assert len(sources) == 1
    assert sources[0].table_id == "welded_seamless_pipe_dimensions"


def test_database_lookup_nps_2_schedule_40(built_db: Path) -> None:
    database = PipeDimensionsDatabase(built_db)
    row = database.lookup("welded_seamless_pipe_dimensions", "2", schedule="40")
    assert row.nps == "2"
    assert row.schedule == "40"
    assert row.outside_diameter_in == pytest.approx(2.375)
    assert row.wall_thickness_in == pytest.approx(0.154)
    assert row.standard_slug == "asme_b36.10"


def test_database_lookup_std_schedule_alias(built_db: Path) -> None:
    database = PipeDimensionsDatabase(built_db)
    row = database.lookup("welded_seamless_pipe_dimensions", '2"', schedule="STD")
    assert row.schedule == "40"
    assert row.wall_thickness_in == pytest.approx(0.154)


def test_pipe_dimension_lookup_uses_database(project_root: Path, built_db: Path) -> None:
    assert built_db.is_file()
    lookup = PipeDimensionLookup(project_root / "standards")
    result = lookup.lookup("4")
    assert result.outside_diameter_in == pytest.approx(4.500)
    assert result.standard_slug == "asme_b36.10"
    assert result.table_id == "welded_seamless_pipe_dimensions"


def test_resolve_pipe_dimension_db_path(project_root: Path, built_db: Path) -> None:
    path = resolve_pipe_dimension_db_path(project_root / "standards", "asme_b36.10")
    assert path == built_db
