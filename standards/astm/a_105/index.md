# ASTM A105 — Master Index

Carbon steel forgings for piping applications per **ASTM A105/A105M**.

## Tables

| Table | Description |
|-------|-------------|
| `a_105_tables.db` | A105 catalog entry (`astm_a105_material_properties`) |

## Lookup

Use `MaterialPropertiesLookup` with `standard="a_105"`:

```python
from pathlib import Path
from engine.executor.material_properties_lookup import MaterialPropertiesLookup

lookup = MaterialPropertiesLookup(Path("standards"), standard="a_105")
props = lookup.lookup("SA-105")
```
