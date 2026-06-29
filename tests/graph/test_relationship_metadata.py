"""Relationship metadata compilation tests."""

from __future__ import annotations

from engine.reference.graph_compile import compile_metadata_edges


def test_requires_edge_preserves_relationship_metadata() -> None:
    edges = compile_metadata_edges(
        "equation_pipe_thickness",
        {
            "requires": [
                {
                    "node_id": "quantity_pressure",
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
                "displayName": "Design pressure",
                "required": True,
                "defaultValue": 0,
                "validation": {"min": 0},
                "priority": 10,
            },
        )
    ]


def test_explicit_edge_preserves_metadata_without_routing_fields() -> None:
    edges = compile_metadata_edges(
        "equation_external_pressure",
        {
            "edges": [
                {
                    "to": "quantity_pressure",
                    "type": "requires",
                    "direction": "outgoing",
                    "alias": "Pe",
                    "role": "External Pressure",
                    "required": False,
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
                "required": False,
                "when": {"field": "pressure_loading", "in": ["external_pressure"]},
            },
        )
    ]


def test_duplicate_requires_to_same_concept_keep_distinct_aliases() -> None:
    edges = compile_metadata_edges(
        "equation_eq_2",
        {
            "requires": [
                {
                    "node_id": "quantity_thickness",
                    "alias": "t",
                    "priority": 85,
                },
                {
                    "node_id": "quantity_thickness",
                    "alias": "c",
                    "priority": 90,
                },
            ],
        },
    )

    assert len(edges) == 2
    aliases = sorted((edge[3] or {}).get("alias") for edge in edges)
    assert aliases == ["c", "t"]
    edges = compile_metadata_edges(
        "equation_pipe_thickness",
        {"requires": [{"node_id": "quantity_pressure", "when": "sometimes"}]},
    )

    assert edges == [("equation_pipe_thickness", "quantity_pressure", "requires", None)]
