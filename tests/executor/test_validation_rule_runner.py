"""Tests for generic validation_rule execution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.node_runner import NodeRunner
from engine.executor.validation_rule_contract import assess_validation_rule_support
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.execution import NodeExecutionStatus
from models.task import TaskStatus
from tests.helpers.facts import set_fact

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def reader() -> StandardsReader:
    return StandardsReader(PROJECT_ROOT / "knowledge" / "standards", standard="asme_b31.3")


def test_thin_wall_valrule_supported_by_contract(reader: StandardsReader) -> None:
    meta = reader.load("asme-b313-304-1-2-valrule-a").metadata
    support = assess_validation_rule_support(meta, reader=reader)
    assert support.supported is True


def test_reinforcement_valrule_skipped_when_result_param_missing(reader: StandardsReader) -> None:
    meta = reader.load("asme-b313-304-3-3-valrule-6a").metadata
    support = assess_validation_rule_support(meta, reader=reader)
    assert support.supported is False
    assert "result parameter not found" in support.reason


def test_wall_thickness_valrule_skipped_when_result_param_missing(reader: StandardsReader) -> None:
    meta = reader.load("asme-b313-304-1-1-valrule-a").metadata
    support = assess_validation_rule_support(meta, reader=reader)
    assert support.supported is False
    assert "result parameter not found" in support.reason


def test_thick_wall_valrule_skipped_when_result_param_missing(reader: StandardsReader) -> None:
    meta = reader.load("asme-b313-304-1-2-valrule-b").metadata
    support = assess_validation_rule_support(meta, reader=reader)
    assert support.supported is False
    assert "result parameter not found" in support.reason


def test_thin_wall_valrule_passes_when_t_less_than_d_over_six(reader: StandardsReader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("valrule-pass", status=TaskStatus.AWAITING_INPUT)
    set_fact(task, "required_wall_thickness", 5.0, unit="mm")
    set_fact(task, "outside_diameter", 60.0, unit="mm")

    runner = NodeRunner(reader)
    result = runner.run(
        "asme-b313-304-1-2-valrule-a",
        task_inputs=task.fact_store.active_facts(),
        dependency_outputs={},
        task=task,
    )

    assert result.status == NodeExecutionStatus.COMPLETED
    assert result.trace["passed"] is True
    assert result.outputs["thin_wall_applicable"] is True
    fact = task.fact_store.active_fact("thin_wall_applicability")
    assert fact is not None
    assert fact.value.label == "true"
    assert fact.provenance.produced_by_node == "asme-b313-304-1-2-valrule-a"
    assert fact.provenance.created_by == "validation_rule"
    assert fact.source.source_id == "asme-b313-304-1-2-valrule-a"


def test_thin_wall_valrule_warns_when_t_exceeds_limit(reader: StandardsReader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("valrule-fail", status=TaskStatus.AWAITING_INPUT)
    set_fact(task, "required_wall_thickness", 12.0, unit="mm")
    set_fact(task, "outside_diameter", 60.0, unit="mm")

    runner = NodeRunner(reader)
    result = runner.run(
        "asme-b313-304-1-2-valrule-a",
        task_inputs=task.fact_store.active_facts(),
        dependency_outputs={},
        task=task,
    )

    assert result.status == NodeExecutionStatus.COMPLETED
    assert result.trace["passed"] is False
    assert result.outputs["thin_wall_applicable"] is False
    assert result.warnings
    assert "t < D/6" in result.warnings[0]
    fact = task.fact_store.active_fact("thin_wall_applicability")
    assert fact is not None
    assert fact.value.label == "false"


def test_unsupported_valrule_returns_skip_with_reason(reader: StandardsReader) -> None:
    runner = NodeRunner(reader)
    result = runner.run(
        "asme-b313-304-3-3-valrule-6a",
        task_inputs={},
        dependency_outputs={},
    )

    assert result.status == NodeExecutionStatus.SKIPPED
    assert result.trace["contract"] == "validation_rule"
    assert "result parameter not found" in result.trace["reason"]
