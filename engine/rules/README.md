# engine/rules/

Minimal rule/condition evaluation for node metadata during execution.

## Purpose

`RuleEngine` evaluates safe arithmetic/boolean expressions from node `conditions` using `expression_evaluator`. **Not** the full `ValidationEngine` compliance layer.

## Entry Points

| Symbol | File |
|--------|------|
| `RuleEngine` | `rule_engine.py` |

## Dependencies

**Depends on:** `engine/executor/expression_evaluator.py`

**Used by:** `engine/executor/node_runner.py`, `tests/rules/`

## Runtime Usage

**Active** inside `NodeRunner` when nodes define executable conditions.

## Possible Dead Code

None.

## Notes

- `rules/__init__.py` exports `ConditionResult`, `RuleEngine`.
- Planner's `RuleTools` (in `engine/planner/tools.py`) is unrelated — reads limitation strings only.

## Execution Traces

```
NodeRunner.run
  → RuleEngine.evaluate_condition / evaluate_rules
  → expression_evaluator.evaluate_expression
  → pass/fail affects node execution result
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Public exports | `RuleEngine`, `ConditionResult` | external |
| `rule_engine.py` | Condition evaluation | `RuleEngine` | node_runner, tests |
