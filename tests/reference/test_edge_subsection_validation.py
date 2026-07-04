"""Edge validation: redundant subsection metadata on paragraph targets."""

from __future__ import annotations

from engine.reference.relationship_validator import validate_edge_item


def test_rejects_subsection_on_lettered_paragraph_target() -> None:
    issues = validate_edge_item(
        {
            "type": "depends_on",
            "target": "302.3.5-e",
            "subsection": "e",
        },
        source_node_type="lookup",
    )
    assert any("redundant" in issue for issue in issues)


def test_rejects_parent_target_plus_subsection() -> None:
    issues = validate_edge_item(
        {
            "type": "depends_on",
            "target": "302.3.3-a",
            "subsection": "b",
        },
        source_node_type="lookup",
    )
    assert any("302.3.3-b" in issue for issue in issues)


def test_accepts_lettered_paragraph_target_without_subsection() -> None:
    issues = validate_edge_item(
        {
            "type": "depends_on",
            "target": "302.3.5-e",
        },
        source_node_type="lookup",
    )
    assert not any("subsection" in issue for issue in issues)
