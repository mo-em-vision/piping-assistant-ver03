"""Tests for ASME B31.3 validation_rule ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.b313_legacy_aliases import build_b313_legacy_aliases
from engine.reference.standards_markdown import split_frontmatter
from engine.validation.validation_rule_node_validator import validate_validation_rule_node

_EXPECTED_VALRULE_IDS = frozenset(
    {
        "asme-b313-304-1-1-valrule-a",
        "asme-b313-304-1-2-valrule-b",
        "asme-b313-304-3-3-valrule-6a",
    }
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _validation_rule_dir() -> Path:
    return (
        _project_root()
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "validation_rule"
    )


def test_validation_rule_nodes_have_required_template_fields() -> None:
    paths = sorted(_validation_rule_dir().glob("asme-b313-*.yaml"))
    assert paths
    ids = {path.stem for path in paths}
    assert _EXPECTED_VALRULE_IDS <= ids
    for path in paths:
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "validation_rule"
        assert validate_validation_rule_node(meta) == [], path.name


def test_legacy_eq_6a_alias_resolves_to_validation_rule() -> None:
    aliases = build_b313_legacy_aliases()
    assert aliases["asme_b313_304_3_3_eq_6a"] == "asme-b313-304-3-3-valrule-6a"


def test_paragraph_304_1_1_a_references_wall_thickness_valrule() -> None:
    from engine.reference.standards_reader import StandardsReader

    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    record = reader.load("304.1.1-a")
    edge_targets = [
        e.get("target")
        for e in record.metadata.get("edges") or []
        if isinstance(e, dict) and e.get("type") == "references_validation_rule"
    ]
    assert edge_targets == ["asme-b313-304-1-1-valrule-a"]


def test_paragraph_304_1_2_b_references_thick_wall_valrule() -> None:
    from engine.reference.standards_reader import StandardsReader

    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    record = reader.load("304.1.2-b")
    edge_targets = [
        e.get("target")
        for e in record.metadata.get("edges") or []
        if isinstance(e, dict) and e.get("type") == "references_validation_rule"
    ]
    assert edge_targets == ["asme-b313-304-1-2-valrule-b"]
