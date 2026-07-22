"""Tests for scripts/restricted_path_check.py."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.restricted_path_check import (
    Manifest,
    TaskContext,
    check_normative_language,
    classify_path,
    load_manifest,
    parse_task_context,
    validate_changed_paths,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "config" / "restricted_paths.yaml"


def test_load_production_manifest() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    assert classify_path("docs/rules.md", manifest) == "constitutional"
    assert classify_path("api/server.py", manifest) is None
    assert classify_path(".cursor/rules/agent-rules.mdc", manifest) == "agent_rule"
    assert classify_path("docs/core/1. Architecture.md", manifest) == "architecture_authoritative"
    assert classify_path("docs/audit/MAINTENANCE.md", manifest) == "explanatory"
    assert classify_path("knowledge/standards/README.md", manifest) == "contract"
    assert (
        classify_path("contracts/center_panel_report_role_order.json", manifest)
        == "generated"
    )


def test_unprotected_path() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    assert classify_path("api/server.py", manifest) is None


def test_implementation_mode_blocks_constitutional() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["docs/rules.md"],
        TaskContext(),
        manifest,
    )
    assert not ok
    assert any(
        v.message == "RESTRICTED DOCUMENTATION PHASE REQUIRED — IMPLEMENTATION BLOCKED"
        for v in violations
    )


def test_implementation_mode_blocks_architecture_authoritative() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["docs/core/1. Architecture.md"],
        TaskContext(),
        manifest,
    )
    assert not ok
    assert violations[0].categories == ("architecture_authoritative",)


def test_implementation_mode_explanatory_in_impact_report() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["docs/audit/MAINTENANCE.md"],
        TaskContext(impact_report=frozenset({"docs/audit/MAINTENANCE.md"})),
        manifest,
        path_diffs={"docs/audit/MAINTENANCE.md": "+++ b\n+Sync note only.\n"},
    )
    assert ok
    assert not violations


def test_implementation_mode_explanatory_not_in_impact_report() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["docs/audit/MAINTENANCE.md"],
        TaskContext(),
        manifest,
    )
    assert not ok
    assert any(
        v.message == "EXPLANATORY SYNC VIOLATION — NOT IN IMPACT REPORT"
        for v in violations
    )


def test_implementation_mode_normative_language_in_diff() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["docs/audit/MAINTENANCE.md"],
        TaskContext(impact_report=frozenset({"docs/audit/MAINTENANCE.md"})),
        manifest,
        path_diffs={"docs/audit/MAINTENANCE.md": "+++ b\n+Agents must update this file.\n"},
    )
    assert not ok
    assert any(
        v.message == "EXPLANATORY SYNC VIOLATION — NORMATIVE LANGUAGE"
        for v in violations
    )


def test_documentation_edit_mode_allows_listed_file() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["docs/rules.md"],
        TaskContext(
            mode="documentation-edit",
            allowed_files=frozenset({"docs/rules.md"}),
        ),
        manifest,
    )
    assert ok
    assert not violations


def test_documentation_edit_mode_denies_unlisted_protected_file() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["docs/protected-files/registry.md"],
        TaskContext(
            mode="documentation-edit",
            allowed_files=frozenset({"docs/rules.md"}),
        ),
        manifest,
    )
    assert not ok
    assert any(v.message == "RESTRICTED-FILE EDIT NOT AUTHORIZED" for v in violations)


def test_mixed_code_and_constitutional_doc() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["api/server.py", "docs/rules.md"],
        TaskContext(),
        manifest,
    )
    assert not ok
    assert any(
        v.message == "MIXED RESTRICTED-FILE AND IMPLEMENTATION TASK — BLOCKED"
        for v in violations
    )


def test_generated_always_blocked() -> None:
    manifest = load_manifest(MANIFEST_PATH)
    ok, violations = validate_changed_paths(
        ["contracts/center_panel_report_role_order.json"],
        TaskContext(
            mode="documentation-edit",
            allowed_files=frozenset(
                {"contracts/center_panel_report_role_order.json"}
            ),
        ),
        manifest,
    )
    assert not ok
    assert any(v.message == "GENERATED FILE — MANUAL EDIT BLOCKED" for v in violations)


def test_load_manifest_rejects_unknown_category(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        yaml.dump(
            {
                "version": 1,
                "globs": [{"pattern": "docs/**", "category": "not_a_category"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown category"):
        load_manifest(bad)


def test_load_manifest_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "missing.yaml")


def test_parse_task_context() -> None:
    message = """
Mode: documentation-edit

Allowed files:
- docs/rules.md
- docs/protected-files/registry.md

Implementation impact report:
- docs/audit/MAINTENANCE.md
"""
    ctx = parse_task_context(message)
    assert ctx.mode == "documentation-edit"
    assert ctx.allowed_files == frozenset(
        {"docs/rules.md", "docs/protected-files/registry.md"}
    )
    assert ctx.impact_report == frozenset({"docs/audit/MAINTENANCE.md"})


def test_check_normative_language_allows_quoted() -> None:
    diff = '+++ b\n+See `must` in code only.\n+Quote: "must" inside.\n'
    assert not check_normative_language(diff)


def test_check_normative_language_detects_added_must() -> None:
    diff = "+++ b\n+This layer must not own prompts.\n"
    assert check_normative_language(diff)


def test_explicit_entry_overrides_glob(tmp_path: Path) -> None:
    manifest = Manifest(
        globs=(("docs/audit/**", "explanatory"),),
        entries={"docs/audit/SPECIAL.md": "architecture_explanatory"},
    )
    assert classify_path("docs/audit/SPECIAL.md", manifest) == "architecture_explanatory"
    assert classify_path("docs/audit/OTHER.md", manifest) == "explanatory"
