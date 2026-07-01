"""Tests for canonical graph edge schema compilation."""

from __future__ import annotations

from engine.reference.graph_compile import compile_metadata_edges


def test_requires_edge_preserves_relationship_metadata() -> None:
    edges = compile_metadata_edges(
        "equation_pipe_thickness",
        {
            "edges": [
                {
                    "type": "requires",
                    "target": "quantity_pressure",
                    "alias": "P",
                    "role": "Internal Pressure",
                    "displayName": "Design pressure",
                    "required": True,
                    "defaultValue": 0,
                    "validation": {"min": 0},
                    "priority": 10,
                }
            ],
        },
    )

    assert edges == [
        (
            "equation_pipe_thickness",
            "quantity_pressure",
            "requires",
            {
                "alias": "P",
                "role": "Internal Pressure",
            },
        )
    ]


def test_explicit_edge_preserves_metadata_without_routing_fields() -> None:
    edges = compile_metadata_edges(
        "equation_external_pressure",
        {
            "edges": [
                {
                    "target": "quantity_pressure",
                    "type": "requires",
                    "alias": "Pe",
                    "role": "External Pressure",
                    "when": {"field": "pressure_loading", "in": ["external_pressure"]},
                }
            ],
        },
    )

    assert edges == [
        (
            "equation_external_pressure",
            "quantity_pressure",
            "requires",
            {
                "alias": "Pe",
                "role": "External Pressure",
                "when": {"field": "pressure_loading", "in": ["external_pressure"]},
            },
        )
    ]


def test_duplicate_requires_to_same_concept_keep_distinct_aliases() -> None:
    edges = compile_metadata_edges(
        "equation_eq_2",
        {
            "edges": [
                {"type": "requires", "target": "quantity_thickness", "alias": "t", "priority": 85},
                {"type": "requires", "target": "quantity_thickness", "alias": "c", "priority": 90},
            ],
        },
    )

    assert len(edges) == 2
    aliases = sorted((edge[3] or {}).get("alias") for edge in edges)
    assert aliases == ["c", "t"]


def test_depends_on_subsection_target_suffix() -> None:
    edges = compile_metadata_edges(
        "B313-table-302-3-5-1",
        {
            "edges": [{"type": "depends_on", "target": "302.3.5/e"}],
        },
    )

    assert edges == [
        (
            "B313-table-302-3-5-1",
            "302.3.5",
            "depends_on",
            {"subsection": "e"},
        )
    ]
