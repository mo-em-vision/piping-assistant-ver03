# Intentionally deferred (per design / current scope)

## Calculation execution

reports reflect task state; incomplete tasks show missing inputs until the executor stores results in `task.outputs`.

## Integrity / audit / summary report types

template stubs only (`integrity_report.md`, `audit_report.md`).

## Full traversal trace

populated from task + standards where available; richer trace waits on workflow executor (STEP 4/5).

**Deferred:** CLI bootstrap (`task execute`), Workflow Engine (STEP 6), full Validation Layer, parallel execution.



## Out of scope (stubs only)

- Multi-standard packs beyond ASME B31.3 (candidates listed, not executable)
- Full ambiguity UI / user branch selection in CLI (return `CLARIFY` with options)
- Workflow Engine (STEP 6) — planner uses graph roots directly
- Planner content in engineering reports (doc 11 §22 — audit field only)

