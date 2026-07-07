# engine/reference/

Standards knowledge layer: read nodes from `knowledge/standards/`, compile micro-graphs, SQLite caches, lookup tables, materials, and display helpers.

## Purpose

Single source of truth for engineering **reference data** (not runtime task state). `StandardsReader` is the primary facade; build scripts populate `*_graph.db`, `*_nodes.db`, `*_tables.db`, etc.

## Entry Points

| Symbol | File |
|--------|------|
| `StandardsReader` | `standards_reader.py` |
| `list_standard_packs`, `resolve_standard_pack` | `standards_paths.py` |
| `build_or_load_graph` | `graph_cache.py` |
| `GraphBuilder` | `../graph/graph_builder.py` (uses reference compile helpers) |

## Dependencies

**Depends on:** `knowledge/standards/` tree, `engine/graph/pack_graph.py`, `engine/units/unit_ids.py`

**Used by:** `engine/graph/`, `engine/executor/`, `engine/validation/`, `api/`, `scripts/build_*.py`, `ai/`

## Runtime Usage

**Active.** Every workflow session constructs a `StandardsReader`. Graph store loads via `graph_cache.build_or_load_graph` when pack DB exists.

## Possible Dead Code

| Item | Confidence |
|------|------------|
| `graph_cache.invalidate_graph_cache` | **High** — defined, no importers |
| `standards_reader._split_frontmatter` | **Medium** — duplicate of `standards_markdown.split_frontmatter` |

## Notes

- Markdown/YAML nodes under `knowledge/standards/*/nodes/` compile to `PackGraph` (in-memory) with optional SQLite cache.
- Embedded children (`embedded_nodes.py`) become first-class graph nodes.
- `node_types.py` normalizes legacy types to canonical micro-graph types (`equation`, `lookup`, `validation_rule`, `table`, …).
- ASTM material slugs (`astm_a53`, `astm_a106`, …) resolve to the consolidated `astm` pack via `standards_paths.py`.
- Global workflow index: `knowledge/standards/workflows.db` (built from repo-root `workflows/*.yaml`).

## Execution Traces

```
standards/*/nodes/*.yaml|md
  → standards_reader.StandardsReader.load / graph_store
  → graph_cache.build_or_load_graph
    → graph_builder.GraphBuilder
    → pack_graph.PackGraph in GraphStore
```

Build-time only:

```
scripts/build_graph_db.py → graph_cache.write_graph_cache
scripts/build_standards_nodes_db.py → standards_nodes.StandardsNodesDatabase
scripts/build_standards_tables_db.py → standards_tables.StandardsTablesDatabase
```

## Per-file inventory

