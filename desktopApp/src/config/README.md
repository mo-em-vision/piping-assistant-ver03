# src/config — Architecture Audit

Shared configuration constants and environment-derived settings for the renderer and (via bundling) the Electron main process.

## Purpose

Single source for app naming, default backend URL, health-check paths, and dev-vs-production feature flags exposed as `env` to React code.

## Files

| File | Purpose | Exports | Imported by |
| --- | --- | --- | --- |
| `constants.ts` | App name, backend URL defaults, health helpers, `BackendStatusPayload` type | `constants`, `backendConfig`, `parseBackendUrl`, `buildHealthUrl`, types | `env.ts`, `electron/*`, `connectionStore`, `useBackend`, banners |
| `development.ts` | Dev Vite env mapping | `developmentConfig` | `env.ts` only |
| `production.ts` | Production Vite env mapping | `productionConfig` | `env.ts` only |
| `env.ts` | Picks dev or prod config at build time | `env`, `AppEnv` | Renderer: `backendClient`, `AppHeader`, `WorkspaceLayout`, `RightPanel`, `DevNodeHoverSurface` |

### Per-file detail

**`constants.ts`** — Confidence: **High**
- Shared between Electron main and renderer (TypeScript compiled into both bundles)
- `buildHealthUrl`: `{baseUrl}/health`
- No `import.meta` — safe for main process

**`development.ts`** — Confidence: **High**
- `devToolsAvailable: true` (Vite dev server and unpackaged Electron)

**`production.ts`** — Confidence: **High**
- `devToolsAvailable`: `VITE_ENABLE_DEV_TOOLS === 'true'` (packaged Electron builds set this in `package:win`)

**`env.ts`** — Confidence: **High**
- `export const env = import.meta.env.DEV ? developmentConfig : productionConfig`
- Renderer-only (uses `import.meta.env`)
- `devMode` export is deprecated; use `env.devToolsAvailable` + `useDevToolsStore().devModeActive`

## Entry Points

No runtime entry. Modules load as side-effect imports when consumers first import `env` or `constants`.

Electron main imports `constants` directly, not `env.ts`.

## Dependencies

**Depends on:**

- Vite `import.meta.env` (`development.ts`, `production.ts`)
- Optional env vars: `VITE_BACKEND_URL`, `VITE_APP_NAME`, `VITE_DEV_MODE`

**Depended on by:**

- `electron/main.ts`, `electron/services/startup.ts`, `electron/services/backendProcess.ts`, `electron/preload.ts` (types)
- `src/services/api/backendClient.ts`
- `src/hooks/useBackend.ts`, `useWorkspaceBootstrap.ts` (types)
- `src/components/layout/*`, `src/components/errors/ConnectionErrorBanner.tsx`
- `src/types/frontend/electron.d.ts`

## Runtime Usage

**Always active.** Backend URL and health paths used on every app session.

**Two-gate dev tools model:**

| Gate | Meaning |
| --- | --- |
| `env.devToolsAvailable` | Build may load dev UI chunks (all Electron builds via `VITE_ENABLE_DEV_TOOLS=true`; always true in Vite dev) |
| `useDevToolsStore().devModeActive` | User toggled Dev Mode on (persisted in `localStorage`) |

Effective dev UI: `devToolsAvailable && devModeActive`. Backend dev APIs (`DEV_INSPECTION_ENABLED`) are enabled for all Electron spawns; the toggle controls visibility only.

## Possible Dead Code

| Item | Evidence | Confidence |
| --- | --- | --- |
| Direct imports of `development.ts` / `production.ts` | Only via `env.ts` | Low (by design) |
| `constants.appName` vs `env.appName` | Both exist; UI mostly uses `env.appName` in header | Medium — dual access pattern, both used |

## Notes

- **Two backend URL resolutions:** Electron `startup.ts` uses `process.env.VITE_BACKEND_URL`; renderer uses `env.backendUrl` from Vite `import.meta.env`. Usually aligned in dev; verify both in custom deployments.
- `docs/README.md` and `.env.example` document `VITE_*` variables (not in this folder).
- `constants.appName` is "Engineering Knowledge Graph Assistant"; not all UI strings use `env.appName`.

## Execution Traces

### Renderer API call

```
backendClient constructor
  → env.backendUrl (developmentConfig | productionConfig)
  → fetch(baseUrl + path)
```

### Electron backend spawn

```
startup.ts resolveBackendUrl()
  → process.env.VITE_BACKEND_URL ?? constants.defaultBackendUrl
backendProcess.ts
  → parseBackendUrl → BACKEND_HOST, BACKEND_PORT env for child
  → buildHealthUrl for polling
```

### Dev inspector gate

```
WorkspaceLayout
  → env.devToolsAvailable ? lazy(DeveloperInspector) : null
  → devModeActive ? mount inspector : null
```

### Connection banner

```
ConnectionErrorBanner
  → BackendStatusPayload from Electron (prop)
  → connectionStore.apiStatus from renderer health check
```
