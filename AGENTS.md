# Engineering Desktop App — Agent Guide

Ver03 is a **Python engineering backend** plus an **Electron + React desktop client** (`desktopApp/`). The desktop app is a thin presentation layer; the backend owns calculations, standards, task state, and reports.

## Before coding

1. Read and follow `docs/rules.md` (workflow, verification, debugging, node structure, **§12 planner vs messaging prompts**, **§13 graph-driven workflow paths**, **§21 Flow Guidance Layer**).
2. Read the relevant doc under `docs/desktopApp/` (start with `14_desktop_app_implementation_roadmap.md`).
3. Inspect existing code in the target area (stores, `api/`, `desktopApp/src/`).
4. Propose a short plan for non-trivial changes (files, approach, risks) with an **Architecture Consistency Review** and **Plan Review Gate** (`docs/process/plan_review_gate.md`, `docs/rules.md` §22–§23). Do not implement until consistency review is **CLEAR** and gate status is **APPROVED**.

## Architecture boundaries

| Layer | Owns |
| --- | --- |
| Backend (`api/`, `engine/`, `storage/`, `ai/`) | Engineering logic, validation, task state, SQLite, reports |
| Frontend (`desktopApp/src/`) | UI, Zustand stores, API client, rendering backend `task_state` |

Do **not** move engineering rules, formulas, or workflow logic into the frontend.

## Runtime execution context

Mutable runtime state (Facts, Goals, decisions, assumptions, validation, trace refs) lives in [`models/execution_context.py`](models/execution_context.py) on each `Task` — not in `knowledge/`. See [`docs/node-templates/Execution Context.md`](docs/node-templates/Execution%20Context.md).

**Authority Context** (active governing standards) is a peer object on each `Task`: [`models/authority_context.py`](models/authority_context.py). See [`docs/node-templates/Authority Context.md`](docs/node-templates/Authority%20Context.md). Linked to the execution context via `authority_context_id` / `execution_context_id`. `active_authorities[].authority_id` references immutable [`AUTH-*` Authority nodes](knowledge/global/authorities/) — see [`docs/node-templates/Authority Node.md`](docs/node-templates/Authority%20Node.md).

## Micro-graph data flow

Standards micro-graph nodes follow: **Markdown/YAML → GraphBuilder → PackGraph → SQLite cache**.

- Source of truth: `knowledge/standards/*/nodes/**/node.{yaml,md}` — **paragraph** nodes use flat `nodes/paragraph/{id}.yaml` plus optional sidecars (`{id}/nomenclature.yaml`) for nomenclature; pack defaults (`source_language`, etc.) live in `pack.yaml` at the pack root and inherit to child nodes at compile/load time; one node per lettered subsection with hyphen ids (`304.1.2-a`, `paragraph_number` matches `id`); required `metadata.last_revision` and `metadata.edited_by` — see [`docs/node-templates/Paragraph Node.md`](docs/node-templates/Paragraph%20Node.md) and [`.cursor/rules/paragraph-subsection-naming.mdc`](.cursor/rules/paragraph-subsection-naming.mdc); **equation** nodes use flat `nodes/equation/asme-b313-*.yaml` with inline execution fields and `equation_number` / `paragraph_number` citation metadata (ids prefixed `asme-b313-` per pack); section nodes use `node.yaml` (structure) plus optional `node.md` (paragraph trace and embedded child `source:` blocks)
- **Graph relationships:** every knowledge node uses typed `edges: [{type, target}]` only (outgoing). Do **not** author a top-level `links` metadata block. See [`docs/node-templates/_relationship_schema.md`](docs/node-templates/_relationship_schema.md). Paragraph **hierarchy traversal** (`parent`, ordered `children`) lives in the `hierarchy` metadata block; cross-paragraph citations use `related_to` edges. See [`Paragraph Node.md`](docs/node-templates/Paragraph%20Node.md#relationship-rule). Nomenclature prose traces use `citations`.
- Embedded children in metadata containers (`equations`, `assumptions`, `texts`, …) compile as first-class nodes via `engine/reference/embedded_nodes.py`
- Runtime: `GraphStore` / `build_or_load_graph()` compile sources into a `PackGraph` in memory
- SQLite (`*_graph.db`) is an optional performance cache only; rebuild with `python scripts/build_graph_db.py`
- Canonical node types: `workflow`, `paragraph`, `definition`, `calculation`, `equation`, `lookup`, `validation_rule`, `table`, `parameter`, `quantity`, `designation`, `text`, `unit`, `concept`, `authority` — use `kind` metadata for variants (e.g. `parameter` + `kind: assumption`, `paragraph` + `kind: calculation`). Equation (`EQ-*`) calculates quantities only; use `lookup` (`LOOKUP-*`) for table resolution and `validation_rule` (`VALRULE-*`) for checks.

## Development order

Structure → data flow → backend connection → visualization → interaction → polish.

## Testing

- Backend: `python -m pytest tests/api tests/mvp/test_desktop_mvp_workflow.py`
- Frontend: `cd desktopApp && npm run test:run`
- MVP smoke: `cd desktopApp && npm run verify:mvp`
- Release gate: `cd desktopApp && npm run verify:release`
- After changing standards markdown/YAML: `python scripts/build_graph_db.py` and `python scripts/build_standards_nodes_db.py` (or `python scripts/build_all_standards_dbs.py`) then re-run backend tests

## Developer Inspector (development only)

Centralized debugging panel in the desktop app for execution trace, provenance, planner decisions, replay, and graph integrity checks.

**Full documentation:** [`docs/developer_inspection_framework.md`](docs/developer_inspection_framework.md)

1. Start backend with inspection enabled:
   ```bash
   set DEV_INSPECTION_ENABLED=1
   python -m api.server
   ```
   (Unpackaged Electron builds set this automatically.)

2. Run the desktop app in dev mode (`npm run dev` in `desktopApp/`).

3. Click **Inspector** in the app header when a task is active.

## Key paths

```
api/server.py              # Desktop REST API
api/flow_guidance.py       # Flow Guidance payload on task_state
engine/presentation/       # GuidanceResolver, ResponseComposer (docs/rules.md §21)
presentation/guidance/     # Traversal narration YAML per workflow
desktopApp/electron/       # Main process, backend child process
desktopApp/src/store/      # Zustand state
desktopApp/src/services/api/  # Backend client
docs/desktopApp/           # Product and architecture docs
docs/audit/                # Living architecture audit (INDEX, MAINTENANCE, DUPLICATES, traces)
**/README.md               # Per-folder audit docs (see docs/audit/INDEX.md)
```

## Architecture audit (living documentation)

Per-folder audit READMEs describe **current implementation** (not design intent). When you change code, update the matching audit sections in the same task — see [docs/audit/MAINTENANCE.md](docs/audit/MAINTENANCE.md).

- **Index:** [docs/audit/INDEX.md](docs/audit/INDEX.md) — all audit paths and section anchors
- **Cite a section:** `@audit api/README.md#execution-traces` or markdown `#anchor` links
- **Cross-cutting:** [docs/audit/DUPLICATES.md](docs/audit/DUPLICATES.md), [docs/audit/EXECUTION_TRACES.md](docs/audit/EXECUTION_TRACES.md)

## After coding

Explain what changed, why, and any remaining risks. Keep diffs minimal and match existing conventions.
