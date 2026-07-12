"""Integration tests for validation rule node audit process."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.validation_rule_node_validator import validate_validation_rule_node


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


def test_audit_script_exposes_validation_rule_projection() -> None:
    audit_path = _project_root() / "scripts" / "audit_current_node_yaml.py"
    source = audit_path.read_text(encoding="utf-8")
    assert "render_validation_rule_report" in source
    assert '"validation_rule"' in source
    assert "validate_validation_rule_node" in source
    assert "validation-rule-node-audit.md" in source


def test_validation_rule_nodes_pass_contract_validator() -> None:
    for path in sorted(_validation_rule_dir().glob("asme-b313-*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        issues = validate_validation_rule_node(meta)
        assert issues == [], f"{path.name}: {issues}"


def test_validation_rule_validator_rejects_calculates_parameter_edge() -> None:
    meta = {
        "id": "asme-b313-example-valrule",
        "type": "validation_rule",
        "key": "asme-b313-example-valrule",
        "name": "Example",
        "description": "Example validation rule",
        "rule_class": "validation",
        "authority": {
            "authorized_by": ["304.1.2-a"],
            "authority_context_required": True,
        },
        "validates": [{"parameter": "PARAM-thin-wall-applicability"}],
        "edges": [{"type": "calculates_parameter", "target": "PARAM-thin-wall-applicability"}],
        "metadata": {
            "status": "active",
            "last_revision": "2026-07-04",
            "edited_by": "admin",
        },
    }
    issues = validate_validation_rule_node(meta)
    assert any("calculates_parameter" in issue for issue in issues)


def test_validation_rule_validator_requires_validates_or_edge() -> None:
    meta = {
        "id": "asme-b313-example-valrule",
        "type": "validation_rule",
        "key": "asme-b313-example-valrule",
        "name": "Example",
        "description": "Example validation rule",
        "authority": {
            "authorized_by": ["304.1.2-a"],
            "authority_context_required": True,
        },
        "metadata": {
            "status": "active",
            "last_revision": "2026-07-04",
            "edited_by": "admin",
        },
    }
    issues = validate_validation_rule_node(meta)
    assert any("validates" in issue for issue in issues)
