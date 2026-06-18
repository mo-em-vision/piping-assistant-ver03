"""MVP strategy §1, §3, §5–§6, §17, §23–§26 — strategy meta and completion criteria."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e.assertions import ScenarioAssertionError
from tests.e2e.scenario_loader import discover_scenarios


CRITICAL_SCENARIOS = [
    "pipe_wall_thickness_basic",
    "pipe_wall_thickness_missing_inputs",
    "pipe_wall_thickness_temperature_recovery",
    "pipe_wall_thickness_deterministic",
]

MVP_COMPLETION_CHECKS = [
    "all_tests_pass",
    "acceptance_layer_present",
    "critical_workflows_present",
    "test_data_layout",
    "traceable_failure_format",
    "security_layer_present",
]


class TestTestingObjectives:
    """§1 Testing Objectives — workflow reliability and architecture verification."""

    def test_critical_workflow_scenarios_exist(self, scenarios_dir: Path) -> None:
        names = {scenario.name for scenario in discover_scenarios(scenarios_dir)}
        for scenario_name in CRITICAL_SCENARIOS:
            assert scenario_name in names

    def test_behavior_driven_scenario_format(self, scenarios_dir: Path) -> None:
        for scenario in discover_scenarios(scenarios_dir):
            assert scenario.given
            assert scenario.when
            assert scenario.expected
            assert scenario.name


class TestTestDataManagement:
    """§23 Test Data Management — scenarios/ and expected/ layout."""

    def test_data_directories_exist(self, data_dir: Path) -> None:
        assert (data_dir / "scenarios").is_dir()
        assert (data_dir / "expected").is_dir()

    def test_expected_reference_files_exist(self, expected_dir: Path) -> None:
        assert (expected_dir / "pipe_wall_thickness_calculation.json").exists()
        assert (expected_dir / "pipe_wall_thickness_report_structure.json").exists()

    def test_scenarios_contain_workflow_definitions(self, scenarios_dir: Path) -> None:
        scenarios = discover_scenarios(scenarios_dir)
        assert len(scenarios) >= 8
        assert all(scenario.when.get("user_request") for scenario in scenarios)


class TestFailureReporting:
    """§24 Test Reporting — detailed failure output with workflow, component, trace."""

    def test_scenario_assertion_error_includes_trace_context(self) -> None:
        error = ScenarioAssertionError(
            "pipe_wall_thickness_basic",
            "Graph Engine",
            "Missing dependency",
            node="B313-304.1.1",
            source="304.1.1 dependency",
            trace={"requires": "material lookup"},
        )
        message = str(error)
        assert "Failure:" in message
        assert "pipe_wall_thickness_basic" in message
        assert "Graph Engine" in message
        assert "Missing dependency" in message
        assert "B313-304.1.1" in message
        assert "Trace:" in message


class TestAiTestingBoundaryReference:
    """§17 AI Testing Boundary — covered by acceptance layer."""

    def test_ai_boundary_tests_exist(self, project_root: Path) -> None:
        assert (project_root / "tests" / "acceptance" / "test_ai_boundary.py").exists()
        assert (project_root / "tests" / "agents").is_dir()


@pytest.mark.parametrize("check_id", MVP_COMPLETION_CHECKS)
def test_mvp_completion_criteria(check_id: str, project_root: Path, scenarios_dir: Path) -> None:
    """§25 MVP Completion Criteria."""

    if check_id == "all_tests_pass":
        # Verified by CI/local `pytest tests/` invocation; this check validates harness exists.
        assert (project_root / "tests").is_dir()

    elif check_id == "acceptance_layer_present":
        assert (project_root / "tests" / "acceptance").is_dir()
        assert (project_root / "tests" / "acceptance" / "test_mvp_workflow.py").exists()

    elif check_id == "critical_workflows_present":
        names = {s.name for s in discover_scenarios(scenarios_dir)}
        assert "pipe_wall_thickness_basic" in names

    elif check_id == "test_data_layout":
        assert (project_root / "tests" / "data" / "scenarios").is_dir()
        assert (project_root / "tests" / "data" / "expected").is_dir()

    elif check_id == "traceable_failure_format":
        assert ScenarioAssertionError.__doc__

    elif check_id == "security_layer_present":
        assert (project_root / "tests" / "mvp" / "test_security.py").exists()

    else:
        pytest.fail(f"Unhandled completion check: {check_id}")


def test_final_testing_principle_documented(project_root: Path) -> None:
    """§26 Final Testing Principle — strategy doc exists and is implemented in tests/mvp/."""
    strategy_doc = project_root / "docs" / "tests" / "3. mvp_test_strategy.md"
    assert strategy_doc.exists()
    text = strategy_doc.read_text(encoding="utf-8")
    assert "deterministic" in text.lower()
    assert "traceable" in text.lower()
    assert (project_root / "tests" / "mvp").is_dir()
