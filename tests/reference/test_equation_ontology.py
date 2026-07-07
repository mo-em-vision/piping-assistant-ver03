"""Tests for ASME B31.3 equation ontology nodes."""

from __future__ import annotations

from pathlib import Path

from engine.reference.b313_legacy_aliases import build_b313_legacy_aliases
from engine.reference.standards_markdown import split_frontmatter
from engine.reference.standards_reader import StandardsReader
from engine.validation.equation_node_validator import validate_equation_node

_FORBIDDEN_FIELDS = frozenset(
    {
        "runtime_value",
        "fact_value",
        "user_input",
        "execution_id",
        "task_id",
        "calculation_result",
        "selected_for_execution",
        "active_in_context",
    }
)

_EXPECTED_EQUATION_IDS = frozenset(
    {
        "asme-b313-304-1-1-eq-2",
        "asme-b313-304-1-2-eq-3a",
        "asme-b313-304-1-2-eq-3b",
        "asme-b313-mawp-pressure",
        "asme-b313-pressure-design-thickness",
        "asme-b313-302-3-5-eq-1a",
        "asme-b313-302-3-5-eq-1b",
        "asme-b313-302-3-5-eq-1c",
        "asme-b313-304-3-3-eq-6",
        "asme-b313-304-3-3-eq-7",
        "asme-b313-304-3-3-eq-8",
    }
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _equation_dir() -> Path:
    return (
        _project_root()
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "equation"
    )


def test_equation_nodes_have_required_template_fields() -> None:
    paths = sorted(_equation_dir().glob("asme-b313-*.yaml"))
    assert len(paths) == 11
    ids = {path.stem for path in paths}
    assert ids == _EXPECTED_EQUATION_IDS
    for path in paths:
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert meta["type"] == "equation"
        assert str(meta["id"]).startswith("asme-b313-")
        assert validate_equation_node(meta) == [], path.name
        for field in _FORBIDDEN_FIELDS:
            assert field not in meta, f"{path.name} must not contain {field!r} in frontmatter"
        if "-eq-" in path.stem:
            assert meta.get("equation_number"), path.name


def test_equation_nodes_have_no_sidecar_directories() -> None:
    for path in _equation_dir().glob("asme-b313-*"):
        assert path.is_file(), f"unexpected non-file equation path: {path}"


def test_equation_rejects_parent_edge() -> None:
    meta = {
        "type": "equation",
        "id": "asme-b313-test-eq",
        "key": "asme-b313-test-eq",
        "name": "Test",
        "equation_class": "calculation",
        "description": "Test",
        "authority": {
            "authorized_by": ["304.1.2-a"],
            "authority_context_required": True,
        },
        "requires": [{"symbol": "P", "parameter": "PARAM-internal-design-gage-pressure"}],
        "metadata": {
            "status": "active",
            "last_revision": "2026-07-04",
            "edited_by": "admin",
        },
        "edges": [{"type": "parent", "target": "304.1.2-a"}],
    }
    issues = validate_equation_node(meta)
    assert any("structural edge type: parent" in issue for issue in issues)


def test_equation_nodes_expose_executor_metadata() -> None:
    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    record = reader.load("asme-b313-304-1-2-eq-3a")
    assert record.metadata.get("executor") == "calculate_wall_thickness"
    assert record.metadata.get("variables")
    assert record.metadata.get("steps")
    assert record.metadata.get("equation_number") == "3a"


def test_legacy_equation_aliases_resolve() -> None:
    aliases = build_b313_legacy_aliases()
    assert aliases["B313-eq-2"] == "asme-b313-304-1-1-eq-2"
    assert aliases["304.1.1-eq-2"] == "asme-b313-304-1-1-eq-2"
    assert aliases["B313-eq-wall-thickness"] == "asme-b313-304-1-2-eq-3a"
    assert aliases["b313-3a"] == "asme-b313-304-1-2-eq-3a"
    assert aliases["b313-3b"] == "asme-b313-304-1-2-eq-3b"
    assert aliases["asme_b313_304_1_2_wall_thickness"] == "asme-b313-304-1-2-eq-3a"
    assert aliases["B313-eq-mawp"] == "asme-b313-mawp-pressure"


def test_paragraph_references_new_equation_ids() -> None:
    pack_root = _project_root() / "knowledge" / "standards"
    reader = StandardsReader(pack_root, standard="asme_b31.3")
    record = reader.load("304.1.1-a")
    edge_targets = [
        e.get("target")
        for e in record.metadata.get("edges") or []
        if isinstance(e, dict) and e.get("type") == "references_equation"
    ]
    assert "asme-b313-304-1-1-eq-2" in edge_targets
    record_304_1_2 = reader.load("304.1.2-a")
    edge_targets_304_1_2 = [
        e.get("target")
        for e in record_304_1_2.metadata.get("edges") or []
        if isinstance(e, dict) and e.get("type") == "references_equation"
    ]
    assert edge_targets_304_1_2 == [
        "asme-b313-304-1-2-eq-3a",
        "asme-b313-304-1-2-eq-3b",
    ]
