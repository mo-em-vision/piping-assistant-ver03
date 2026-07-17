"""Tests for engine-owned equation source-node provenance resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from api import equation_display_registry as api_equation_display_registry
from api.display_block_metadata import equation_trace_semantic_key
from engine.graph import equation_source as engine_equation_source
from engine.graph.equation_source import source_node_id_for_equation
from engine.reference.standards_reader import NodeRecord, StandardsReader

EQ_3A_ID = "asme-b313-304-1-2-eq-3a"
EQ_2_ID = "asme-b313-304-1-1-eq-2"
WORKFLOW_ID = "pipe_wall_thickness_design"


@dataclass(frozen=True)
class _StubReader:
    records: dict[str, NodeRecord]

    def load(self, node_id: str) -> NodeRecord:
        if node_id not in self.records:
            raise FileNotFoundError(node_id)
        return self.records[node_id]


def _record(node_id: str, metadata: dict[str, Any]) -> NodeRecord:
    return NodeRecord(
        node_id=node_id,
        path=Path(f"/stub/{node_id}.yaml"),
        metadata=metadata,
        body="",
    )


def test_authorized_owner_precedence_over_paragraph_number() -> None:
    reader = _StubReader(
        {
            "eq-precedence": _record(
                "eq-precedence",
                {
                    "authority": {"authorized_by": ["304.1.2-a"]},
                    "paragraph_number": "304.1.2",
                },
            )
        }
    )
    assert source_node_id_for_equation(reader, "eq-precedence") == "304.1.2-a"


def test_paragraph_fallback_when_authorized_by_absent() -> None:
    reader = _StubReader(
        {
            "eq-paragraph": _record(
                "eq-paragraph",
                {"paragraph_number": "304.1.2"},
            )
        }
    )
    assert source_node_id_for_equation(reader, "eq-paragraph") == "304.1.2"


def test_paragraph_fallback_when_authorized_by_empty() -> None:
    reader = _StubReader(
        {
            "eq-empty-auth": _record(
                "eq-empty-auth",
                {
                    "authority": {"authorized_by": []},
                    "paragraph_number": "304.1.1-a",
                },
            )
        }
    )
    assert source_node_id_for_equation(reader, "eq-empty-auth") == "304.1.1-a"


def test_node_id_fallback_when_ownership_fields_absent() -> None:
    reader = _StubReader(
        {
            "eq-standalone": _record("eq-standalone", {"type": "equation"}),
        }
    )
    assert source_node_id_for_equation(reader, "eq-standalone") == "eq-standalone"


def test_missing_node_returns_supplied_equation_node_id() -> None:
    reader = _StubReader({})
    assert source_node_id_for_equation(reader, "missing-eq-id") == "missing-eq-id"


def test_empty_authorized_value_falls_through_to_paragraph() -> None:
    reader = _StubReader(
        {
            "eq-whitespace-auth": _record(
                "eq-whitespace-auth",
                {
                    "authority": {"authorized_by": ["   "]},
                    "paragraph_number": "304.1.2-a",
                },
            )
        }
    )
    assert source_node_id_for_equation(reader, "eq-whitespace-auth") == "304.1.2-a"


def test_api_reexport_is_same_function_object() -> None:
    assert api_equation_display_registry.source_node_id_for_equation is engine_equation_source.source_node_id_for_equation


@pytest.mark.parametrize(
    ("equation_node_id", "expected_source"),
    [
        (EQ_3A_ID, "304.1.2-a"),
        (EQ_2_ID, "304.1.1-a"),
    ],
)
def test_real_b313_equation_source_mappings(
    standards_reader: StandardsReader,
    equation_node_id: str,
    expected_source: str,
) -> None:
    engine_result = source_node_id_for_equation(standards_reader, equation_node_id)
    api_result = api_equation_display_registry.source_node_id_for_equation(
        standards_reader,
        equation_node_id,
    )
    assert engine_result == expected_source
    assert api_result == expected_source


def test_semantic_registry_key_unchanged_for_eq2(standards_reader: StandardsReader) -> None:
    source = source_node_id_for_equation(standards_reader, EQ_2_ID)
    key = equation_trace_semantic_key(
        workflow_id=WORKFLOW_ID,
        source_node_id=source,
        equation_node_id=EQ_2_ID,
    )
    assert key == f"{WORKFLOW_ID}|304.1.1-a|{EQ_2_ID}|equation"


def test_execution_trace_node_id_matches_source_resolution(standards_reader: StandardsReader) -> None:
    from engine.equation.equation_display_trace_builder import build_equation_display_trace

    eq_record = standards_reader.load(EQ_3A_ID)
    source = source_node_id_for_equation(standards_reader, EQ_3A_ID)
    trace = build_equation_display_trace(
        reader=standards_reader,
        equation_id=EQ_3A_ID,
        equation_metadata=eq_record.metadata,
        symbol_values={},
        source_node_id=source,
    )
    assert trace.equation_id == EQ_3A_ID
    assert trace.node_id == "304.1.2-a"


def test_display_block_source_fields_unchanged(standards_reader: StandardsReader) -> None:
    from api.display_block_metadata import equation_display_block_id, tag_equation_block

    source = source_node_id_for_equation(standards_reader, EQ_2_ID)
    block = tag_equation_block(
        {
            "type": "equation",
            "id": equation_display_block_id(EQ_2_ID),
            "content": "t_m = t + c",
        },
        display_state="preview",
        equation_node_id=EQ_2_ID,
        source_node_id=source,
    )
    assert block["id"] == f"equation-{EQ_2_ID}"
    assert block["equation_node_id"] == EQ_2_ID
    assert block["source_node_id"] == "304.1.1-a"
