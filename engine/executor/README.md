# engine/executor/

Deterministic workflow runtime: execute `ExecutionPlan` nodes, table lookups, SymPy equations, and registered formula functions.

## Purpose

`Executor` walks the plan; `NodeRunner` executes one node (lookup, equation, calculation, text). Side-effect resolvers apply coefficient/stress/NPS lookups to task inputs before or during planning.

## Entry Points

| Symbol | File |
|--------|------|
| `Executor`, `execute_workflow` | `executor.py` |
| `NodeRunner` | `node_runner.py` |
| `get_execution_function` | `functions.py` |
| `LookupEngine` | `lookup_engine.py` |
| `apply_*_lookup` resolvers | `*_resolver.py`, `coefficient_lookup.py` |

## Dependencies

**Depends on:** `engine/graph/`, `engine/validation/`, `engine/events/`, `engine/execution/`, `engine/inspection/` (trace), `engine/equation/`, `engine/rules/`, `engine/reference/`, `engine/units/` (via unit_manager), `models/execution`

**Used by:** `api/workflow_bootstrap.py`, `api/parameter_definitions.py`, `api/output_blocks.py`, `api/material_detail.py`, acceptance/e2e tests

## Runtime Usage

**Active.** `execute_workflow` is the main high-level entry for running a planned workflow end-to-end.

## Possible Dead Code

| Item | Confidence |
|------|------------|
| `formula_loader.load_formula_data` | **High** — defined, never imported |
| `CalculationEngine` direct use outside `functions.py` | **Low** — used via registry; tests import directly |

## Notes

- **Resolver modules** (`allowable_stress_resolver`, `coefficient_lookup`, `nps_input_resolver`, `mawp_geometry_resolver`) mutate `Task.inputs` during API bootstrap — not inside `NodeRunner` for all paths.
- `expression_evaluator` is shared with `rules/rule_engine.py`.
- `standards_equation.py` runs companion `.py` next to equation assets.

## Execution Traces

```
execute_workflow(task_id, reader, state)
  → GraphEngine.build_plan
  → Executor.execute_plan
    → ValidationEngine.validate_plan
    → for node_id in plan.execution_order:
        → NodeRunner.run(node_id, ...)
          → get_execution_function / LookupEngine / evaluate_equation
          → RuleEngine (conditions)
    → definition_equations.try_complete_definition_equations
    → inspection.trace (if enabled)
    → TaskStateManager.store_output
```

```
api/parameter_definitions (input edit)
  → apply_allowable_stress_lookup / apply_coefficient_lookups / apply_nominal_pipe_size_lookup
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Lazy exports | `Executor`, `execute_workflow`, engines | tests, external |
| `allowable_stress_resolver.py` | Material+temp → S | `apply_allowable_stress_lookup` | parameter_definitions |
| `calculation_engine.py` | Multi-step formula YAML execution | `CalculationEngine`, `load_formula_file` | functions, tests |
| `coefficient_lookup.py` | E, W, Y auto-apply | `apply_coefficient_lookups` | workflow_bootstrap, parameter_definitions |
| `executor.py` | **Plan runner** | `Executor`, `execute_workflow` | api, tests |
| `expression_evaluator.py` | Safe AST math | `evaluate_expression` | calculation_engine, rule_engine |
| `formula_loader.py` | Load formula text from nodes | `read_formula_text` | functions, node_runner |
| `functions.py` | Registered calc functions | `get_execution_function`, `calculate_*` | node_runner |
| `lookup_engine.py` | Standards table lookup | `LookupEngine` | node_runner |
| `material_properties_lookup.py` | ASTM mechanical props | `MaterialPropertiesLookup` | api/material_detail |
| `mawp_geometry_resolver.py` | MAWP NPS/schedule geometry | `apply_pipe_schedule_lookup`, … | workflow_bootstrap, tests |
| `node_runner.py` | **Per-node execution** | `NodeRunner` | executor |
| `nps_input_resolver.py` | NPS → outside diameter | `apply_nominal_pipe_size_lookup` | parameter_definitions, mawp_geometry |
| `pipe_dimension_lookup.py` | B36.10 dimensions | `PipeDimensionLookup` | node_runner |
| `pipe_schedule_recommendation.py` | Schedule recommendation | `recommend_pipe_schedule_for_task` | output_blocks |
| `standards_equation.py` | Run equation `.py` scripts | `execute_standards_equation` | functions |
| `unit_manager.py` | SI conversion for calcs | `prepare_engineering_input`, `convert_to_si` | node_runner, api, tests |
