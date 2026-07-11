# engine/graph/

Micro-graph workflow engine: compile sources to `PackGraph`, expand active subgraph, assumptions, interactions, navigation, and execution plans.

## Purpose

Resolves **which nodes run** and **in what order** for a workflow root. `GraphEngine` is the public coordinator; `MicroGraphEngine` implements pack-graph workflows; `lazy_expander` drives step-by-step expansion.

## Entry Points

| Symbol | File |
|--------|------|
| `GraphEngine` | `graph_engine.py` |
| `normalize_root_id`, `resolve_workflow_node_id` | `graph_engine.py` |
| `GraphStore`, `PackGraph` | `graph_store.py`, `pack_graph.py` |
| `MicroGraphEngine` | `micro_graph_engine.py` |
| `expand_workflow` | `lazy_expander.py` |
| `build_workflow_phased_navigation` | `navigation_phases.py` |

## Dependencies

**Depends on:** `engine/reference/` (reader, node_types, nomenclature, graph_db records)

**Used by:** `engine/planner/`, `engine/executor/`, `engine/state/`, `engine/presentation/`, `engine/execution/`, `api/workflow_bootstrap.py`, `api/workflow_timeline.py`, `api/chat_orchestrator.py`, `ai/`

## Runtime Usage

**Active** when `StandardsReader.graph_store.available`. `api/workflow_bootstrap.py` and `Executor` call `GraphEngine` / expansion on every task.

Legacy `depends_on` traversal remains behind `VER03_LEGACY_GRAPH_TRAVERSAL=1` or absent graph cache.

## Possible Dead Code

| Item | Confidence | Notes |
|------|------------|-------|
| `parameter_registry.apply_registry_to_inputs`, `merge_descriptor_into_input` | **High** | No importers |
| `navigation_phases.build_phased_navigation`, `build_mawp_phased_navigation` | **High** | Superseded by `build_workflow_phased_navigation`; docs only |
| `display_emitter.emit_active_context` | **High** | No importers |
| `prefetch_cache().get` / read path | **High** | Writes only; no consumer reads cache |
| `parameter_registry.seed_parameter_registry` (legacy path) | **Medium** | Called only when legacy traversal enabled |
| `GraphTools.limitation_hints` / `RuleTools` | **High** | Duplicate; never called |

## Notes

- **Duplicate traversal:** `traversal.py` (BFS/DFS/topo) used by `micro_graph_engine` and `lazy_expander`; legacy path in `graph_engine.py` uses separate depends_on logic.
- **Duplicate limitation hints:** `GraphTools.limitation_hints` and `RuleTools.limitation_hints` — identical, unused.
- `graph_engine._STUB_ROOTS` surfaces unimplemented workflow candidates.

## Execution Traces

### Plan build (micro-graph)

```
GraphEngine.build_plan(reader, root, inputs)
  → MicroGraphEngine.expand / lazy_expander.expand_workflow
  → assumption_checker + node_interaction gates
  → topological_order (traversal.py)
  → ExecutionPlan (models.execution)
```

### Desktop phased navigation

```
api/workflow_bootstrap.refresh_planning_state
  → navigation_phases.build_workflow_phased_navigation
  → workflow_navigation.load_workflow_navigation
  → graph_timeline.graph_input_step_order (parameter ordering)
```

### Prefetch (background)

```
GraphEngine.prefetch → MicroGraphEngine.prefetch
  → prefetch.prefetch_async (thread)
  → lazy_expander.expand_workflow (horizon)
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Lazy exports | `GraphEngine`, `GraphCycleError` | docs, tests |
| `assumption_checker.py` | Expansion/execution assumption eval | `AssumptionEvaluation`, `evaluate_*` | graph_engine, planner, node_runner |
| `conditions.py` | `when` clause matching | `when_clause_matches`, `GraphCycleError` | traversal, lazy_expander, graph_engine |
| `definition_equations.py` | Post-calc definition equations | `try_complete_definition_equations` | executor, workflow_bootstrap |
| `display_emitter.py` | Output blocks from graph nodes | `emit_initiation_blocks`, `emit_equation_blocks` | micro_graph_engine, presentation/blocks |
| `doc_templates.py` | `{{var}}` doc rendering | `build_doc_context`, `render_doc_template` | documentation_resolver, lifecycle_emitter |
| `documentation_resolver.py` | Structured node docs | `resolve_workflow_documentation` | workflow_state |
| `graph_builder.py` | MD/YAML → PackGraph | `GraphBuilder`, `compute_source_fingerprint` | graph_cache |
| `graph_engine.py` | **Plan coordinator**, legacy traversal | `GraphEngine`, `normalize_root_id` | planner, executor, api, tests |
| `graph_store.py` | In-memory graph facade | `GraphStore` | widespread |
| `graph_timeline.py` | Parameter step ordering | `graph_input_step_order`, `graph_step_titles` | workflow_bootstrap, workflow_timeline |
| `lazy_expander.py` | Step expansion state machine | `expand_workflow`, `ExpansionState` | micro_graph_engine, prefetch |
| `micro_graph_engine.py` | Micro-graph workflow API | `MicroGraphEngine`, `build_plan`, `required_user_inputs`, `seed_parameter_registry` | graph_engine |
| `navigation_phases.py` | Phased missing-field navigation | `build_workflow_phased_navigation`, `allowed_fields_for_phase` | planner, orchestrator, api |
| `node_behaviors.py` | Type behavior registry | `is_executable_equation`, `is_data_parameter` | lazy_expander, lifecycle_emitter |
| `node_interaction.py` | User interaction specs | `NodeInteractionSpec`, `evaluate_node_interactions` | graph_engine, messaging, ai |
| `pack_graph.py` | In-memory pack graph | `PackGraph` | graph_store, graph_builder |
| `parameter_registry.py` | Legacy descriptor seeding (fallback) | `seed_parameter_registry` from definition nomenclature | graph_engine (legacy traversal only) |
| `param_priority.py` | Parameter collection order | `parameter_collection_priority` | workflow_parameters, graph_timeline |
| `prefetch.py` | Background expansion cache | `prefetch_async`, `PrefetchCache` | micro_graph_engine |
| `relationship_resolver.py` | Equation `requires` → parameters | `resolve_require_bindings` | definition_equations, node_runner, display_emitter |
| `traversal.py` | BFS/DFS/topo on edges | `topological_order`, `bfs_neighbors` | micro_graph_engine, lazy_expander |
| `workflow_navigation.py` | Load nav config from workflow metadata | `load_workflow_navigation` | planner, orchestrator, api |
