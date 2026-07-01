# src/dev-studio — Architecture Audit

**Node Dev Studio** — development-only browser UI for CRUD on standards graph node YAML via backend `/api/v1/dev/*` endpoints. Separate Vite entry; not bundled in default production build.

## Purpose

Edit `standards/*/nodes/**` sources through the API exposed when `DEV_STUDIO_ENABLED=1` on the Python server. Provides pack picker, node list/search, YAML/metadata editor (Monaco), relationship editor, equation editor, bulk actions, and mini dependency graph.

## Files

| File | Purpose |
| --- | --- |
| `main.tsx` | React root for `studio.html` |
| `DevStudioApp.tsx` | Top-level layout, keyboard shortcuts, panel orchestration |
| `api/devStudioApi.ts` | REST client for `/api/v1/dev/*` |
| `store/devStudioStore.ts` | Zustand state for studio session |
| `hooks/useDebouncedSearch.ts` | `useDebouncedValue` for search input |
| `hooks/useRevisionPoll.ts` | Polls pack revision for external edits |
| `styles/dev-studio.css` | Studio-specific styles |
| `components/sidebar/NodeListPanel.tsx` | Filterable node list |
| `components/editor/NodeEditorPanel.tsx` | Monaco YAML/body editor |
| `components/graph/GraphPanel.tsx` | Dependency graph container |
| `components/graph/MiniDependencyGraph.tsx` | Small graph visualization |
| `components/relationships/RelationshipEditor.tsx` | Incoming/outgoing edges |
| `components/equation/EquationEditor.tsx` | Equation-specific fields |
| `components/fields/FieldComponents.tsx` | Reusable metadata field inputs |
| `components/bulk/BulkActionBar.tsx` | Multi-select delete/tag/export |

### Per-file inventory (key modules)

**`devStudioApi.ts`** — Confidence: **High**
- Reuses `backendClient` from main app API layer
- Endpoints: packs, node-types, nodes list/get/put/post/delete, relationships, validate, bulk, export
- Types: `NodeSummary`, `NodeDetail`, `NodeTypeSchema`, `ValidationResult`, `RelationshipsPayload`

**`devStudioStore.ts`** — Confidence: **High**
- Default pack: `asme_b31.3`
- Actions: `bootstrap`, `refreshNodes`, `loadNode`, `saveNode`, `createNode`, `duplicateNode`, `deleteSelectedNode`, `bulkDelete`, `bulkAddTags`, `exportSelected`
- Side effects: all via `devStudioApi`

**`DevStudioApp.tsx`** — Confidence: **High**
- Shortcuts: Ctrl+F search, Ctrl+N new node, Ctrl+D duplicate, Delete, arrow navigation
- Composes sidebar + editor + graph + bulk bar

## Entry Points

| Entry | Command | HTML |
| --- | --- | --- |
| `main.tsx` | `npm run dev:studio` (`VITE_DEV_STUDIO=true vite --open /studio.html`) | `studio.html` |

`vite.config.ts` when `isStudioOnly`: no Electron plugin; Rollup input is only `studio.html`.

## Dependencies

**Depends on:**

- `@/services/api/backendClient` (shared with main app)
- `@monaco-editor/react` (dependency in root `package.json`)
- Backend with `DEV_STUDIO_ENABLED=1` (Electron dev spawn sets this automatically; manual server needs `set DEV_STUDIO_ENABLED=1`)

**Depended on by:**

- `studio.html` only
- Tests: `tests/dev-studio/useDebouncedSearch.test.ts`
- `src/components/math/engineeringMath.tsx` imported by `EquationEditor` (shared math rendering)

**Not used by:** Main `App.tsx` / `WorkspaceLayout` execution path.

## Runtime Usage

**Development:** Active when developer runs `npm run dev:studio` and backend dev API is enabled.

**Production package:** Default `npm run build` excludes studio entry unless `VITE_DEV_STUDIO=true` at build time (per `AGENTS.md`).

## Possible Dead Code

| Item | Evidence | Confidence |
| --- | --- | --- |
| None in folder | All 15 files referenced from `DevStudioApp` or store/api graph | High |

## Notes

- Studio uses same `VITE_BACKEND_URL` / `env.backendUrl` as main app for API host.
- Revision poll (`useRevisionPoll`) warns when graph DB revision changes under another editor.
- No Electron IPC; plain browser `fetch` only.
- See also: [`docs/node_dev_studio.md`](../../../docs/node_dev_studio.md) (product doc).

## Execution Traces

### Studio open

```
studio.html
  → src/dev-studio/main.tsx
  → DevStudioApp
  → useEffect → devStudioStore.bootstrap()
      → devStudioApi.listPacks()
      → devStudioApi.getNodeTypes()
  → useRevisionPoll (interval checkRevision)
```

### Select and edit node

```
NodeListPanel click
  → devStudioStore.setSelectedId → loadNode(id)
  → devStudioApi.getNode + getRelationships
  → NodeEditorPanel displays metadata/body
  → User edits → saveNode
  → devStudioApi.updateNode → refreshNodes
```

### Create node (Ctrl+N)

```
DevStudioApp keydown
  → devStudioStore.createNode({ id, type, ... })
  → devStudioApi.createNode
  → refreshNodes → loadNode
```

### Bulk delete

```
BulkActionBar
  → devStudioStore.bulkDelete
  → devStudioApi.bulkDelete
  → clearSelection + refreshNodes
```
