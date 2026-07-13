"""Reference data and regression helpers for MVP strategy tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.executor.unit_manager import convert_to_si
from models.task import Task
from tests.helpers.facts import fact_get_unit, fact_get_value

_PRESSURE_KEYS = ("design_pressure", "internal_design_gage_pressure", "P")
_DIAMETER_KEYS = ("outside_diameter", "D")
_CORROSION_KEYS = ("corrosion_allowance", "c")


def _fact_quantity(task: Task, keys: tuple[str, ...]) -> tuple[float, str]:
    for key in keys:
        try:
            return float(fact_get_value(task, key)), fact_get_unit(task, key)
        except KeyError:
            continue
    raise KeyError(keys)


def expected_wall_thickness(task: Task) -> float:
    p_value, p_unit = _fact_quantity(task, _PRESSURE_KEYS)
    d_value, d_unit = _fact_quantity(task, _DIAMETER_KEYS)
    p_pa, _ = convert_to_si(p_value, p_unit)
    d_mm, _ = convert_to_si(d_value, d_unit)
    s_pa = float(task.outputs.get("allowable_stress", task.outputs.get("S", 0)))
    e = 1.0
    w = 1.0
    y = 0.4
    sew = s_pa * e * w
    py = p_pa * y
    return p_pa * d_mm / (2 * (sew + py))


def expected_minimum_required_thickness(task: Task) -> float:
    thickness_t = task.outputs.get("t", task.outputs.get("required_thickness"))
    if thickness_t is None:
        thickness_t = expected_wall_thickness(task)
    else:
        thickness_t = float(thickness_t)
    c_value, c_unit = _fact_quantity(task, _CORROSION_KEYS)
    c_mm, _ = convert_to_si(c_value, c_unit, target_unit="mm")
    return thickness_t + float(c_mm)


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
        elif isinstance(spec, dict) and spec.get("formula") == "minimum_required_thickness":
            tolerance = float(spec.get("tolerance", 1e-6))
            expected_value = expected_minimum_required_thickness(task)
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
