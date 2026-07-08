# engine/equation/

SymPy-based equation evaluation, generic equation display traces, and four-step display rendering for micro-graph equation nodes.

## Purpose

- `sympy_evaluator.evaluate_equation` runs sympy equation nodes at execution time.
- `equation_display_trace_builder.build_equation_display_trace` builds the canonical `equation_display_trace` for all equation executors (sympy and function-based).
- `latex_format.py` provides shared KaTeX formatting (numeric values, `\mathrm{}` units, substituted terms).
- `equation_renderer.render_equation_steps` optionally enriches evaluated traces (sympy path).

## Entry Points

| Symbol | File |
|--------|------|
| `evaluate_equation` | `sympy_evaluator.py` |
| `build_equation_display_trace` | `equation_display_trace_builder.py` |
| `enrich_equation_block` | `display_trace_serializer.py` |
| `render_equation_steps` | `equation_renderer.py` |
| `format_substituted_equation` | `latex_format.py` |

## Dependencies

**Depends on:** SymPy (external), `models/equation_display_trace.py`, `engine/reference/parameter_value_source.py`

**Used by:** `engine/executor/node_runner.py`, `api/equation_evaluation_display.py`, `engine/presentation/blocks.py`, `engine/graph/display_emitter.py`, tests

## Runtime Usage

**Active** for micro-graph `equation` nodes executed by `NodeRunner`. Execution trace entries include `equation_display_trace` when an equation completes.

## Execution Traces

```
NodeRunner (equation node)
  → evaluate (sympy or executor function)
  → build_equation_display_trace(metadata, facts, CalculationResult, render_steps?)
  → trace.equation_display_trace on NodeExecutionResult
  → api/equation_display_trace_serializer.enrich_equation_block
  → EquationOutputBlock.equation_display_trace (desktop)
```

## Per-file inventory

| File | Purpose | Key exports |
|------|---------|-------------|
| `__init__.py` | Public exports | `build_equation_display_trace`, `enrich_equation_block`, … |
| `equation_display_trace_builder.py` | Generic trace builder | `build_equation_display_trace` |
| `display_trace_serializer.py` | Block enrichment | `enrich_equation_block`, `find_trace_for_equation` |
| `latex_format.py` | Shared KaTeX helpers | `format_substituted_equation`, `format_unit_latex` |
| `equation_renderer.py` | 4-step SymPy display | `EquationRenderSteps`, `render_equation_steps` |
| `sympy_evaluator.py` | Numeric equation eval | `EquationEvalResult`, `evaluate_equation` |
