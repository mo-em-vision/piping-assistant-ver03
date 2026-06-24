# ASTM A312 — Master Index

Austenitic stainless steel pipe material properties per **ASTM A312/A312M**.

## Tables

| Table | Description |
|-------|-------------|
| `standards_tables.db` | TP grades — chemical limits and minimum mechanical properties (`astm_a312_material_properties`) |

## Grades

| Grade | Alloy type |
|-------|------------|
| TP304 / TP304L / TP304H | 18Cr-8Ni austenitic |
| TP316 / TP316L / TP316H | 18Cr-12Ni-2.5Mo austenitic |
| TP321 | Titanium-stabilized |
| TP347 | Columbium-stabilized |
| TP317L | Higher molybdenum low-carbon |

## Lookup

Use `MaterialPropertiesLookup` with `standard="astm_a312"`:

```python
from pathlib import Path
from engine.executor.material_properties_lookup import MaterialPropertiesLookup

lookup = MaterialPropertiesLookup(Path("standards"), standard="astm_a312")
props = lookup.lookup("TP316L")
```
