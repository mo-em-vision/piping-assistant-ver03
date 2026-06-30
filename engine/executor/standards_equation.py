"""Execute companion .py calculations co-located with standards equation files."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from engine.executor.calculation_engine import load_formula_text
from engine.executor.formula_loader import read_formula_text
from engine.reference.standards_reader import NodeRecord, StandardsReader
from models.calculation import CalculationResult, CalculationStatus, CalculationStep, QuantityResult


def execute_standards_equation(
    *,
    node_dir: Path,
    py_filename: str,
    md_filename: str,
    calculation_id: str,
    variables: dict[str, float],
    reader: StandardsReader | None = None,
    record: NodeRecord | None = None,
    equation_meta: dict[str, Any] | None = None,
) -> CalculationResult:
    """Run ``compute(variables)`` from a node-root ``*.py`` equation module."""
    py_path = node_dir / py_filename
    if not py_path.is_file():
        legacy = node_dir / "equations" / py_filename
        if legacy.is_file():
            py_path = legacy
    if not py_path.is_file():
        raise FileNotFoundError(f"Missing equation calculation module: {py_path}")

    formula_text = read_formula_text(
        reader=reader,
        record=record,
        file_ref=f"equations/{md_filename}",
        equation_meta=equation_meta,
        node_dir=node_dir,
    )
    formula_data: dict[str, Any] = load_formula_text(formula_text or "")

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
