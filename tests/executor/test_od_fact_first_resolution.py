"""Tests for fact-first outside diameter resolution in equation input binding."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from engine.executor.node_runner import NodeRunner
from engine.reference.standards_reader import StandardsReader
from models.fact import (
    FactClass,
    FactProvenance,
    FactSource,
    FactValidation,
    SourceType,
    ValidationStatus,
    build_numeric_fact,
)
from models.input import InputSource, InputStatus
from tests.helpers.facts import facts_from_inputs, legacy_input


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _od_fact(*, amount: float = 88.9, task_id: str = "od-first") -> dict:
    from engine.state.fact_migration import facts_from_legacy_inputs

    inputs = {
        "outside_diameter__resolution_branch": legacy_input(
            "outside_diameter__resolution_branch",
            "nps_lookup",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "nominal_pipe_size": legacy_input(
            "nominal_pipe_size",
            "3",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }
    store = facts_from_legacy_inputs(inputs, task_id=task_id)
    od = build_numeric_fact(
        key="outside_diameter",
        parameter="outside_diameter",
        amount=amount,
        unit="mm",
        fact_class=FactClass.LOOKED_UP,
        source=FactSource(
            source_type=SourceType.TABLE_LOOKUP,
            source_id="B3610-table-2-1:by_nps",
            lookup_node="asme-b3610-nps-outside-diameter-lookup",
        ),
        provenance=FactProvenance(task_id=task_id, created_by="lookup"),
        validation_status=ValidationStatus.CONFIRMED,
    )
    store.upsert_active(od)
    return store.active_facts()


def test_resolve_outside_diameter_prefers_existing_fact_over_table_lookup() -> None:
    reader = _reader()
    runner = NodeRunner(reader)
    task_inputs = _od_fact(amount=88.9)
    record = reader.load("304.1.2-a")

    with patch.object(runner._lookup_engine, "execute_rule_lookup") as mocked:
        missing_key = runner._resolve_outside_diameter(
            record,
            task_inputs=task_inputs,
            resolved={},
            missing=[],
            nomenclature={},
        )
        mocked.assert_not_called()

    assert missing_key is None


def test_resolve_outside_diameter_uses_graph_metadata_when_fact_missing() -> None:
    reader = _reader()
    runner = NodeRunner(reader)
    task_inputs = facts_from_inputs(
        {
            "outside_diameter__resolution_branch": legacy_input(
                "outside_diameter__resolution_branch",
                "nps_lookup",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "nominal_pipe_size": legacy_input(
                "nominal_pipe_size",
                "2",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="od-graph-meta",
    )
    record = reader.load("304.1.2-a")
    resolved: dict = {}
    missing_key = runner._resolve_outside_diameter(
        record,
        task_inputs=task_inputs,
        resolved=resolved,
        missing=[],
        nomenclature={},
    )
    assert missing_key is None
    assert resolved["D"] == pytest.approx(60.33, rel=1e-3)
    assert resolved.get("D_unit") == "mm"
