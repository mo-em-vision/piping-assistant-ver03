"""Integration tests for authority node audit process."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.authority_node_validator import (
    ALLOWED_AUTHORITY_CLASSES,
    validate_authority_node,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_audit_script_exposes_authority_projection() -> None:
    audit_path = _project_root() / "scripts" / "audit_current_node_yaml.py"
    source = audit_path.read_text(encoding="utf-8")
    assert "render_authority_report" in source
    assert '"authority"' in source
    assert "validate_authority_node" in source
    assert "authority-node-audit.md" in source


def test_authority_nodes_pass_contract_validator() -> None:
    authorities_dir = _project_root() / "knowledge" / "global" / "authorities" / "nodes"
    for path in sorted(authorities_dir.glob("AUTH-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        issues = validate_authority_node(meta)
        assert issues == [], f"{path.name}: {issues}"


def test_authority_validator_rejects_non_auth_id() -> None:
    meta = {
        "id": "ASME-B31.3",
        "type": "authority",
        "key": "asme_b31_3",
        "name": "ASME B31.3",
        "authority_class": "design_code",
        "description": "Example",
        "metadata": {"last_revision": "2026-07-04", "edited_by": "admin"},
    }
    issues = validate_authority_node(meta)
    assert any("AUTH-" in issue for issue in issues)


def test_allowed_authority_classes_match_contract() -> None:
    contract_classes = {
        "design_code",
        "inspection_code",
        "material_standard",
        "dimensional_standard",
        "testing_standard",
        "regulation",
        "company_standard",
        "project_specification",
        "client_requirement",
        "reference_standard",
        "recommended_practice",
        "engineering_procedure",
        "manufacturer_document",
    }
    assert ALLOWED_AUTHORITY_CLASSES == contract_classes
