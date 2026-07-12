"""Integration tests for designation node audit process."""

from __future__ import annotations

from pathlib import Path

from engine.validation.designation_node_validator import validate_designation_node


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_audit_script_exposes_designation_projection() -> None:
    audit_path = _project_root() / "scripts" / "audit_current_node_yaml.py"
    source = audit_path.read_text(encoding="utf-8")
    assert "render_designation_report" in source
    assert '"designation"' in source
    assert "validate_designation_node" in source
    assert "designation-node-audit.md" in source


def test_designation_validator_accepts_minimal_skeleton() -> None:
    meta = {
        "id": "B313-designation-nps",
        "type": "designation",
        "name": "Nominal Pipe Size",
        "symbol": "NPS",
        "metadata": {"last_revision": "2026-07-04", "edited_by": "admin"},
    }
    assert validate_designation_node(meta) == []


def test_designation_validator_rejects_runtime_and_dimension_fields() -> None:
    meta = {
        "id": "designation_nps",
        "type": "designation",
        "name": "Nominal Pipe Size",
        "symbol": "NPS",
        "dimension": "length",
        "value": "4",
        "metadata": {"last_revision": "2026-07-04", "edited_by": "admin"},
    }
    issues = validate_designation_node(meta)
    assert any("dimension" in issue for issue in issues)
    assert any("value" in issue for issue in issues)


def test_designation_validator_requires_symbol() -> None:
    meta = {
        "id": "B313-designation-nps",
        "type": "designation",
        "name": "Nominal Pipe Size",
        "metadata": {"last_revision": "2026-07-04", "edited_by": "admin"},
    }
    issues = validate_designation_node(meta)
    assert any("symbol" in issue for issue in issues)
