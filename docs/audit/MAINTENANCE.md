# Architecture audit — maintenance

Living documentation workflow: keep audit files aligned with the code as you edit.

See also: [INDEX.md](INDEX.md) (all audit paths and section anchors), [PROGRESS.md](PROGRESS.md) (completion status).

---

## When to update

Update audit docs **in the same change** (or immediately after) when you:

- Add, remove, or rename files in an audited folder
- Change entry points (CLI commands, API routes, Electron startup, scripts)
- Alter who imports whom (new coupling or decoupling)
- Move code on/off the runtime path
- Introduce or remove a parallel implementation
- Change an end-to-end flow (desktop, CLI, compile pipeline)

**Do not** rewrite audit docs for trivial edits (comments, formatting) unless the described behavior changes.

---

## Change checklist

After a code change, walk this list for the **affected folder(s)**:

1. **`#files`** — table row for each touched file
2. **`#entry-points`** — if invoke path changed
3. **`#dependencies`** — grep importers/imports; update both directions
4. **`#runtime-usage`** — still on path? proof (test name or import chain)
5. **`#per-file-inventory`** — public API, inputs/outputs, side effects for changed files
6. **`#execution-traces`** — if call chain changed
7. **`#possible-dead-code`** — move items if usage changed
8. **Cross-cutting** — if needed:
   - [DUPLICATES.md](DUPLICATES.md)
   - [EXECUTION_TRACES.md](EXECUTION_TRACES.md)
   - [ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md) (repo-level only)

Set **Confidence** (High / Medium / Low) when uncertain; use *Unknown from static analysis.* when you cannot prove from code.

---

## How to ask the agent to update a section

Use `@audit` citations so the agent opens the right file and section:

```text
@audit api/README.md#files — add the new report_batch route
@audit docs/audit/EXECUTION_TRACES.md#report-generation — trace now goes through ReportQueue
```

You can also paste a markdown link:

```text
Update [engine/planner/README.md#execution-traces](../../engine/planner/README.md#execution-traces)
for the new phased navigation path.
```

The agent should:

1. Read the cited section
2. Re-grep / read code for evidence
3. Edit only the affected sections (surgical doc diff)
4. Mention which sections were updated in the PR/summary

---

## Standard section template

When creating a **new** audited folder, add `README.md` with these headings (stable anchors):

```markdown
# <folder>/ — Architecture Audit

## Purpose
## Files
## Entry Points
## Dependencies
### This folder depends on
### Who depends on this folder
## Runtime Usage
## Possible Dead Code
## Notes
## Execution traces
## Per-file inventory
```

---

## Audit-only vs living sync

| Mode | When | Rules |
|------|------|-------|
| **Audit-only** | Deliberate documentation pass | No code changes; accuracy over speed ([Architecture Audit Mode](../todo/Architecture%20Audit%20Mode.md)) |
| **Living sync** | Normal feature/fix work | Code + matching audit sections updated together |

Living sync does **not** require re-auditing entire folders—only sections impacted by your diff.

---

## Files *not* in the audit set

- `README.md` (repo root) — user onboarding; do not merge audit content here
- `desktopApp/docs/README.md` — desktop setup guide
- `docs/core/*` — design intent (may drift from implementation; audit docs describe *what is*)

---

## Verification

After audit edits:

- Links in [INDEX.md](INDEX.md) still resolve
- No recommendation language (“should use X instead”) — document duplicates, do not prescribe
- Date stamp optional: `Audit date: YYYY-MM-DD` at top of heavily edited READMEs
