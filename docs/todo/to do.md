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

tests:

## **Optional follow-up tests (if you want them)**

- Binary PDF golden-file comparison under `tests/data/expected/`
- E2E scenarios with mocked LLM for full chat lifecycle (request → question → answer → report)
- Scenarios for unimplemented workflows (`integrity_check`, `pressure_test_verification`) once those roots are executable



## Out of scope (for now)

- LLM-based input extraction fallback (planned in docs but not required for this fix; deterministic path covers your case and keeps tests stable with `FakeLLMClient`)
- Auto-mapping mislabeled `Pressure: 4 inch` to diameter (explicitly rejected per your choice)

before expanding a path, for example pipe thickness, first make sure that all the assumptions in the node are met, (if the user hasn't provided them, then ask). for example the pipe thickness has to first check if the pipe is internally or externally stressed (it has to have an assumptions field with limitations on expanding the node, or the default values used). the formula t=PD/2(SE+PY) currently in the node is only valid for internally stressed pipes. 