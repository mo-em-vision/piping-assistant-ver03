# ASTM — Master Index

Material property lookup nodes for ASTM specifications.

## Material nodes

| Node | Standard | Table |
|------|----------|-------|
| [nodes/A53.yaml](nodes/A53.yaml) | ASTM A53/A53M | `astm_a53_material_properties` |
| [nodes/A106.yaml](nodes/A106.yaml) | ASTM A106/A106M | `astm_a106_material_properties` |
| [nodes/A312.yaml](nodes/A312.yaml) | ASTM A312/A312M | `astm_a312_material_properties` |
| [nodes/A105.yaml](nodes/A105.yaml) | ASTM A105/A105M | `astm_a105_material_properties` |

## Compiled databases

| File | Description |
|------|-------------|
| `astm_a53_tables.db` | A53 catalog |
| `astm_a106.db` | A106 mechanical properties |
| `astm_a312.db` | A312 mechanical properties |
| `a_105_tables.db` | A105 catalog |
| `astm_graph.db` | Compiled micro-graph cache |
| `astm_nodes.db` | Node index cache |

Rebuild: `python scripts/build_astm_standards_tables_db.py` and `python scripts/build_all_standards_dbs.py`
