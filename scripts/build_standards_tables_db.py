#!/usr/bin/env python3
"""Build the ASME B31.3 standards lookup tables SQLite database."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.reference.standards_tables import StandardsTablesDatabase

_PACK_ROOT = _ROOT / "standards" / "asme" / "asme_b31.3"
_DB_PATH = resolve_pack_tables_db(_PACK_ROOT)

_STRESS_MATERIALS = {
    "SA-106B": {
        "display_name": "SA-106 Grade B (sample)",
        "rows": [
            {"design_temperature": 100, "allowable_stress": 207_000_000},
            {"design_temperature": 200, "allowable_stress": 193_000_000},
            {"design_temperature": 300, "allowable_stress": 186_000_000},
            {"design_temperature": 400, "allowable_stress": 179_000_000},
        ],
    },
    "A106-B": {
        "display_name": "A106 Grade B (sample alias)",
        "rows": [
            {"design_temperature": 100, "allowable_stress": 207_000_000},
            {"design_temperature": 200, "allowable_stress": 193_000_000},
            {"design_temperature": 300, "allowable_stress": 186_000_000},
            {"design_temperature": 400, "allowable_stress": 179_000_000},
        ],
    },
}


def build_database(db_path: Path = _DB_PATH) -> StandardsTablesDatabase:
    database = StandardsTablesDatabase(db_path)
    if db_path.exists():
        db_path.unlink()

    database.upsert_table(
        table_id="A-1",
        title="Table A-1 — Allowable Stress (sample)",
        version="1.0",
        unit="Pa",
        temperature_unit="F",
        interpolation=True,
        keys=["material", "design_temperature"],
        layout="material_rows",
        source_node="B313-table-A-1",
        aliases=[
            "table_b31_3_A1",
            "nodes/B313-appendix_A/tables/A-1.yaml",
            "nodes/B313-appendix_A/tables/A-1",
        ],
        materials=_STRESS_MATERIALS,
    )

    database.upsert_table(
        table_id="material_allowable_stress",
        title="Sample Material Allowable Stress",
        version="1.0",
        unit="Pa",
        temperature_unit="F",
        interpolation=True,
        keys=["material", "design_temperature"],
        layout="material_rows",
        source_node="B313-material-stress",
        aliases=[
            "tables/material_allowable_stress.yaml",
            "tables/material_allowable_stress",
        ],
        materials=_STRESS_MATERIALS,
    )

    database.upsert_table(
        table_id="A-1A",
        title="Table A-1A — Quality Factors for Seamless Pipe (sample)",
        version="1.0",
        keys=["material", "joint_category"],
        layout="flat_rows",
        source_node="B313-table-A-1A",
        aliases=[
            "table_b31_3_A-1A",
            "nodes/B313-appendix_A/tables/A-1A.yaml",
            "nodes/B313-appendix_A/tables/A-1A",
        ],
        rows=[
            {"material": "SA-106B", "joint_category": "seamless", "quality_factor_E": 1.0},
            {"material": "A106-B", "joint_category": "seamless", "quality_factor_E": 1.0},
        ],
    )

    database.upsert_table(
        table_id="A-1B",
        title="Table A-1B — Quality Factors for Welded Pipe and Forgings (sample)",
        version="1.0",
        keys=["material", "joint_category"],
        layout="flat_rows",
        source_node="B313-table-A-1B",
        aliases=[
            "table_b31_3_A_1B",
            "nodes/B313-appendix_A/tables/A-1B.yaml",
            "nodes/B313-appendix_A/tables/A-1B",
        ],
        rows=[
            {"material": "SA-106B", "joint_category": "seamless", "quality_factor_E": 1.0},
            {"material": "A106-B", "joint_category": "seamless", "quality_factor_E": 1.0},
            {"material": "SA-105", "joint_category": "forging", "quality_factor_E": 1.0},
            {"material": "SA-106B", "joint_category": "erw", "quality_factor_E": 0.85},
            {
                "material": "SA-106B",
                "joint_category": "furnace_butt_welded",
                "quality_factor_E": 0.60,
            },
        ],
    )

    database.upsert_table(
        table_id="table_304_1_1",
        title="Table 304.1.1 — Temperature Coefficient Y (sample)",
        version="1.0",
        temperature_unit="F",
        interpolation=True,
        keys=["design_temperature"],
        layout="flat_rows",
        source_node="B313-table-304-1-1",
        aliases=[
            "nodes/B313-304.1.1/tables/table_304_1_1.yaml",
            "nodes/B313-304.1.1/tables/table_304_1_1",
        ],
        rows=[
            {"design_temperature": 100, "coefficient_Y": 0.4},
            {"design_temperature": 200, "coefficient_Y": 0.4},
            {"design_temperature": 300, "coefficient_Y": 0.4},
            {"design_temperature": 400, "coefficient_Y": 0.4},
            {"design_temperature": 500, "coefficient_Y": 0.4},
            {"design_temperature": 600, "coefficient_Y": 0.4},
            {"design_temperature": 700, "coefficient_Y": 0.5},
            {"design_temperature": 800, "coefficient_Y": 0.5},
            {"design_temperature": 900, "coefficient_Y": 0.6},
        ],
    )

    database.upsert_table(
        table_id="302.3.5",
        title="Table 302.3.5 — Weld Joint Strength Reduction Factor W (sample)",
        version="1.0",
        subsection="302.3.5(e)",
        temperature_unit="F",
        interpolation=True,
        keys=["material", "design_temperature", "weld_joint_category"],
        layout="flat_rows",
        source_node="B313-table-302-3-5",
        aliases=[
            "nodes/B313-302.3.5/tables/302.3.5.yaml",
            "nodes/B313-302.3.5/tables/302.3.5",
        ],
        rows=[],
    )

    return database


if __name__ == "__main__":
    built = build_database()
    print(f"Built {built.db_path} with {len(built.list_table_ids())} tables")
