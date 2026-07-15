#!/usr/bin/env python3

"""Build the ASME B31.3 standards lookup tables SQLite database."""



from __future__ import annotations



import sys

from pathlib import Path



_ROOT = Path(__file__).resolve().parents[1]

if str(_ROOT) not in sys.path:

    sys.path.insert(0, str(_ROOT))



from engine.reference.asme_b31_3_table_ids import (

    TABLE_302_3_3_1,
    TABLE_302_3_3_2,
    TABLE_302_3_5_1,

    TABLE_304_1_1_1,

    TABLE_A_1,

    TABLE_A_2,

    TABLE_A_3,

)

from engine.reference.material_ids import (
    API_5L,
    ASTM_A105,
    ASTM_A106_GR_A,
    ASTM_A106_GR_B,
    ASTM_A106_GR_C,
    ASTM_A351,
    ASTM_A451,
    ASTM_A487,
    ASTM_A53,
)

from engine.reference.pack_tables_db import resolve_pack_tables_db

from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_tables import StandardsTablesDatabase



_PACK_ROOT = _ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3"

_DB_PATH = resolve_pack_tables_db(_PACK_ROOT)


def _option_queries_from_table_yaml(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    queries = meta.get("option_queries")
    return dict(queries) if isinstance(queries, dict) else {}


_TABLE_A_3_OPTION_QUERIES = _option_queries_from_table_yaml(
    _PACK_ROOT / "nodes" / "tables" / "asme-b313-table-A-3.yaml"
)

# B31.3 Table A-2 base-metal group headings (row field: base_metal_group).
BASE_METAL_GROUP_STAINLESS_STEEL = "Stainless Steel"
BASE_METAL_GROUP_IRON = "Iron"
BASE_METAL_GROUP_CARBON_STEEL = "Carbon steel"
BASE_METAL_GROUP_LOW_AND_INTERMEDIATE_ALLOY_STEEL = "Low and Intermediate Alloy Steel"
BASE_METAL_GROUP_COPPER_AND_COPPER_ALLOY = "Copper and Copper Alloy"
BASE_METAL_GROUP_NICKEL_AND_NICKEL_ALLOY = "Nickel and Nickel Alloy"
BASE_METAL_GROUP_ALUMINUM_ALLOY = "Aluminum Alloy"

_TABLE_A_2_DESCRIPTION = (
    "These quality factors are determined in accordance with "
    "[para. 302.3.3-b](node:302.3.3-a-b). See also "
    "[para. 302.3.3-c](node:302.3.3-a-c) and "
    "[Table 302.3.3-1](table:asme_b31.3_302.3.3-1) for increased quality factors "
    "applicable in special cases. Specifications are ASTM."
)

_TABLE_302_3_3_1_DESCRIPTION = (
    "Increased casting quality factors per "
    "[para. 302.3.3-c](node:302.3.3-a-c). "
    "Notes to this table: "
    "[(1)](node:asme-b313-table-302-3-3-1-note-1), "
    "[(2)(a)](node:asme-b313-table-302-3-3-1-note-2a), "
    "[(2)(b)](node:asme-b313-table-302-3-3-1-note-2b), "
    "[(3)(a)](node:asme-b313-table-302-3-3-1-note-3a), "
    "[(3)(b)](node:asme-b313-table-302-3-3-1-note-3b)."
)

_TABLE_302_3_3_2_DESCRIPTION = (
    "Acceptance levels for castings per "
    "[para. 302.3.3-c](node:302.3.3-a-c)."
)





def _y_rows(points: list[tuple[float, float]]) -> list[dict[str, float]]:
    return [
        {
            "design_temperature": temperature_f,
            "coefficient_Y": coefficient_y,
        }
        for temperature_f, coefficient_y in points
    ]





_TABLE_304_1_1_MATERIALS = {

    "ferritic_steels": {

        "display_name": "Ferritic steels",

        "rows": _y_rows(
            [
                (900, 0.4),
                (950, 0.5),
                (1000, 0.7),
                (1050, 0.7),
                (1100, 0.7),
                (1150, 0.7),
                (1200, 0.7),
                (1250, 0.7),
            ]
        ),

    },

    "austenitic_steels": {

        "display_name": "Austenitic steels",

        "rows": _y_rows(
            [
                (900, 0.4),
                (950, 0.4),
                (1000, 0.4),
                (1050, 0.4),
                (1100, 0.5),
                (1150, 0.7),
                (1200, 0.7),
                (1250, 0.7),
            ]
        ),

    },

    "nickel_alloys": {

        "display_name": "Nickel alloys",

        "rows": _y_rows(
            [
                (900, 0.4),
                (950, 0.4),
                (1000, 0.4),
                (1050, 0.4),
                (1100, 0.4),
                (1150, 0.4),
                (1200, 0.5),
                (1250, 0.7),
            ]
        ),

    },

    "gray_iron": {

        "display_name": "Gray iron",

        "rows": _y_rows([(900, 0.0)]),

    },

    "other_ductile_metals": {

        "display_name": "Other ductile metals",

        "rows": _y_rows(
            [
                (900, 0.4),
                (950, 0.4),
                (1000, 0.4),
                (1050, 0.4),
                (1100, 0.4),
                (1150, 0.4),
                (1200, 0.4),
                (1250, 0.4),
            ]
        ),

    },

}



_STRESS_MATERIALS = {

    ASTM_A106_GR_B: {

        "display_name": "ASTM A106 Grade B",

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
    database.clear_all_tables()

    database.upsert_table(

        table_id=TABLE_A_1,

        title="Table A-1 — Allowable Stress (sample)",

        version="1.0",

        unit="Pa",

        temperature_unit="F",

        interpolation=True,

        keys=["material_id", "design_temperature"],

        layout="material_rows",

        source_node="B313-table-A-1",

        aliases=[

            "A-1",

            "table_b31_3_A1",

            "nodes/B313-table-A-1/tables/A-1.yaml",

            "nodes/B313-table-A-1/tables/A-1",

            "material_allowable_stress",

            "tables/material_allowable_stress.yaml",

            "tables/material_allowable_stress",

        ],

        materials=_STRESS_MATERIALS,

    )



    database.upsert_table(

        table_id=TABLE_A_2,

        title="Table A-2 — Basic Casting Quality Factors, E_c",

        version="1.0",

        keys=["material_id", "base_metal_group"],

        layout="flat_rows",

        source_node="B313-table-A-2",

        metadata={"description": _TABLE_A_2_DESCRIPTION},

        aliases=[

            "A-2",

            "A-1A",

            "table_b31_3_A-2",

            "table_b31_3_A-1A",

            "nodes/tables/B313-table-A-2.yaml",

            "nodes/B313-table-A-1A/tables/A-1A.yaml",

            "nodes/B313-table-A-1A/tables/A-1A",

        ],

        rows=[

            {
                "material_id": ASTM_A351,
                "base_metal_group": BASE_METAL_GROUP_STAINLESS_STEEL,
                "description": "Austenitic steel castings",
                "quality_factor_E_c": 0.8,
            },
            {
                "material_id": ASTM_A451,
                "base_metal_group": BASE_METAL_GROUP_STAINLESS_STEEL,
                "description": "Centrifugally cast pipe",
                "quality_factor_E_c": 0.9,
            },
            {
                "material_id": ASTM_A487,
                "base_metal_group": BASE_METAL_GROUP_STAINLESS_STEEL,
                "description": "Steel castings",
                "quality_factor_E_c": 0.8,
            },
        ],

    )



    database.upsert_table(

        table_id=TABLE_A_3,

        title="Table A-3 — Basic Quality Factors for Longitudinal Weld Joints in Pipes and Tubes, E_j",

        version="1.0",

        keys=["material_id", "joint_category"],

        layout="flat_rows",

        source_node="B313-table-A-3",

        metadata={"option_queries": _TABLE_A_3_OPTION_QUERIES} if _TABLE_A_3_OPTION_QUERIES else None,

        aliases=[

            "A-3",

            "A-1B",

            "asme-b313-table-A-3",

            "table_b31_3_A-3",

            "table_b31_3_A_1B",

            "nodes/tables/B313-table-A-3.yaml",

            "nodes/B313-table-A-1B/tables/A-1B.yaml",

            "nodes/B313-table-A-1B/tables/A-1B",

        ],

        rows=[

            {
                "material_id": ASTM_A53,
                "class": "Type S",
                "joint_category": "Seamless pipe",
                "quality_factor_E": 1.0,
            },
            {
                "material_id": ASTM_A53,
                "class": "Type E",
                "joint_category": "Electric resistance welded pipe",
                "quality_factor_E": 0.85,
            },
            {
                "material_id": ASTM_A53,
                "class": "Type F",
                "joint_category": "Furnace butt welded pipe",
                "quality_factor_E": 0.6,
            },
            {
                "material_id": ASTM_A105,
                "joint_category": "Forgings",
                "quality_factor_E": 0.6,
            },
            {
                "material_id": ASTM_A106_GR_A,
                "joint_category": "Seamless pipe",
                "quality_factor_E": 1.0,
            },
            {
                "material_id": ASTM_A106_GR_B,
                "joint_category": "Seamless pipe",
                "quality_factor_E": 1.0,
            },
            {
                "material_id": ASTM_A106_GR_C,
                "joint_category": "Seamless pipe",
                "quality_factor_E": 1.0,
            },
            {
                "material_id": API_5L,
                "joint_category": "Seamless pipe",
                "quality_factor_E": 1.0,
            },
            {
                "material_id": API_5L,
                "joint_category": "Electric fusion welded pipe, 100% radiographed",
                "quality_factor_E": 1.0,
            },
            {
                "material_id": API_5L,
                "joint_category": "Electric resistance welded pipe",
                "quality_factor_E": 0.85,
            },
            {
                "material_id": API_5L,
                "joint_category": "Electric fusion welded pipe, double butt seam",
                "quality_factor_E": 0.95,
            },
            {
                "material_id": API_5L,
                "joint_category": "Continuous welded (furnace butt welded) pipe",
                "quality_factor_E": 0.6,
            },

        ],

    )



    database.upsert_table(

        table_id=TABLE_304_1_1_1,

        title="Table 304.1.1-1 — Values of Coefficient Y for t < D/6",

        version="1.0",

        temperature_unit="F",

        interpolation=True,

        keys=["material_id", "design_temperature"],

        layout="material_rows",

        source_node="B313-table-304-1-1-1",

        aliases=[

            "asme_b31.3_table_304_1_1",

            "table_304_1_1",

            "B313-table-304-1-1",

            "nodes/tables/B313-table-304-1-1.yaml",

            "nodes/B313-table-304-1-1/tables/table_304_1_1.yaml",

            "nodes/B313-table-304-1-1/tables/table_304_1_1",

            "asme_table_304_1_1",

            "asme-b313-table-304-1-1-1",

        ],

        materials=_TABLE_304_1_1_MATERIALS,

    )



    database.upsert_table(

        table_id=TABLE_302_3_5_1,

        title="Table 302.3.5-1 — Weld Joint Strength Reduction Factor, W",

        version="1.0",

        subsection="302.3.5-e",

        temperature_unit="F",

        interpolation=True,

        keys=["material_id", "design_temperature"],

        layout="flat_rows",

        source_node="B313-table-302-3-5-1",

        aliases=[

            "asme_b31.3_302.3.5",

            "302.3.5",

            "B313-table-302-3-5",

            "nodes/tables/B313-table-302-3-5.yaml",

            "nodes/B313-table-302-3-5/tables/302.3.5.yaml",

            "nodes/B313-table-302-3-5/tables/302.3.5",

        ],

        rows=[],

    )



    database.upsert_table(
        table_id=TABLE_302_3_3_1,
        title="Increased Casting Quality Factors, E_c",
        version="1.0",
        keys=["supplementary_examination"],
        layout="flat_rows",
        source_node="asme-b313-table-302-3-3-1",
        metadata={"description": _TABLE_302_3_3_1_DESCRIPTION},
        aliases=[
            "302.3.3-1",
            "302.3.3C",
            "table_302_3_3C",
            "asme_b31.3_table_302_3_3C",
            "B313-table-302-3-3C",
            "nodes/tables/asme-b313-table-302-3-3-1.yaml",
        ],
        rows=[],
    )

    database.upsert_table(
        table_id=TABLE_302_3_3_2,
        title="Acceptance Levels for Castings",
        version="1.0",
        keys=[
            "material_examined_thickness_T",
            "applicable_standard",
            "acceptance_level_or_class",
            "acceptable_discontinuities",
        ],
        layout="flat_rows",
        source_node="asme-b313-table-302-3-3-2",
        metadata={"description": _TABLE_302_3_3_2_DESCRIPTION},
        aliases=[
            "302.3.3-2",
            "302.3.3D",
            "nodes/tables/asme-b313-table-302-3-3-2.yaml",
        ],
        rows=[],
    )



    return database





if __name__ == "__main__":

    built = build_database()

    print(f"Built {built.db_path} with {len(built.list_table_ids())} tables")


