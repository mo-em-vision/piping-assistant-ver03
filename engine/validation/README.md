# engine/validation/

Deterministic compliance gate before and during execution.

## Purpose

`ValidationEngine` orchestrates five validators: conflicts, per-node inputs, units, engineering limits, and dependency outputs. Failures block `Executor.execute_plan`.

## Entry Points

| Symbol | File |
|--------|------|
| `ValidationEngine` | `validation_engine.py` |
| `validate_task_input_units` | `unit_validator.py` (standalone helper) |

## Dependencies

**Depends on:** `engine/reference/`, `engine/events/`, `engine/graph/assumption_checker`, `engine/executor/unit_manager`, `engine/units/`, `models/validation`

**Used by:** `engine/executor/executor.py`, acceptance/MVP tests, `tests/e2e/scenario_runner.py`

## Runtime Usage

**Active.** Every `Executor.execute_plan` calls `validate_plan` first; per-node validation during execution loop.

## Possible Dead Code

None identified at module level. Sub-validators are only used via `ValidationEngine`.

## Notes

- Not the same as `engine/rules/rule_engine.py` (node condition expressions during execution).
- `UnitValidator` has both class API and module-level `validate_task_input_units` for API/tests.

## Execution Traces

```
Executor.execute_plan
  → ValidationEngine.validate_plan(plan, task)
    → ConflictValidator.validate_task
    → InputValidator.validate_node_inputs (per node)
  → (during node loop) validate_node_execution
    → EngineeringValidator, UnitValidator, DependencyValidator
  → EventLogger on failures
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Export `ValidationEngine` | — | external |
| `conflict_validator.py` | Input conflict detection | `ConflictValidator` | validation_engine |
| `dependency_validator.py` | Required dependency outputs | `DependencyValidator` | validation_engine |
| `engineering_validator.py` | Limitations, material/temp rules | `EngineeringValidator` | validation_engine |
| `input_validator.py` | Required inputs per node | `InputValidator` | validation_engine |
| `unit_validator.py` | Unit compatibility | `UnitValidator`, `validate_task_input_units` | validation_engine, api tests |
| `validation_engine.py` | **Coordinator** | `ValidationEngine` | executor, tests |
