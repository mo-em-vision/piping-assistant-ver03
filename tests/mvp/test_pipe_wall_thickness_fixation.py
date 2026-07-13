"""Pipe wall thickness fixation scenarios — verify t_m from fixed user inputs."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.scenario_loader import load_scenario
from tests.e2e.scenario_runner import ScenarioRunner
from tests.helpers.facts import fact_get_unit, fact_get_value
from tests.mvp.regression import expected_minimum_required_thickness, expected_wall_thickness

FIXATION_SCENARIOS = (
    "pipe_wall_thickness_fixation_zero_corrosion",
    "pipe_wall_thickness_fixation_with_corrosion",
)


def _corrosion_allowance_mm(task) -> float:
    from engine.executor.unit_manager import convert_to_si

    value = float(fact_get_value(task, "corrosion_allowance"))
    unit = fact_get_unit(task, "corrosion_allowance")
    c_mm, _ = convert_to_si(value, unit, target_unit="mm")
    return float(c_mm)


@pytest.mark.parametrize("scenario_name", FIXATION_SCENARIOS)
def test_fixation_returns_expected_t_m(
    scenario_runner: ScenarioRunner,
    scenarios_dir: Path,
    scenario_name: str,
) -> None:
    scenario = load_scenario(scenarios_dir / f"{scenario_name}.yaml")
    result = scenario_runner.run(scenario)
    task = result.final.task
    assert task is not None

    t = float(task.outputs.get("t") or task.outputs["required_thickness"])
    t_m = float(task.outputs["t_m"])
    c_mm = _corrosion_allowance_mm(task)

    assert abs(t_m - (t + c_mm)) <= 1e-3
    assert float(task.outputs["minimum_required_thickness"]) == pytest.approx(t_m, abs=1e-3)
    assert abs(t - expected_wall_thickness(task)) <= 1e-3
    assert abs(t_m - expected_minimum_required_thickness(task)) <= 1e-3
