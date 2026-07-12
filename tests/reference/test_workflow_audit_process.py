"""Integration tests for workflow node audit process."""

from __future__ import annotations

from pathlib import Path

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.workflow_node_validator import (
    ALLOWED_WORKFLOW_CLASSES,
    validate_workflow_node,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_audit_script_exposes_workflow_projection() -> None:
    audit_path = _project_root() / "scripts" / "audit_current_node_yaml.py"
    source = audit_path.read_text(encoding="utf-8")
    assert "render_workflow_report" in source
    assert '"workflow"' in source
    assert "validate_workflow_node" in source
    assert "workflow-node-audit.md" in source


def test_workflow_nodes_pass_contract_validator() -> None:
    workflows_dir = _project_root() / "workflows"
    for path in sorted(workflows_dir.glob("*.yaml")):
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        if meta.get("type") != "workflow":
            continue
        issues = validate_workflow_node(meta)
        assert issues == [], f"{path.name}: {issues}"


def test_workflow_validator_rejects_top_level_navigation() -> None:
    meta = {
        "id": "WF-EXAMPLE",
        "type": "workflow",
        "key": "example_workflow",
        "name": "Example",
        "workflow_class": "design_calculation",
        "description": "Example workflow",
        "navigation": {"phases": {}},
        "metadata": {
            "status": "draft",
            "last_revision": "2026-07-04",
            "edited_by": "admin",
        },
    }
    issues = validate_workflow_node(meta)
    assert any("navigation" in issue for issue in issues)


def test_allowed_workflow_classes_match_contract() -> None:
    contract_classes = {
        "design_calculation",
        "verification",
        "inspection",
        "assessment",
        "lookup",
        "selection",
        "reporting",
        "screening",
        "troubleshooting",
    }
    assert ALLOWED_WORKFLOW_CLASSES == contract_classes
