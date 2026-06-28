"""Approved execution function registry."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from engine.executor.calculation_engine import CalculationEngine
from engine.executor.standards_equation import execute_standards_equation
from models.calculation import CalculationResult

CalculationFn = Callable[..., CalculationResult]

_calculation_engine = CalculationEngine()


def calculate_wall_thickness(
    *,
    node_dir: Path,
    variables: dict[str, float],
) -> CalculationResult:
    formula_path = node_dir / "equations" / "wall_thickness.md"
    return _calculation_engine.execute_from_file(
        calculation_id="B313-304.1.2:wall_thickness",
        formula_path=formula_path,
        variables=variables,
    )


def calculate_allowable_displacement_stress_range(
    *,
    node_dir: Path,
    variables: dict[str, float],
) -> CalculationResult:
    return execute_standards_equation(
        node_dir=node_dir,
        py_filename="eq_1a_allowable_displacement_stress_range.py",
        md_filename="eq_1a_allowable_displacement_stress_range.md",
        calculation_id="B313-302.3.5:eq-1a",
        variables=variables,
    )


def calculate_allowable_displacement_stress_range_with_margin(
    *,
    node_dir: Path,
    variables: dict[str, float],
) -> CalculationResult:
    return execute_standards_equation(
        node_dir=node_dir,
        py_filename="eq_1b_allowable_displacement_stress_range_with_margin.py",
        md_filename="eq_1b_allowable_displacement_stress_range_with_margin.md",
        calculation_id="B313-302.3.5:eq-1b",
        variables=variables,
    )


def calculate_stress_range_factor(
    *,
    node_dir: Path,
    variables: dict[str, float],
) -> CalculationResult:
    return execute_standards_equation(
        node_dir=node_dir,
        py_filename="eq_1c_stress_range_factor.py",
        md_filename="eq_1c_stress_range_factor.md",
        calculation_id="B313-302.3.5:eq-1c",
        variables=variables,
    )


def calculate_minimum_required_thickness(
    *,
    node_dir: Path,
    variables: dict[str, float],
) -> CalculationResult:
    formula_path = node_dir / "equations" / "eq_2_minimum_required_thickness.md"
    return _calculation_engine.execute_from_file(
        calculation_id="B313-304.1.1:eq-2",
        formula_path=formula_path,
        variables=variables,
    )


def calculate_pressure_design_thickness(
    *,
    node_dir: Path,
    variables: dict[str, float],
) -> CalculationResult:
    formula_path = node_dir.parent / "mawp_definition" / "equations" / "pressure_design_thickness.md"
    return _calculation_engine.execute_from_file(
        calculation_id="B313-MAWP-PRESSURE-DESIGN:pressure_design_thickness",
        formula_path=formula_path,
        variables=variables,
    )


def calculate_mawp(
    *,
    node_dir: Path,
    variables: dict[str, float],
) -> CalculationResult:
    formula_path = node_dir.parent / "304.1.2" / "equations" / "mawp_pressure.md"
    return _calculation_engine.execute_from_file(
        calculation_id="B313-MAWP-CALCULATION:mawp_pressure",
        formula_path=formula_path,
        variables=variables,
    )


REGISTERED_FUNCTIONS: dict[str, CalculationFn] = {
    "calculate_wall_thickness": calculate_wall_thickness,
    "calculate_minimum_required_thickness": calculate_minimum_required_thickness,
    "calculate_pressure_design_thickness": calculate_pressure_design_thickness,
    "calculate_mawp": calculate_mawp,
    "calculate_allowable_displacement_stress_range": calculate_allowable_displacement_stress_range,
    "calculate_allowable_displacement_stress_range_with_margin": (
        calculate_allowable_displacement_stress_range_with_margin
    ),
    "calculate_stress_range_factor": calculate_stress_range_factor,
}


def get_execution_function(name: str) -> CalculationFn | None:
    return REGISTERED_FUNCTIONS.get(name)
