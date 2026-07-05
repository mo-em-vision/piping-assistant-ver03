# Duplicate Implementations Register

Documented during Architecture Audit Mode. **No recommendation** on which to keep — code as-is.

## Graph loading / compile

| Implementation | Path | Used by |
|----------------|------|---------|
| In-memory compile | `engine/reference/graph_compile.py` | `GraphStore`, build scripts |
| Pack graph DB cache | `engine/reference/pack_graph_db.py` | `GraphStore` when cache hit |
| Graph store facade | `engine/graph/graph_store.py` | API, executor, explorer |
| CLI graph DB builder | `scripts/build_graph_db.py` | Offline; Graph Explorer watcher |

## Graph traversal

| Implementation | Path | When |
|----------------|------|------|
| Micro-graph + lazy expand | `engine/graph/micro_graph_engine.py`, `lazy_expander.py`, `traversal.py` | Default when `*_graph.db` exists |
| Legacy `depends_on` BFS | `engine/graph/graph_engine.py` | `VER03_LEGACY_GRAPH_TRAVERSAL=1` or no cache |

## Standards reading

| Implementation | Path | Used by |
|----------------|------|---------|
| Engine reader | `engine/reference/standards_reader.py` | API, engine, scripts |
| CLI shim | `cli/standards_reader.py` | CLI display commands |

## Planning / intent

| Implementation | Path | Used by |
|----------------|------|---------|
| Deterministic planner | `engine/planner/planner.py` | Workflow navigation |
| LLM planner fallback | `ai/agents/planner_agent.py` | CLI orchestrator |
| Deterministic router | `engine/router.py` | CLI first pass |
| LLM intent | `ai/agents/intent_agent.py` | CLI orchestrator |
| Unused routing agent | `ai/agents/routing_agent.py` | Tests only |

## Node parsing / graph build

| Implementation | Path | Role |
|----------------|------|------|
| Graph builder | `engine/graph/graph_builder.py` | YAML/MD → graph |
| Embedded nodes | `engine/reference/embedded_nodes.py` | Container child compilation |

## Session / project storage

| Implementation | Path | Used by |
|----------------|------|---------|
| Desktop SQLite | `storage/project_session_store.py` | API / desktop |
| CLI filesystem | `cli/session_store.py` | CLI `task` commands |

## Parameter registry

| Implementation | Path | When |
|----------------|------|------|
| MicroGraphEngine seed | `engine/graph/micro_graph_engine.py` | Active path |
| Deprecated registry | `engine/graph/parameter_registry.py` | Legacy traversal |

## Node DB compile paths

| Implementation | Output | Script |
|----------------|--------|--------|
| Pack graph DB | `*_graph.db` | `build_graph_db.py` |
| Pack nodes DB | `*_nodes.db` | `build_standards_nodes_db.py` |

## Graph visualization (dev)

| Implementation | Path |
|----------------|------|
| Graph Explorer | `dev/graph_explorer/` |
| Inspector graph panel | `dev/desktop_ui/inspector/InspectorGraphPanel.tsx` |
| CLI `graph show` | `cli/commands/graph.py` |

## Frontmatter parsing

| Implementation | Path |
|----------------|------|
| `standards_reader._split_frontmatter` | `engine/reference/standards_reader.py` |
| `standards_markdown.split_frontmatter` | `engine/reference/standards_markdown.py` |

## Limitation hints (both unused)

| Implementation | Path |
|----------------|------|
| `GraphTools.limitation_hints` | `engine/planner/tools.py` |
| `RuleTools.limitation_hints` | `engine/planner/tools.py` |
