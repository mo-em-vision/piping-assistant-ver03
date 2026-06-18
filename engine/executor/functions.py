"""Approved execution function registry."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from engine.executor.calculation_engine import CalculationEngine, load_formula_file
from models.calculation import CalculationResult

CalculationFn = Callable[..., CalculationResult]

_calculation_engine = CalculationEngine()


def calculate_wall_thickness(
    *,
    node_dir: Path,
    variables: dict[str, float],
) -> CalculationResult:
    formula_path = node_dir / "formulas" / "wall_thickness.md"
    return _calculation_engine.execute_from_file(
        calculation_id="B313-304.1.1:wall_thickness",
        formula_path=formula_path,
        variables=variables,
    )


REGISTERED_FUNCTIONS: dict[str, CalculationFn] = {
    "calculate_wall_thickness": calculate_wall_thickness,
}


def get_execution_function(name: str) -> CalculationFn | None:
    return REGISTERED_FUNCTIONS.get(name)