| File | Purpose | Key exports | Importers (sample) |
|------|---------|-------------|-------------------|
| `__init__.py` | Public exports | `StandardsReader`, path helpers | external packages |
| `asme_b31_3_table_ids.py` | Canonical B31.3 table ID strings | `TABLE_*`, `asme_b31_3_table_id` | executor lookups, api, scripts |
| `authority_registry.py` | Standard slug → canonical `AUTH-*` id | `standard_primary_authority`, `STANDARD_PRIMARY_AUTHORITY` | `authority_context_sync`, migration |
| `coefficient_resolver.py` | E, W, Y table/formula resolution | `lookup_*`, `propose_coefficient_defaults` | `node_runner`, `workflow_bootstrap`, tests |
| `embedded_nodes.py` | Parse embedded child sources in metadata | `iter_embedded_node_sources`, `find_embedded_body` | `graph_builder`, `formula_loader`, scripts |
| `formula_display.py` | Equation display strings from nodes | `load_equation_context`, `resolve_equation_display_variables` | `api/node_display`, messaging, reports |
| `graph_cache.py` | PackGraph SQLite cache R/W | `build_or_load_graph`, `write_graph_cache` | `graph_store`, `unit_resolver`, dev_studio |
| `graph_compile.py` | Metadata → semantic edges | `compile_metadata_edges`, `node_aliases`, `validate_edge_item` | `graph_builder`, dev_studio graph_sync |
| `graph_edge_schema.py` | Canonical edge types and metadata | `CANONICAL_EDGE_TYPES`, `REVERSE_EDGE_TYPE`, `workflow_anchor_target` | graph_compile, relationship_taxonomy, lazy_expander |
| `relationship_taxonomy.py` | Relationship taxonomy vocabulary | `KNOWLEDGE_EDGE_TYPES` (`reads_table`, `returns_parameter`, `constrains_equation`, …), `normalize_authoring_edge`, `expand_edge_types_for_query` | graph_compile, relationship_validator, traversal |
| `relationship_validator.py` | Taxonomy edge validation | `validate_edge_item`, `validate_edges_for_node` | node validators, graph_compile |
| `graph_db.py` | SQLite graph nodes/edges | `GraphDatabase`, `GraphNodeRecord`, `GraphEdgeRecord` | graph_builder, graph_store, lazy_expander |
| `graph_db.py` schemas | — | migration helpers | internal |
| `material_catalog_db.py` | Global material search index | `GlobalMaterialCatalog`, `search_materials` | api/desktop_service, material lookups |
| `material_ids.py` | Canonical material ID format | `make_material_id`, `ASTM_*` constants | tables scripts, lookups |
| `material_resolver.py` | Token → table key | `canonical_material_id` | engineering_validator, tests |
| `nomenclature_resolver.py` | Symbol definitions from definition nodes | `load_nomenclature`, `resolve_input_spec` | graph, node_interaction, messaging |
| `paragraph_sidecar.py` | Merge paragraph sidecars (`nomenclature.yaml`, `execution.yaml`) | `merge_paragraph_sidecar_metadata` | `standards_reader`, `graph_builder`, `node_interaction`, `assumption_checker` |
| `equation_sidecar.py` | Merge equation / validation_rule execution sidecars | `merge_equation_sidecar_metadata` | `standards_reader`, `graph_builder`, `formula_loader` |
| `workflow_sidecar.py` | Merge workflow runtime sidecars (`workflows/{id}/runtime.yaml`) | `merge_workflow_sidecar_metadata` | `standards_reader`, `graph_builder`, `node_interaction`, `assumption_checker` |
| `node_types.py` | Type/kind predicates | `is_lookup_node`, `is_validation_rule_node`, `canonical_type`, … | widespread |
| `pack_graph_db.py` | Path resolver | `resolve_pack_graph_db` | graph_store, graph_cache, dev_studio |
| `pack_nodes_db.py` | Path resolver | `resolve_pack_nodes_db` | standards_reader, scripts |
| `pack_pipe_dimensions_db.py` | Path resolver | `resolve_pack_pipe_dimensions_db` | pipe_dimension_lookup |
| `pack_tables_db.py` | Path resolver | `resolve_pack_tables_db` | lookup_engine, scripts |
| `parameter_metadata.py` | Parameter node metadata | `parameter_concept_id`, `prepare_parameter_metadata` | workflow_parameters, unit_validator |
| `pipe_dimensions_db.py` | B36.10 pipe dimensions SQLite | `PipeDimensionsDatabase` | pipe lookups, scripts |
| `pipe_dimensions_registry.py` | Multi-pack dimension source registry | `load_pipe_dimensions_registry` | scripts, tests |
| `standards_config_db.py` | Global standards registry DB | `StandardsConfigDatabase` | material_catalog, scripts |
| `standards_markdown.py` | Frontmatter parse/compose | `split_frontmatter`, `compose_frontmatter` | reader, dev_studio, scripts |
| `standards_nodes.py` | Per-pack node content SQLite | `StandardsNodesDatabase` | standards_reader |
| `standards_paths.py` | Pack path resolution | `resolve_standard_pack`, `list_standard_packs` | reader, scripts, api |
| `standards_reader.py` | **Main reader** — load nodes, graph_store | `StandardsReader`, `NodeRecord` | entire codebase |
| `standards_tables.py` | Per-pack lookup tables SQLite | `StandardsTablesDatabase` | lookup_engine, coefficient_resolver |
| `standards_tasks_db.py` | Global workflow task index | `StandardsTasksDatabase` | standards_browse, reader |
