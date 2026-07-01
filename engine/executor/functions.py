"""Approved execution function registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from engine.executor.calculation_engine import CalculationEngine
from engine.executor.formula_loader import read_formula_text
from engine.executor.standards_equation import execute_standards_equation
from engine.reference.standards_reader import NodeRecord, StandardsReader
from models.calculation import CalculationResult

CalculationFn = Callable[..., CalculationResult]

_calculation_engine = CalculationEngine()


def _run_formula(
    *,
    calculation_id: str,
    node_dir: Path,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
    file_ref: str | None = None,
    fallback_node_id: str | None = None,
) -> CalculationResult:
    formula_text = read_formula_text(
        reader=reader,
        record=record,
        file_ref=file_ref,
        equation_meta=equation_meta,
        fallback_node_id=fallback_node_id,
        node_dir=node_dir,
    )
    if not formula_text:
        raise FileNotFoundError(f"Missing formula definition for {calculation_id}")
    return _calculation_engine.execute_from_text(
        calculation_id=calculation_id,
        formula_text=formula_text,
        variables=variables,
    )


def calculate_wall_thickness(
    *,
    node_dir: Path,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
    **_: Any,
) -> CalculationResult:
    return _run_formula(
        calculation_id="B313-304.1.2:wall_thickness",
        node_dir=node_dir,
        variables=variables,
        reader=reader,
        record=record,
        equation_meta=equation_meta,
        file_ref="equations/wall_thickness.md",
        fallback_node_id="B313-304.1.2",
    )


def calculate_allowable_displacement_stress_range(
    *,
    node_dir: Path,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
    **_: Any,
) -> CalculationResult:
    return execute_standards_equation(
        node_dir=node_dir,
        py_filename="eq_1a_allowable_displacement_stress_range.py",
        md_filename="eq_1a_allowable_displacement_stress_range.md",
        calculation_id="B313-302.3.5:eq-1a",
        variables=variables,
        reader=reader,
        record=record,
        equation_meta=equation_meta,
    )


def calculate_allowable_displacement_stress_range_with_margin(
    *,
    node_dir: Path,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
    **_: Any,
) -> CalculationResult:
    return execute_standards_equation(
        node_dir=node_dir,
        py_filename="eq_1b_allowable_displacement_stress_range_with_margin.py",
        md_filename="eq_1b_allowable_displacement_stress_range_with_margin.md",
        calculation_id="B313-302.3.5:eq-1b",
        variables=variables,
        reader=reader,
        record=record,
        equation_meta=equation_meta,
    )


def calculate_stress_range_factor(
    *,
    node_dir: Path,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
    **_: Any,
) -> CalculationResult:
    return execute_standards_equation(
        node_dir=node_dir,
        py_filename="eq_1c_stress_range_factor.py",
        md_filename="eq_1c_stress_range_factor.md",
        calculation_id="B313-302.3.5:eq-1c",
        variables=variables,
        reader=reader,
        record=record,
        equation_meta=equation_meta,
    )


def calculate_minimum_required_thickness(
    *,
    node_dir: Path,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
    **_: Any,
) -> CalculationResult:
    return _run_formula(
        calculation_id="304.1.1:eq-2",
        node_dir=node_dir,
        variables=variables,
        reader=reader,
        record=record,
        equation_meta=equation_meta,
        file_ref="304.1.1/equations/eq-2.md",
        fallback_node_id="304.1.1",
    )


def calculate_pressure_design_thickness(
    *,
    node_dir: Path,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
    **_: Any,
) -> CalculationResult:
    return _run_formula(
        calculation_id="B313-MAWP-PRESSURE-DESIGN:pressure_design_thickness",
        node_dir=node_dir,
        variables=variables,
        reader=reader,
        record=record,
        equation_meta=equation_meta,
        file_ref="equations/pressure_design_thickness.md",
        fallback_node_id="B313-MAWP-SECTION",
    )


def calculate_mawp(
    *,
    node_dir: Path,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
    **_: Any,
) -> CalculationResult:
    return _run_formula(
        calculation_id="B313-MAWP-CALCULATION:mawp_pressure",
        node_dir=node_dir,
        variables=variables,
        reader=reader,
        record=record,
        equation_meta=equation_meta,
        file_ref="equations/mawp_pressure.md",
        fallback_node_id="B313-304.1.2",
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
