"""Policy and behavior tests for generic table-backed composer options."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from engine.reference.parameter_keys import load_parameter_node_metadata
from engine.reference.parameter_metadata import prepare_parameter_metadata
from engine.reference.table_options_resolver import (
    execute_option_query,
    load_option_query_profile,
    resolve_table_dropdown_options,
    validate_param_table_options_metadata,
)
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.helpers.goals import task_with_planning
from tests.helpers.facts import legacy_input, set_fact_from_input
from models.input import InputSource, InputStatus


def test_parameter_definitions_has_no_per_parameter_dropdown_helpers() -> None:
    source = (Path(__file__).resolve().parents[2] / "api" / "parameter_definitions.py").read_text(
        encoding="utf-8"
    )
    assert not re.search(r"def _\w+_dropdown_options\(", source)
    assert 'if parameter_id == "nominal_pipe_size"' not in source
    assert 'if parameter_id == "pipe_schedule"' not in source
    assert 'if parameter_id == "outside_diameter"' not in source
    assert 'if parameter_id == "pipe_construction_type"' not in source


def test_table_backed_params_reject_composer_options() -> None:
    table_backed = [
        "PARAM-nominal-pipe-size",
        "PARAM-pipe-schedule",
        "PARAM-outside-diameter",
        "PARAM-pipe-construction-type",
        "PARAM-material-grade",
    ]
    for node_id in table_backed:
        meta = load_parameter_node_metadata(node_id)
        assert meta is not None, node_id
        prepared = prepare_parameter_metadata(meta)
        assert prepared.get("table_options"), node_id
        assert not prepared.get("composer_options"), node_id
        assert not validate_param_table_options_metadata(meta)


def test_pressure_design_case_uses_static_composer_options_only() -> None:
    meta = load_parameter_node_metadata("PARAM-pressure-design-case")
    assert meta is not None
    prepared = prepare_parameter_metadata(meta)
    assert prepared.get("composer_options")
    assert not prepared.get("table_options")


@pytest.fixture
def standards_root(project_root: Path) -> Path:
    return project_root / "knowledge" / "standards"


def test_nps_values_profile_returns_full_table(standards_root: Path) -> None:
    profile = load_option_query_profile(
        "B3610-table-2-1",
        "nps_values",
        standards_root=standards_root,
    )
    assert profile is not None
    options = execute_option_query(
        profile,
        standards_root=standards_root,
        table_ref="B3610-table-2-1",
        facts={},
    )
    assert len(options) > 10
    assert any(item["value"] == "4" for item in options)


def test_schedules_profile_empty_until_nps_present(standards_root: Path) -> None:
    profile = load_option_query_profile(
        "B3610-table-2-1",
        "schedules_for_nps",
        standards_root=standards_root,
    )
    assert profile is not None
    assert execute_option_query(
        profile,
        standards_root=standards_root,
        table_ref="B3610-table-2-1",
        facts={},
    ) == []

    manager = TaskStateManager()
    task = manager.create_task("schedule-options", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(
        task,
        legacy_input(
            input_id="nominal_pipe_size",
            value="2",
            unit="NPS",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    options = resolve_table_dropdown_options(
        task,
        "pipe_schedule",
        standards_root=standards_root,
    )
    assert options
    assert all("Schedule" in item["label"] for item in options)


def test_b3610_yaml_compiles_option_queries(standards_root: Path) -> None:
    yaml_path = (
        standards_root / "asme" / "asme_b36.10" / "tables" / "B3610-table-2-1.yaml"
    )
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    queries = data.get("option_queries") or {}
    assert "nps_values" in queries
    assert "schedules_for_nps" in queries
    assert "nps_od_values" in queries
