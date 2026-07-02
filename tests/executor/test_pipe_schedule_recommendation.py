"""Tests for pipe schedule recommendation from calculated t_m."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.pipe_schedule_recommendation import (
    format_schedule_recommendation_text,
    recommend_pipe_schedule,
    resolve_task_nps,
)
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus


def test_recommend_next_schedule_for_nps_2(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    recommendation = recommend_pipe_schedule(
        nps="2",
        minimum_required_thickness_mm=2.752,
        standards_root=standards_root,
    )
    assert recommendation is not None
    assert recommendation.schedule == "10"
    assert recommendation.wall_thickness_mm == pytest.approx(2.769, abs=0.001)
    assert recommendation.standard_display == "ASME B36.10M"


def test_recommend_schedule_40_when_between_schedules(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    recommendation = recommend_pipe_schedule(
        nps="2",
        minimum_required_thickness_mm=3.0,
        standards_root=standards_root,
    )
    assert recommendation is not None
    assert recommendation.schedule == "20"
    assert recommendation.wall_thickness_mm == pytest.approx(3.175, abs=0.001)


def test_recommend_schedule_prefers_numeric_alias(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    recommendation = recommend_pipe_schedule(
        nps="2",
        minimum_required_thickness_mm=3.2,
        standards_root=standards_root,
    )
    assert recommendation is not None
    assert recommendation.schedule == "40"
    assert recommendation.schedule != "STD"


def test_format_schedule_recommendation_text(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    recommendation = recommend_pipe_schedule(
        nps="2",
        minimum_required_thickness_mm=0.13,
        standards_root=standards_root,
    )
    assert recommendation is not None
    text = format_schedule_recommendation_text(recommendation)
    assert "Select Schedule" in text
    assert "NPS 2" in text
    assert "ASME B36.10M" in text
    assert "t_m" in text


def test_resolve_task_nps_from_nominal_pipe_size(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("schedule-nps-from-input", status=TaskStatus.COMPLETED)
    set_fact_from_input(task, legacy_input(input_id="nominal_pipe_size",
        value="4",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    assert resolve_task_nps(task, standards_root) == "4"


def test_resolve_task_nps_from_outside_diameter_lookup(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("schedule-nps-from-lookup", status=TaskStatus.COMPLETED)
    task.outputs["outside_diameter_lookup"] = {
        "nps": "6",
        "outside_diameter_mm": 168.275,
    }
    assert resolve_task_nps(task, standards_root) == "6"


def test_resolve_task_nps_from_matching_outside_diameter(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("schedule-nps-from-od", status=TaskStatus.COMPLETED)
    set_fact_from_input(task, legacy_input(input_id="outside_diameter",
        value=168.275,
        unit="mm",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    assert resolve_task_nps(task, standards_root) == "6"


def test_no_recommendation_when_thickness_exceeds_all_schedules(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    recommendation = recommend_pipe_schedule(
        nps="1/8",
        minimum_required_thickness_mm=10.0,
        standards_root=standards_root,
    )
    assert recommendation is None
