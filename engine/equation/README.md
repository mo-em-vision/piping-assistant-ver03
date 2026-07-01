# engine/equation/

SymPy-based equation evaluation and four-step display rendering for micro-graph equation nodes.

## Purpose

`sympy_evaluator.evaluate_equation` runs equation nodes at execution time; `equation_renderer.render_equation_steps` produces substitution/result steps for UI and reports.

## Entry Points

| Symbol | File |
|--------|------|
| `evaluate_equation` | `sympy_evaluator.py` |
| `render_equation_steps` | `equation_renderer.py` |

## Dependencies

**Depends on:** SymPy (external), `engine/equation/equation_renderer` (evaluator imports renderer)

**Used by:** `engine/executor/node_runner.py`, `engine/graph/display_emitter.py` (via node results), tests

## Runtime Usage

**Active** for micro-graph `equation` nodes executed by `NodeRunner`.

## Possible Dead Code

None identified.

## Notes

- Renderer is Phase 10 four-step pipeline (general → substituted → numeric → result).
- Public re-exports in `__init__.py`: `EquationRenderSteps`, `render_equation_steps`, `evaluate_equation`.

## Execution Traces

```
NodeRunner (equation node)
  → sympy_evaluator.evaluate_equation(sympy_expr, inputs, outputs)
    → equation_renderer.render_equation_steps (for display trace)
  → outputs stored on task
```

## Per-file inventory

| File | Purpose | Key exports | Importers |
|------|---------|-------------|-----------|
| `__init__.py` | Public exports | `evaluate_equation`, `render_equation_steps` | external |
| `equation_renderer.py` | 4-step SymPy display | `EquationRenderSteps`, `render_equation_steps` | sympy_evaluator, tests |
| `sympy_evaluator.py` | Numeric equation eval | `EquationEvalResult`, `evaluate_equation` | node_runner, tests |
