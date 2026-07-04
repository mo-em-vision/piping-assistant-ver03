"""Tests for standards lookup table SQLite storage."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.asme_b31_3_table_ids import TABLE_A_1, TABLE_A_2, TABLE_A_1A
from engine.reference.material_ids import ASTM_A106_GR_B
from engine.reference.standards_reader import StandardsReader
from engine.reference.standards_tables import StandardsTablesDatabase


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_standards_tables_db_exists(standards_reader: StandardsReader) -> None:
    assert standards_reader.tables_db_path.is_file()


def test_resolve_legacy_yaml_alias(standards_reader: StandardsReader) -> None:
    data = standards_reader.load_table("nodes/asme-b313-table-A-1/tables/A-1.yaml")
    assert data["table_id"] == TABLE_A_1
    assert ASTM_A106_GR_B in data["materials"]


def test_load_table_by_id_returns_db_path(standards_reader: StandardsReader) -> None:
    path, data = standards_reader.load_table_by_id("A-1A")
    assert path.name in {"standards_tables.db", "tables.db"}
    assert data["table_id"] == TABLE_A_2
    assert TABLE_A_1A == TABLE_A_2


def test_material_catalog_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "tables.db"
    database = StandardsTablesDatabase(db_path)
    database.upsert_table(
        table_id="demo_catalog",
        title="Demo Catalog",
        layout="material_catalog",
        keys=["grade"],
        metadata={"standard": "Demo", "aliases": {"grade": {"B": "Grade B"}}},
        materials={
            "Grade B": {
                "display_name": "Grade B",
                "mechanical_properties": {
                    "room_temperature": {
                        "test_temperature_f": 70,
                        "tensile_strength_min": {"ksi": 60, "pa": 1.0},
                        "yield_strength_min": {"ksi": 35, "pa": 2.0},
                    }
                },
            }
        },
    )

    loaded = database.get_table("demo_catalog")
    assert loaded is not None
    assert loaded["standard"] == "Demo"
    assert loaded["materials"]["Grade B"]["display_name"] == "Grade B"


def test_material_rows_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "tables-rows.db"
    database = StandardsTablesDatabase(db_path)
    database.upsert_table(
        table_id="demo",
        title="Demo",
        layout="material_rows",
        keys=["material", "design_temperature"],
        materials={
            "SA-106B": {
                "display_name": "Sample",
                "rows": [{"design_temperature": 100, "allowable_stress": 1.0}],
            }
        },
    )

    loaded = database.get_table("demo")
    assert loaded is not None
    assert loaded["materials"]["SA-106B"]["rows"][0]["allowable_stress"] == 1.0
