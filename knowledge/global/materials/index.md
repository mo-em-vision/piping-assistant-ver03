# Global material catalog

Cross-pack material search index. ASTM table data lives under `knowledge/standards/astm/`; this folder maps slugs to those DBs and builds the searchable catalog.

| File | Role |
|------|------|
| `registry.yaml` | Maps material slugs (`astm_a106`, …) to ASTM table DB paths |
| `supplemental.yaml` | Non-ASTM catalog entries (e.g. API 5L) |
| `materials.db` | Built search index (`scripts/build_material_catalog_db.py`) |
