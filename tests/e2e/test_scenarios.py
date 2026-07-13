"""Parametrized end-to-end scenarios from tests/data/scenarios/."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.scenario_loader import Scenario, discover_scenarios, load_scenario
from tests.e2e.scenario_runner import ScenarioRunner


@pytest.mark.parametrize(
    "scenario_path",
    sorted(Path(__file__).resolve().parents[1].joinpath("data", "scenarios").glob("*.yaml")),
    ids=lambda path: path.stem,
)
def test_e2e_scenario(scenario_path: Path, scenario_runner: ScenarioRunner) -> None:
    scenario = load_scenario(scenario_path)
    scenario_runner.run(scenario)


def test_all_scenarios_discovered(scenarios_dir: Path) -> None:
    scenarios = discover_scenarios(scenarios_dir)
    assert len(scenarios) >= 2
    names = {scenario.name for scenario in scenarios}
    assert "pipe_wall_thickness_missing_inputs" in names
    assert "pipe_wall_thickness_invalid_pressure" in names
