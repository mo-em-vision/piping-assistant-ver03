"""Reference data and regression helpers for MVP strategy tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.executor.unit_manager import convert_to_si
from models.task import Task


def expected_wall_thickness(task: Task) -> float:
    p_pa, _ = convert_to_si(float(task.inputs["design_pressure"].value), task.inputs["design_pressure"].unit)
    d_mm, _ = convert_to_si(float(task.inputs["outside_diameter"].value), task.inputs["outside_diameter"].unit)
    s_pa = float(task.outputs.get("allowable_stress", task.outputs.get("S", 0)))
    e = 1.0
    w = 1.0
    y = 0.4
    sew = s_pa * e * w
    py = p_pa * y
    return p_pa * d_mm / (2 * (sew + py))


def load_expected(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_regression_outputs(task: Task, expected: dict[str, Any]) -> None:
    outputs = expected.get("outputs", {})
    for key, spec in outputs.items():
        actual = task.outputs.get(key)
        if isinstance(spec, dict) and spec.get("formula") == "wall_thickness":
            tolerance = float(spec.get("tolerance", 1e-6))
            expected_value = expected_wall_thickness(task)
            assert actual is not None
            assert abs(float(actual) - expected_value) <= tolerance
        elif isinstance(spec, (int, float)):
            assert actual is not None
            assert abs(float(actual) - float(spec)) < 1e-6
        else:
            assert actual == spec


def compute_reference_thickness(
    *,
    pressure_psi: float = 500,
    diameter_in: float = 10,
    allowable_stress_pa: float = 193_000_000.0,
) -> float:
    p_pa, _ = convert_to_si(pressure_psi, "psi")
    d_mm, _ = convert_to_si(diameter_in, "in")
    e = 1.0
    w = 1.0
    y = 0.4
    sew = allowable_stress_pa * e * w
    py = p_pa * y
    return p_pa * d_mm / (2 * (sew + py))
