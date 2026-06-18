# ASTM A106 — Master Index

Seamless carbon steel pipe material properties per **ASTM A106/A106M**.

## Tables

| Table | Description |
|-------|-------------|
| [tables/material_properties.yaml](tables/material_properties.yaml) | Grades A, B, C — chemical limits and minimum mechanical properties |

## Grades

| Grade | Typical use |
|-------|-------------|
| A106 Gr A | Lower-strength carbon steel seamless pipe |
| A106 Gr B | Most common carbon steel pipe grade for pressure service |
| A106 Gr C | Higher minimum strength carbon steel seamless pipe |

## Lookup

Use `MaterialPropertiesLookup` with `standard="astm_a106"`:

```python
from pathlib import Path
from engine.executor.material_properties_lookup import MaterialPropertiesLookup

lookup = MaterialPropertiesLookup(Path("standards"), standard="astm_a106")
props = lookup.lookup("SA-106B")
```
