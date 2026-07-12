"""Synthetic fixtures for one-primary-YAML-per-node authoring policy."""

from __future__ import annotations

import pytest

from engine.reference.node_block_extractor import extract_and_flatten_node_metadata
from engine.reference.paragraph_authoring_policy import (
    check_paragraph_frontmatter_placement,
)
from engine.reference.workflow_authoring_policy import check_workflow_frontmatter_placement
from engine.validation.paragraph_node_validator import validate_paragraph_node
from engine.validation.workflow_node_validator import validate_workflow_node


def _paragraph_fixture() -> dict:
    return {
        "id": "304.9.9-a",
        "type": "paragraph",
        "key": "b313_304_9_9_a",
        "title": "Fixture Paragraph",
        "authority": "AUTH-ASME-B31.3",
        "edition": "2024",
        "paragraph_number": "304.9.9-a",
        "text": {"original": "Fixture paragraph text."},
        "hierarchy": {"parent": "304.9", "children": []},
        "metadata": {
            "source_revision_year": 2024,
            "last_revision": "2026-07-12",
            "edited_by": "test",
        },
        "execution": {
            "applicability": {
                "applies_when": [
                    {
                        "parameter": "PARAM-pressure-loading",
                        "operator": "equals",
                        "value": "internal_pressure",
                    }
                ]
            },
            "assumptions": [
                {
                    "id": "straight_pipe_section",
                    "field": "straight_pipe_section",
                    "required_for_expansion": True,
                }
            ],
        },
    }


def test_paragraph_nested_execution_passes_validator() -> None:
    meta = _paragraph_fixture()
    assert not validate_paragraph_node(meta)
    assert not check_paragraph_frontmatter_placement(meta)


def test_paragraph_runtime_state_fails() -> None:
    meta = _paragraph_fixture()
    meta["runtime_value"] = 1.0
    assert any("runtime_value" in issue for issue in validate_paragraph_node(meta))


def test_paragraph_top_level_applicability_fails() -> None:
    meta = _paragraph_fixture()
    del meta["execution"]
    meta["applicability"] = {"applies_when": []}
    findings = check_paragraph_frontmatter_placement(meta)
    assert any("applicability" in msg for _, msg in findings)


def test_extract_paragraph_execution_flattens() -> None:
    flat = extract_and_flatten_node_metadata(_paragraph_fixture(), "paragraph")
    assert flat.get("applicability")
    assert flat.get("assumptions")
    assert "execution" not in flat


def test_workflow_nested_runtime_passes() -> None:
    meta = {
        "id": "WF-FIXTURE",
        "type": "workflow",
        "key": "fixture_workflow",
        "name": "Fixture Workflow",
        "workflow_class": "design_calculation",
        "description": "Fixture workflow for policy tests.",
        "metadata": {
            "status": "draft",
            "last_revision": "2026-07-12",
            "edited_by": "test",
        },
        "runtime": {
            "navigation": {
                "assumption_gate_fields": ["straight_pipe_section"],
                "phases": {"expansion_assumptions": ["straight_pipe_section"]},
            },
            "interactions": [
                {
                    "variable": "pressure_loading",
                    "mode": "decision",
                    "required": True,
                    "options": ["internal_pressure"],
                }
            ],
        },
    }
    assert not validate_workflow_node(meta)
    assert not check_workflow_frontmatter_placement(meta)


def test_workflow_top_level_navigation_fails() -> None:
    meta = {
        "id": "WF-FIXTURE",
        "type": "workflow",
        "key": "fixture_workflow",
        "name": "Fixture Workflow",
        "workflow_class": "design_calculation",
        "description": "Fixture workflow for policy tests.",
        "metadata": {
            "status": "draft",
            "last_revision": "2026-07-12",
            "edited_by": "test",
        },
        "navigation": {"phases": {}},
    }
    findings = check_workflow_frontmatter_placement(meta)
    assert any("navigation" in msg for _, msg in findings)


@pytest.mark.parametrize(
    "node_type",
    [
        "paragraph",
        "parameter",
        "equation",
        "lookup",
        "validation_rule",
        "workflow",
        "unit",
        "authority",
        "concept",
        "dimension",
        "text",
    ],
)
def test_runtime_state_fails_for_canonical_types(node_type: str) -> None:
    meta = {"id": f"FIXTURE-{node_type}", "type": node_type, "runtime_value": 1}
    findings = check_paragraph_frontmatter_placement(meta) if node_type == "paragraph" else []
    if node_type == "paragraph":
        assert any("runtime_value" in msg for _, msg in findings)
