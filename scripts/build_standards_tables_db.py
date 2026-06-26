#!/usr/bin/env python3

"""Build the ASME B31.3 standards lookup tables SQLite database."""



from __future__ import annotations



import sys

from pathlib import Path



_ROOT = Path(__file__).resolve().parents[1]

if str(_ROOT) not in sys.path:

    sys.path.insert(0, str(_ROOT))



from engine.reference.asme_b31_3_table_ids import (

    TABLE_302_3_5,

    TABLE_304_1_1,

    TABLE_A_1,

    TABLE_A_1A,

    TABLE_A_1B,

    TABLE_MATERIAL_ALLOWABLE_STRESS,

)

from engine.reference.material_ids import ASTM_A106_GR_B, ASME_SA_105

from engine.reference.pack_tables_db import resolve_pack_tables_db

from engine.reference.standards_tables import StandardsTablesDatabase



_PACK_ROOT = _ROOT / "standards" / "asme" / "asme_b31.3"

_DB_PATH = resolve_pack_tables_db(_PACK_ROOT)





def _celsius_to_fahrenheit(celsius: float) -> float:

    return celsius * 9.0 / 5.0 + 32.0





def _y_rows(points: list[tuple[float, float]]) -> list[dict[str, float]]:

    return [

        {

            "temperature_c": temperature_c,

            "design_temperature": _celsius_to_fahrenheit(temperature_c),

            "coefficient_Y": coefficient_y,

        }

        for temperature_c, coefficient_y in points

    ]





_TABLE_304_1_1_MATERIALS = {

    "ferritic_steels": {

        "display_name": "Ferritic steels",

        "rows": _y_rows(

            [

                (482, 0.4),

                (510, 0.5),

                (538, 0.7),

                (566, 0.7),

                (593, 0.7),

                (621, 0.7),

                (649, 0.7),

                (677, 0.7),

            ]

        ),

    },

    "austenitic_steels": {

        "display_name": "Austenitic steels",

        "rows": _y_rows(

            [

                (482, 0.4),

                (510, 0.4),

                (538, 0.4),

                (566, 0.4),

                (593, 0.5),

                (621, 0.7),

                (649, 0.7),

                (677, 0.7),

            ]

        ),

    },

    "nickel_alloys": {

        "display_name": "Nickel alloys",

        "rows": _y_rows(

            [

                (482, 0.4),

                (510, 0.4),

                (538, 0.4),

                (566, 0.4),

                (593, 0.4),

                (621, 0.4),

                (649, 0.5),

                (677, 0.7),

            ]

        ),

    },

    "gray_iron": {

        "display_name": "Gray iron",

        "rows": _y_rows([(482, 0.0)]),

    },

    "other_ductile_metals": {

        "display_name": "Other ductile metals",

        "rows": _y_rows(

            [

                (482, 0.4),

                (510, 0.4),

                (538, 0.4),

                (566, 0.4),

                (593, 0.4),

                (621, 0.4),

                (649, 0.4),

                (677, 0.4),

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

            "nodes/B313-appendix_A/tables/A-1.yaml",

            "nodes/B313-appendix_A/tables/A-1",

        ],

        materials=_STRESS_MATERIALS,

    )



    database.upsert_table(

        table_id=TABLE_MATERIAL_ALLOWABLE_STRESS,

        title="Sample Material Allowable Stress",

        version="1.0",

        unit="Pa",

        temperature_unit="F",

        interpolation=True,

        keys=["material_id", "design_temperature"],

        layout="material_rows",

        source_node="B313-material-stress",

        aliases=[

            "material_allowable_stress",

            "tables/material_allowable_stress.yaml",

            "tables/material_allowable_stress",

        ],

        materials=_STRESS_MATERIALS,

    )



    database.upsert_table(

        table_id=TABLE_A_1A,

        title="Table A-1A — Quality Factors for Seamless Pipe (sample)",

        version="1.0",

        keys=["material_id", "joint_category"],

        layout="flat_rows",

        source_node="B313-table-A-1A",

        aliases=[

            "A-1A",

            "table_b31_3_A-1A",

            "nodes/B313-appendix_A/tables/A-1A.yaml",

            "nodes/B313-appendix_A/tables/A-1A",

        ],

        rows=[

            {"material_id": ASTM_A106_GR_B, "joint_category": "seamless", "quality_factor_E": 1.0},

        ],

    )



    database.upsert_table(

        table_id=TABLE_A_1B,

        title="Table A-1B — Quality Factors for Welded Pipe and Forgings (sample)",

        version="1.0",

        keys=["material_id", "joint_category"],

        layout="flat_rows",

        source_node="B313-table-A-1B",

        aliases=[

            "A-1B",

            "table_b31_3_A_1B",

            "nodes/B313-appendix_A/tables/A-1B.yaml",

            "nodes/B313-appendix_A/tables/A-1B",

        ],

        rows=[

            {"material_id": ASTM_A106_GR_B, "joint_category": "seamless", "quality_factor_E": 1.0},

            {"material_id": ASME_SA_105, "joint_category": "forging", "quality_factor_E": 1.0},

            {"material_id": ASTM_A106_GR_B, "joint_category": "erw", "quality_factor_E": 0.85},

            {

                "material_id": ASTM_A106_GR_B,

                "joint_category": "furnace_butt_welded",

                "quality_factor_E": 0.60,

            },

        ],

    )



    database.upsert_table(

        table_id=TABLE_304_1_1,

        title="Table 304.1.1 — Values of Coefficient Y for t < D/6",

        version="1.0",

        temperature_unit="C",

        interpolation=True,

        keys=["material_id", "temperature_c", "design_temperature"],

        layout="material_rows",

        source_node="B313-table-304-1-1",

        aliases=[

            "table_304_1_1",

            "nodes/B313-304.1.1/tables/table_304_1_1.yaml",

            "nodes/B313-304.1.1/tables/table_304_1_1",

            "asme_table_304_1_1",

        ],

        materials=_TABLE_304_1_1_MATERIALS,

    )



    database.upsert_table(

        table_id=TABLE_302_3_5,

        title="Table 302.3.5 — Weld Joint Strength Reduction Factor W (sample)",

        version="1.0",

        subsection="302.3.5(e)",

        temperature_unit="F",

        interpolation=True,

        keys=["material_id", "design_temperature", "weld_joint_category"],

        layout="flat_rows",

        source_node="B313-table-302-3-5",

        aliases=[

            "302.3.5",

            "nodes/B313-302.3.5/tables/302.3.5.yaml",

            "nodes/B313-302.3.5/tables/302.3.5",

        ],

        rows=[],

    )



    return database





if __name__ == "__main__":

    built = build_database()

    print(f"Built {built.db_path} with {len(built.list_table_ids())} tables")


