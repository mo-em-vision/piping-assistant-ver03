"""Execute companion .py calculations co-located with standards equation files."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from engine.executor.calculation_engine import load_formula_file
from models.calculation import CalculationResult, CalculationStatus, CalculationStep, QuantityResult


def execute_standards_equation(
    *,
    node_dir: Path,
    py_filename: str,
    md_filename: str,
    calculation_id: str,
    variables: dict[str, float],
) -> CalculationResult:
    """Run ``compute(variables)`` from a node ``equations/*.py`` module."""
    md_path = node_dir / "equations" / md_filename
    py_path = node_dir / "equations" / py_filename
    if not py_path.exists():
        raise FileNotFoundError(f"Missing equation calculation module: {py_path}")

    formula_data: dict[str, Any] = load_formula_file(md_path) if md_path.exists() else {}

    spec = importlib.util.spec_from_file_location(f"standards_equation_{py_path.stem}", py_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load equation module: {py_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    compute = getattr(module, "compute", None)
    if not callable(compute):
        raise AttributeError(f"Equation module must define compute(variables): {py_path}")

    symbol, value, unit = compute(variables)
    return CalculationResult(
        calculation_id=calculation_id,
        inputs=variables,
        formula={
            "display": formula_data.get("display"),
            "equation_id": formula_data.get("equation_id"),
        },
        steps=[
            CalculationStep(
                name="compute",
                inputs=dict(variables),
                result={symbol: value},
            )
        ],
        final_result=QuantityResult(symbol=symbol, value=float(value), unit=unit),
        status=CalculationStatus.PASS,
    )
