# Protected files registry

**Path authority:** [config/restricted_paths.yaml](../../config/restricted_paths.yaml) — machine-readable manifest of protected paths and categories. Hooks and enforcement scripts read **only** that file.

This document explains **why** paths are protected, **authorization rules**, **editing workflow**, and **ownership**. It does not enumerate paths mechanically.

Cursor agents must read this registry at session start (via [`.cursor/rules/protected-documentation.mdc`](../../.cursor/rules/protected-documentation.mdc)).

---

## Categories

Each protected path has exactly one category in the manifest.

| Category | Implementation mode | Documentation-edit mode |
| --- | --- | --- |
| `constitutional` | Always blocked | Allowed only if listed; diff approval required |
| `contract` | Always blocked | Allowed only if listed; diff approval required |
| `agent_rule` | Always blocked | Allowed only if listed; diff approval required |
| `architecture_authoritative` | Always blocked | Allowed only if listed; diff approval required |
| `architecture_explanatory` | Allowed only under explanatory-sync exception | Allowed if listed |
| `explanatory` | Allowed only under explanatory-sync exception | Allowed if listed |
| `generated` | Always blocked (no manual editing) | Always blocked even if listed |

**Authoritative** (always blocked in implementation mode): `constitutional`, `contract`, `agent_rule`, `architecture_authoritative`.

**Explanatory-sync** (may change during implementation only under the exception below): `explanatory`, `architecture_explanatory`.

---

## Task modes

### Normal implementation mode (default)

No `Mode:` declaration in the user request.

| Edit target | Behavior |
| --- | --- |
| Unprotected code, tests, config | Allowed |
| Authoritative categories (see above) | Block — report `RESTRICTED DOCUMENTATION PHASE REQUIRED — IMPLEMENTATION BLOCKED` with exact path and category |
| `explanatory`, `architecture_explanatory` | Allowed only under explanatory-sync exception |
| `generated` | Always block — `GENERATED FILE — MANUAL EDIT BLOCKED` |

### Documentation-edit mode

Declare in the **latest user message**:

```text
Mode: documentation-edit

Allowed files:
- docs/rules.md
- docs/protected-files/registry.md
```

| Rule | Behavior |
| --- | --- |
| Scope | Edit **only** listed paths that exist in the manifest |
| Code and tests | Read-only — mixed doc + code changes are blocked |
| Authoritative categories | Present proposed diff before applying |
| Explanatory categories | Direct edit when the request clearly defines the change |
| Unlisted protected paths | Block |
| `generated` | Block even if listed |

Structured fields (no free-form “requested change” parsing):

- `Mode: documentation-edit`
- `Allowed files:` — bullet list of repo-relative paths
- `Implementation impact report:` — same format; required in implementation mode when syncing explanatory docs

---

## Explanatory-sync exception (implementation mode only)

Applies to `explanatory` and `architecture_explanatory`. **All** conditions must be true; otherwise require documentation-edit mode.

| # | Condition |
| --- | --- |
| 1 | Describes behavior **already present** in the approved plan and authoritative documentation |
| 2 | Adds **no new requirement** |
| 3 | Changes **no responsibility boundary** |
| 4 | Changes **no schema, contract, state, or source of truth** |
| 5 | Does **not** use normative language (`must`, `shall`, `required`, `forbidden`) except when **directly quoting** an authoritative source |
| 6 | The changed file is listed in the **Implementation impact report** |

**Mechanically enforced** (hooks): #5 (normative language in added diff lines), #6 (path in impact report list).

**Agent policy** (owner review): #1–4.

Example implementation-mode header:

```text
Implementation impact report:
- docs/audit/MAINTENANCE.md
```

---

## Denial messages

| Situation | Message |
| --- | --- |
| Authoritative edit without documentation-edit mode | `RESTRICTED DOCUMENTATION PHASE REQUIRED — IMPLEMENTATION BLOCKED` |
| Protected path outside allowed list | `RESTRICTED-FILE EDIT NOT AUTHORIZED` |
| Doc mode needs another protected file | `ADDITIONAL RESTRICTED FILE REQUIRES AUTHORIZATION` |
| Code + authoritative doc in same turn | `MIXED RESTRICTED-FILE AND IMPLEMENTATION TASK — BLOCKED` |
| `generated` path touched | `GENERATED FILE — MANUAL EDIT BLOCKED` |
| Explanatory sync without impact report entry | `EXPLANATORY SYNC VIOLATION — NOT IN IMPACT REPORT` |
| Explanatory sync adds normative language | `EXPLANATORY SYNC VIOLATION — NORMATIVE LANGUAGE` |

Each denial must name affected paths, categories, and the required mode or decision.

---

## Required reading (before significant work)

| When | Read first |
| --- | --- |
| Any non-trivial feature or architecture change | [`docs/rules.md`](../rules.md) |
| Feature planning | [`docs/process/plan_review_gate.md`](../process/plan_review_gate.md), [`docs/core/3. component_responsibilities.md`](../core/3.%20component_responsibilities.md) |
| Desktop / API work | Matching files under [`docs/desktopApp/`](../desktopApp/) |
| Node / workflow authoring | [`audits/contracts/nodes/`](../audits/contracts/nodes/00-START-HERE.md) and [`audits/contracts/runtime/`](../audits/contracts/runtime/) |
| Standards pack / node content | Relevant files under `knowledge/standards/` |
| Audit or “what exists today” questions | [`docs/audit/INDEX.md`](../audit/INDEX.md) |

Do not use protected files as a substitute for reading implementation code; use both.

---

## Ownership

| Category | Owner approval for changes |
| --- | --- |
| `constitutional`, `agent_rule` | Project owner |
| `contract`, `architecture_authoritative` | Project owner + architecture review when behavior changes |
| `explanatory`, `architecture_explanatory` | Implementation sync under exception; otherwise documentation-edit mode |
| `generated` | Rebuild via scripts — never hand-edit |

---

## Maintaining protected paths

1. Add or reclassify paths in [config/restricted_paths.yaml](../../config/restricted_paths.yaml) only.
2. Update this registry when **policy or ownership** changes — not to duplicate path lists.
3. Do not duplicate path lists in `.cursor/rules/` or other agent rules.
4. Prefer `python scripts/build_graph_db.py` and related build scripts over editing `generated` artifacts.
