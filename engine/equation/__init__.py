"""Equation evaluation and rendering."""

from engine.equation.display_trace_serializer import (
    enrich_equation_block,
    find_trace_for_equation,
    find_trace_in_execution_payload,
    trace_from_dict,
    trace_to_dict,
)
from engine.equation.equation_display_trace_builder import build_equation_display_trace
from engine.equation.equation_renderer import EquationRenderSteps, render_equation_steps
from engine.equation.sympy_evaluator import EquationEvalResult, evaluate_equation

__all__ = [
    "EquationEvalResult",
    "EquationRenderSteps",
    "build_equation_display_trace",
    "enrich_equation_block",
    "evaluate_equation",
    "find_trace_for_equation",
    "find_trace_in_execution_payload",
    "render_equation_steps",
    "trace_from_dict",
    "trace_to_dict",
]
