"""Integration tests for concept node audit process."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.concept_node_validator import validate_concept_node


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_audit_script_exposes_concept_projection() -> None:
    audit_path = _project_root() / "scripts" / "audit_current_node_yaml.py"
    source = audit_path.read_text(encoding="utf-8")
    assert "render_concept_report" in source
    assert '"concept"' in source
    assert "validate_concept_node" in source
    assert "concept-node-audit.md" in source


def test_concept_nodes_pass_contract_validator() -> None:
    concepts_dir = _project_root() / "knowledge" / "global" / "concepts" / "nodes"
    dims_dir = _project_root() / "knowledge" / "global" / "dimensions" / "nodes"
    known_dimension_ids = {path.stem for path in dims_dir.glob("DIM-*.yaml")}

    for path in sorted(concepts_dir.glob("CONCEPT-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        issues = validate_concept_node(meta, known_dimension_ids=known_dimension_ids)
        assert issues == [], f"{path.name}: {issues}"
