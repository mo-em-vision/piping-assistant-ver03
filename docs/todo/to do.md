# Intentionally deferred (per design / current scope)



## Integrity / audit / summary report types

template stubs only (`integrity_report.md`, `audit_report.md`).

## Full traversal trace

**Deferred:** CLI bootstrap (`task execute`), Workflow Engine (STEP 6), full Validation Layer, parallel execution.

## Out of scope (stubs only)

- Multi-standard packs beyond ASME B31.3 (candidates listed, not executable)
- Full ambiguity UI / user branch selection in CLI (return `CLARIFY` with options)
- Workflow Engine (STEP 6) — planner uses graph roots directly
- Planner content in engineering reports (doc 11 §22 — audit field only)



## **Deferred (per MVP scope)**

- CLI override UI for `validation_overrides`
- Orchestrator pre-chat validation (runs at execution time today)
- Separate `rules/*.yaml` files for all engineering rules
- Multi-standard conflict resolution beyond `task.conflicts`

