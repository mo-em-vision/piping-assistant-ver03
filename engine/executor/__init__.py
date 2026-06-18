"""Execution Layer public exports."""

from .calculation_engine import CalculationEngine, load_formula_file
from .expression_evaluator import UnsafeExpressionError, evaluate_expression
from .functions import REGISTERED_FUNCTIONS, get_execution_function
from .lookup_engine import LookupEngine, LookupResult
from .node_runner import NodeRunner
from .unit_manager import convert_to_si, prepare_engineering_input

__all__ = [
    "CalculationEngine",
    "Executor",
    "LookupEngine",
    "LookupResult",
    "NodeRunner",
    "REGISTERED_FUNCTIONS",
    "UnsafeExpressionError",
    "convert_to_si",
    "evaluate_expression",
    "execute_workflow",
    "get_execution_function",
    "load_formula_file",
    "prepare_engineering_input",
]


def __getattr__(name: str):
    if name == "Executor":
        from .executor import Executor

        return Executor
    if name == "execute_workflow":
        from .executor import execute_workflow

        return execute_workflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
