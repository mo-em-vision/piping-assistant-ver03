"""Integration and consistency tests for paragraph audit process."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from engine.reference.paragraph_authoring_policy import (
    EXECUTION_SIDECAR_KEYS,
    FORBIDDEN_PARAGRAPH_FRONTMATTER,
    FORBIDDEN_RUNTIME_STATE_KEYS,
    SIDECAR_ONLY_ENFORCEMENT,
    SIDECAR_ONLY_KEYS,
    check_paragraph_frontmatter_placement,
    classify_edge_target,
    validator_fail_messages_for_frontmatter,
)
from engine.reference.paragraph_sidecar import merge_paragraph_sidecar_metadata
from engine.reference.standards_markdown import split_frontmatter
from engine.validation.paragraph_node_validator import validate_paragraph_node


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _paragraph_dir() -> Path:
    return (
        _project_root()
        / "knowledge"
        / "standards"
        / "asme"
        / "asme_b31.3"
        / "nodes"
        / "paragraph"
    )


def _load_meta(name: str) -> dict:
    path = _paragraph_dir() / name
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    return meta


def test_policy_single_source_sidecar_loader_keys() -> None:
    import engine.reference.paragraph_sidecar as sidecar

    source = Path(sidecar.__file__).read_text(encoding="utf-8")
    assert "_EXECUTION_KEYS" not in source
    assert "EXECUTION_SIDECAR_KEYS" in source


def test_policy_single_source_validator() -> None:
    import engine.validation.paragraph_node_validator as validator

    source = Path(validator.__file__).read_text(encoding="utf-8")
    assert "_FORBIDDEN_FIELDS" not in source
    assert "validator_fail_messages_for_frontmatter" in source


def test_policy_single_source_ontology_test() -> None:
    source = Path(__file__).resolve().parent.joinpath("test_paragraph_ontology.py").read_text(
        encoding="utf-8"
    )
    assert "_FORBIDDEN_FIELDS" not in source
    assert "check_paragraph_frontmatter_placement" in source


def test_policy_single_source_audit_script() -> None:
    audit_path = _project_root() / "scripts" / "audit_current_node_yaml.py"
    source = audit_path.read_text(encoding="utf-8")
    assert "paragraph_sidecar import _EXECUTION_KEYS" not in source
    assert "paragraph_authoring_policy" in source
    assert "run_audit" in source
    assert "render_paragraph_report" in source


def test_validator_audit_ontology_share_forbidden_sets() -> None:
    assert validator_fail_messages_for_frontmatter(
        {"applicability": {"applies_when": [{"parameter": "PARAM-pressure-loading"}]}}
    ) == [
        "forbidden field: applicability (belongs in execution block in primary YAML)"
    ]
    placement = check_paragraph_frontmatter_placement(
        {"applicability": {"applies_when": [{"parameter": "PARAM-pressure-loading"}]}},
        node_id="304.1.3",
    )
    assert any(level == "FAIL" for level, _ in placement)


def test_304_1_2_a_execution_block_passes() -> None:
    meta = _load_meta("304.1.2-a.yaml")
    assert validate_paragraph_node(meta) == []
    assert not check_paragraph_frontmatter_placement(meta, node_id="304.1.2-a")


def test_304_1_3_execution_block_passes() -> None:
    meta = _load_meta("304.1.3.yaml")
    assert validate_paragraph_node(meta) == []


def test_304_1_1_a_execution_assumptions_pass() -> None:
    meta = _load_meta("304.1.1-a.yaml")
    assert validate_paragraph_node(meta) == []
    assert not check_paragraph_frontmatter_placement(meta, node_id="304.1.1-a")


def test_304_1_1_b_execution_parameter_defaults_pass() -> None:
    meta = _load_meta("304.1.1-b.yaml")
    assert validate_paragraph_node(meta) == []
    assert not check_paragraph_frontmatter_placement(meta, node_id="304.1.1-b")


def test_sidecar_merge_extracts_execution_block() -> None:
    merged = merge_paragraph_sidecar_metadata(
        {
            "id": "304.1.2-a",
            "type": "paragraph",
            "execution": {
                "conditions": [{"id": "thin_wall_check"}],
                "subsections": [{"id": "b"}],
            },
        },
        record_path=_paragraph_dir() / "304.1.2-a.yaml",
        node_id="304.1.2-a",
    )
    assert "conditions" in merged
    assert set(EXECUTION_SIDECAR_KEYS) >= {"conditions", "subsections"}


def test_registered_external_refs_info() -> None:
    for target in ("328.5.4", "300.2", "303", "Appendix-J"):
        findings = classify_edge_target(target, "related_to", repo_index=set())
        assert findings and findings[0][0] == "INFO", target


def test_unregistered_related_to_stays_warn() -> None:
    findings = classify_edge_target("999.9.9-z", "related_to", repo_index=set())
    assert findings and findings[0][0] == "WARN"


def test_run_audit_paragraph_projection_matches_section_a() -> None:
    scripts = str(_project_root() / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    audit_mod = importlib.import_module("audit_current_node_yaml")

    section_a, section_b, _, _ = audit_mod.run_audit()
    para_rows = [r for r in section_a + section_b if audit_mod._is_paragraph_row(r)]
    frontmatter = {r.node_id: r for r in section_a if r.canonical_type == "paragraph"}

    for row in para_rows:
        if row.canonical_type != "paragraph":
            continue
        source = frontmatter.get(row.node_id)
        assert source is not None
        assert source.problems == row.problems
        assert source.result == row.result


def test_no_sidecar_only_keys_in_frontmatter_across_repo() -> None:
    """Promotion gate — top-level execution keys must not appear outside execution block."""
    violations: list[str] = []
    for path in sorted(_paragraph_dir().glob("*.yaml")):
        if path.name.endswith(".execution.yaml") or path.name.endswith(".nomenclature.yaml"):
            continue
        meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        for key in SIDECAR_ONLY_KEYS:
            if key in FORBIDDEN_PARAGRAPH_FRONTMATTER:
                continue
            if key in meta and meta[key]:
                violations.append(f"{path.name}: {key}")
    assert not violations, violations


def test_sidecar_merge_uses_policy_execution_keys() -> None:
    test_sidecar_merge_extracts_execution_block()


def test_forbidden_runtime_keys_in_validator_messages() -> None:
    for key in FORBIDDEN_RUNTIME_STATE_KEYS:
        msgs = validator_fail_messages_for_frontmatter({key: "x"})
        assert any(key in m for m in msgs)
