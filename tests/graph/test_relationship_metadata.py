"""Tests for canonical graph edge schema compilation."""

from __future__ import annotations

from engine.reference.graph_compile import compile_metadata_edges


def test_requires_edge_preserves_relationship_metadata() -> None:
    edges = compile_metadata_edges(
        "equation_pipe_thickness",
        {
            "type": "equation",
            "edges": [
                {
                    "type": "requires_parameter",
                    "target": "quantity_pressure",
                    "alias": "P",
                    "role": "Internal Pressure",
                }
            ],
        },
    )

    assert edges == [
        (
            "equation_pipe_thickness",
            "quantity_pressure",
            "requires_parameter",
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
            "type": "equation",
            "edges": [
                {
                    "target": "quantity_pressure",
                    "type": "requires_parameter",
                    "alias": "Pe",
                    "role": "External Pressure",
                    "when": {"field": "pressure_design_case", "in": ["external_pressure"]},
                }
            ],
        },
    )

    assert edges == [
        (
            "equation_external_pressure",
            "quantity_pressure",
            "requires_parameter",
            {
                "alias": "Pe",
                "role": "External Pressure",
                "when": {"field": "pressure_design_case", "in": ["external_pressure"]},
            },
        )
    ]


def test_duplicate_requires_to_same_concept_keep_distinct_aliases() -> None:
    edges = compile_metadata_edges(
        "equation_eq_2",
        {
            "edges": [
                {"type": "requires_parameter", "target": "quantity_thickness", "alias": "t"},
                {"type": "requires_parameter", "target": "quantity_thickness", "alias": "c"},
            ],
        },
    )

    assert len(edges) == 2
    aliases = sorted((edge[3] or {}).get("alias") for edge in edges)
    assert aliases == ["c", "t"]


def test_depends_on_lettered_paragraph_target_has_no_subsection_metadata() -> None:
    edges = compile_metadata_edges(
        "asme-b313-table-302-3-5-1",
        {
            "edges": [{"type": "depends_on", "target": "302.3.5-e"}],
        },
    )

    assert edges == [
        (
            "asme-b313-table-302-3-5-1",
            "302.3.5-e",
            "depends_on",
            None,
        )
    ]
