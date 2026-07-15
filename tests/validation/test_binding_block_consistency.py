"""Tests for raw-YAML binding block vs edge consistency."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.binding_block_consistency import validate_binding_block_consistency
from engine.validation.equation_node_validator import validate_equation_node


def test_consistent_equation_has_no_binding_issues() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "equation"
        / "asme-b313-304-1-2-eq-3a.yaml"
    )
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert validate_binding_block_consistency(meta) == []


def test_drifted_requires_block_reports_missing_edge() -> None:
    meta = {
        "type": "equation",
        "requires": [{"parameter": "PARAM-outside-diameter", "symbol": "D"}],
        "edges": [],
    }
    issues = validate_binding_block_consistency(meta)
    assert any("requires lists PARAM-outside-diameter" in item for item in issues)


def test_drifted_edge_reports_missing_block() -> None:
    meta = {
        "type": "equation",
        "requires": [],
        "edges": [{"type": "requires_parameter", "target": "PARAM-outside-diameter"}],
    }
    issues = validate_binding_block_consistency(meta)
    assert any("requires_parameter edge targets PARAM-outside-diameter" in item for item in issues)


def test_valrule_result_must_match_validates_parameter_edge() -> None:
    meta = {
        "type": "validation_rule",
        "result": {"parameter": "PARAM-thin-wall-applicability"},
        "edges": [],
    }
    issues = validate_binding_block_consistency(meta)
    assert any("result.parameter PARAM-thin-wall-applicability has no validates_parameter edge" in item for item in issues)


def test_equation_node_validator_includes_binding_consistency() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "equation"
        / "asme-b313-304-1-2-eq-3a.yaml"
    )
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    drifted = dict(meta)
    drifted["requires"] = list(meta.get("requires") or []) + [
        {"parameter": "PARAM-corrosion-allowance", "symbol": "c"},
    ]
    issues = validate_equation_node(drifted)
    assert any("requires lists PARAM-corrosion-allowance" in item for item in issues)
