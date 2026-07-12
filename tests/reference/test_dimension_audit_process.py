"""Integration tests for dimension node audit process."""

from __future__ import annotations

from pathlib import Path

from engine.validation.dimension_node_validator import validate_dimension_node


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_audit_script_exposes_dimension_projection() -> None:
    audit_path = _project_root() / "scripts" / "audit_current_node_yaml.py"
    source = audit_path.read_text(encoding="utf-8")
    assert "render_dimension_report" in source
    assert '"dimension"' in source
    assert "validate_dimension_node" in source
    assert "dimension-node-audit.md" in source


def test_dimension_nodes_pass_contract_validator() -> None:
    dims_dir = _project_root() / "knowledge" / "global" / "dimensions" / "nodes"
    units_dir = _project_root() / "knowledge" / "global" / "units" / "nodes"
    unit_ids = {path.stem for path in units_dir.glob("UNIT-*.yaml")}
    from engine.reference.standards_markdown import split_frontmatter

    for path in sorted(dims_dir.glob("DIM-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        issues = validate_dimension_node(meta, known_unit_ids=unit_ids)
        assert issues == [], f"{path.name}: {issues}"
