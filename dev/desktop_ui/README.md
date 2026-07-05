# dev/desktop_ui — Architecture Audit

Audit date: 2026-07-05. Documentation reflects the code as it exists today.

---

## Purpose

Shared dev platform (production boundary, session/graph read models, cross-tool links): [`../README.md`](../README.md#shared-dev-platform).

React components for **inline development UI** embedded in the Electron desktop app: node hover tooltips, Developer Inspector panels, and the in-app Node Edit tab. Lazy-loaded when `env.devToolsAvailable`; rendered only when the user enables **Dev Mode** (`useDevToolsStore().devModeActive`). Graph Explorer embed lives in `InspectorGraphPanel` via `@graph-explorer/embed`.

Source lives under `dev/desktop_ui/` for consistency with other dev tooling (`dev/graph_explorer/`). The desktop app imports this package via the `@dev-ui/*` path alias (configured in `desktopApp/vite.config.ts` and `desktopApp/tsconfig.json`).

---

## Files

| Path | Role |
|------|------|
| `DevNodeHoverProvider.tsx` | Context + tooltip for node provenance hover |
| `DevNodeHoverSurface.tsx` | Wraps output nodes; shows hover in dev mode |
| `DevNodeTooltip.tsx` | Tooltip UI for provenance preview |
| `DevNodeHover.css` | Hover/tooltip styles |
| `NodeEditTab.tsx` | Right-panel tab for quick node YAML edit (Dev Studio API) |
| `NodeEditTab.css` | Node edit tab styles |
| `inspector/` | Developer Inspector bottom panel (trace, graph, planner, …) |
| `tests/` | Vitest unit tests (run via `desktopApp` vitest config) |

---

## Entry Points

| Entry | How it is reached |
|-------|-------------------|
| `DevNodeHoverProvider` | `desktopApp/src/App.tsx` — always mounted |
| `DevNodeHoverSurface` | Output/workflow/standards components — dev hover |
| `DeveloperInspector` | `WorkspaceLayout` — lazy when `devToolsAvailable`; mounted when Dev Mode active |
| `NodeEditTab` | `RightPanel` — lazy when `devToolsAvailable`; tab content when Dev Mode active |
| `InspectorGraphPanel` | Embedded `@graph-explorer` canvas (Inspector Graph tab) |

---

## Dependencies

### This folder depends on

| Area | Examples |
|------|----------|
| `desktopApp/src/store/*` | `rightPanelStore`, `uiStore`, `taskStore` |
| `desktopApp/src/services/api/*` | `inspectionApi` |
| `desktopApp/src/types/*` | `backend/api`, `backend/inspection` |
| `desktopApp/src/dev-studio/*` | `NodeEditTab` reuses Dev Studio field components and API client |
| `desktopApp/src/config/env` | Dev mode gating on hover surfaces |
| `desktopApp/src/utils/*` | `nodeProvenance` |

### Who depends on this folder

| Consumer | Relationship |
|----------|--------------|
| `desktopApp/src/App.tsx` | `DevNodeHoverProvider` |
| `desktopApp/src/components/layout/*` | Inspector store, lazy inspector + node edit |
| `desktopApp/src/components/outputs/*`, `workflow/*`, etc. | `DevNodeHoverSurface` |

---

## Runtime Usage

**On the desktop dev path only.** Production release builds exclude lazy dev panels; hover surfaces no-op when `env.devMode` is false.

Requires backend flags when features are used:

- `DEV_INSPECTION_ENABLED=1` — Developer Inspector API
- `DEV_STUDIO_ENABLED=1` — Node Edit tab / Dev Studio API

Electron dev spawn sets both automatically when unpackaged.

---

## Tests

```bash
cd desktopApp && npm run test:run -- ../dev/desktop_ui/tests/
```

Vitest resolves `@dev-ui/*` and `@/*` via `desktopApp/vitest.config.ts`.
