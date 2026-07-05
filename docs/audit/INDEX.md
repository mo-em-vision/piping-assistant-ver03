# Architecture audit — document index

Master map of audit documentation. Use with [MAINTENANCE.md](MAINTENANCE.md) for how to cite and update sections.

## How to reference a section

In chat or issues, cite:

```text
@audit <path>#<section-anchor>
```

Examples:

```text
@audit cli/README.md#execution-traces
@audit docs/audit/DUPLICATES.md#graph-loading--compile
@audit engine/planner/README.md#possible-dead-code
```

Markdown link form (same anchor):

```text
[cli execution traces](../../cli/README.md#execution-traces)
```

**Anchor rules:** lowercase; spaces → hyphens; `&` → `--`; punctuation dropped. Matches GitHub/Cursor heading anchors for `## Heading Name`.

---

## Standard sections (every package `README.md`)

| Anchor                | Content to update when…                          |
| --------------------- | ------------------------------------------------ |
| `#purpose`            | Folder responsibility changes                    |
| `#files`              | Files added, removed, or renamed                 |
| `#entry-points`       | New scripts, modules, or routes invoked directly |
| `#dependencies`       | Import graph or consumers change                 |
| `#runtime-usage`      | Code moves on/off the execution path             |
| `#possible-dead-code` | Symbols become used/unused                       |
| `#notes`              | Duplicates, unusual patterns                     |
| `#per-file-inventory` | Public API, I/O, side effects of a file change   |
| `#execution-traces`   | Call chains through this folder change           |

Not every README uses identical headings; search the file for the closest section if a heading differs.

---

## Root and cross-cutting

| Document | Anchor examples | Scope |
|----------|-----------------|-------|
| [ARCHITECTURE_AUDIT.md](../../ARCHITECTURE_AUDIT.md) | `#top-level-layout`, `#entry-points`, `#execution-traces` | Repo root map |
| [docs/audit/PROGRESS.md](PROGRESS.md) | `#known-gaps` | Audit status |
| [docs/audit/DUPLICATES.md](DUPLICATES.md) | `#graph-loading--compile`, `#planning--intent`, … | Parallel implementations |
| [docs/audit/EXECUTION_TRACES.md](EXECUTION_TRACES.md) | `#desktop--task-input-to-rendered-output`, `#cli--interactive-chat`, … | End-to-end paths |
| [docs/audit/MAINTENANCE.md](MAINTENANCE.md) | `#when-to-update`, `#change-checklist` | Living-doc workflow |

---

## Backend packages

| Folder | Audit doc |
|--------|-----------|
| `cli/` | [cli/README.md](../../cli/README.md) |
| `api/` | [api/README.md](../../api/README.md) |
| `api/dev_studio/` | [api/dev_studio/README.md](../../api/dev_studio/README.md) |
| `models/` | [models/README.md](../../models/README.md) |
| `storage/` | [storage/README.md](../../storage/README.md) |
| `config/` | [config/README.md](../../config/README.md) |
| `scripts/` | [scripts/README.md](../../scripts/README.md) |
| `ai/` | [ai/README.md](../../ai/README.md) |
| `ai/agents/` | [ai/agents/README.md](../../ai/agents/README.md) |
| `dev/` | [dev/README.md](../../dev/README.md) |
| `dev/graph_explorer/` | [dev/graph_explorer/README.md](../../dev/graph_explorer/README.md) |
| `dev/desktop_ui/` | [dev/desktop_ui/README.md](../../dev/desktop_ui/README.md) |

### `engine/` (parent + subfolders)

| Folder | Audit doc |
|--------|-----------|
| `engine/` | [engine/README.md](../../engine/README.md) |
| `engine/reference/` | [engine/reference/README.md](../../engine/reference/README.md) |
| `engine/graph/` | [engine/graph/README.md](../../engine/graph/README.md) |
| `engine/planner/` | [engine/planner/README.md](../../engine/planner/README.md) |
| `engine/validation/` | [engine/validation/README.md](../../engine/validation/README.md) |
| `engine/executor/` | [engine/executor/README.md](../../engine/executor/README.md) |
| `engine/state/` | [engine/state/README.md](../../engine/state/README.md) |
| `engine/reports/` | [engine/reports/README.md](../../engine/reports/README.md) |
| `engine/inspection/` | [engine/inspection/README.md](../../engine/inspection/README.md) |
| `engine/units/` | [engine/units/README.md](../../engine/units/README.md) |
| `engine/equation/` | [engine/equation/README.md](../../engine/equation/README.md) |
| `engine/presentation/` | [engine/presentation/README.md](../../engine/presentation/README.md) |
| `engine/messaging/` | [engine/messaging/README.md](../../engine/messaging/README.md) |
| `engine/events/` | [engine/events/README.md](../../engine/events/README.md) |
| `engine/execution/` | [engine/execution/README.md](../../engine/execution/README.md) |
| `engine/rules/` | [engine/rules/README.md](../../engine/rules/README.md) |

---

## Frontend

| Folder | Audit doc |
|--------|-----------|
| `desktopApp/` | [desktopApp/README.md](../../desktopApp/README.md) |
| `desktopApp/electron/` | [desktopApp/electron/README.md](../../desktopApp/electron/README.md) |
| `desktopApp/src/services/api/` | [desktopApp/src/services/api/README.md](../../desktopApp/src/services/api/README.md) |
| `desktopApp/src/store/` | [desktopApp/src/store/README.md](../../desktopApp/src/store/README.md) |
| `desktopApp/src/config/` | [desktopApp/src/config/README.md](../../desktopApp/src/config/README.md) |
| `desktopApp/src/dev-studio/` | [desktopApp/src/dev-studio/README.md](../../desktopApp/src/dev-studio/README.md) |
| `desktopApp/src/types/` | [desktopApp/src/types/README.md](../../desktopApp/src/types/README.md) |
| `desktopApp/src/components/` | [desktopApp/src/components/README.md](../../desktopApp/src/components/README.md) |

---

## Knowledge data

| Folder | Audit doc |
|--------|-----------|
| `knowledge/` | [knowledge/README.md](../../knowledge/README.md) |
| `knowledge/standards/` | [knowledge/standards/README.md](../../knowledge/standards/README.md) |
| `knowledge/global/` | [knowledge/global/README.md](../../knowledge/global/README.md) |

---

## Tests

| Folder | Audit doc |
|--------|-----------|
| `tests/` | [tests/README.md](../../tests/README.md) |

---

## Code path → audit doc (quick lookup)

| You changed… | Update first… |
|--------------|----------------|
| REST route or `DesktopApiService` | `api/README.md` + maybe `docs/audit/EXECUTION_TRACES.md` |
| Planner / graph / executor | `engine/<subfolder>/README.md` + `engine/README.md` |
| Zustand store or API client | `desktopApp/src/store/` or `services/api/` README |
| `knowledge/` layout or pack | `knowledge/**/README.md` + `engine/reference/README.md` |
| New duplicate code path | `docs/audit/DUPLICATES.md` |
| New end-to-end user flow | `docs/audit/EXECUTION_TRACES.md` |
