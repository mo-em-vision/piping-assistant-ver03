"""Synthetic tests for paragraph authoring policy placement and edge classification."""

from __future__ import annotations

import pytest

from engine.reference import paragraph_authoring_policy as policy
from engine.reference.paragraph_authoring_policy import (
    EXECUTION_BLOCK_ENFORCEMENT,
    EXECUTION_SIDECAR_KEYS,
    EXTERNAL_UNMODELED_REF_REGISTRY,
    FORBIDDEN_PARAGRAPH_FRONTMATTER,
    FORBIDDEN_RUNTIME_STATE_KEYS,
    SIDECAR_ONLY_ENFORCEMENT,
    SIDECAR_ONLY_KEYS,
    check_paragraph_frontmatter_placement,
    check_paragraph_sidecar_surface,
    classify_edge_target,
    sidecar_only_severity,
    validator_fail_messages_for_frontmatter,
)


@pytest.mark.parametrize(
    ("key", "expected_severity"),
    [
        ("runtime_value", "FAIL"),
        ("fact_value", "FAIL"),
        ("user_input", "FAIL"),
    ],
)
def test_runtime_state_keys_fail_in_frontmatter(key: str, expected_severity: str) -> None:
    findings = check_paragraph_frontmatter_placement(
        {"type": "paragraph", key: "x"}, node_id="304.1.1-a"
    )
    assert any(level == expected_severity and key in msg for level, msg in findings)


@pytest.mark.parametrize(
    "key",
    ["trace", "report", "ai_hints"],
)
def test_forbidden_paragraph_frontmatter_fails(key: str) -> None:
    value = "x"
    if key == "limitations":
        value = []
    findings = check_paragraph_frontmatter_placement(
        {"type": "paragraph", key: value},
        node_id="304.1.2-a",
    )
    assert any(level == "FAIL" for level, _ in findings)


def test_sidecar_only_assumptions_fail_at_top_level() -> None:
    assert EXECUTION_BLOCK_ENFORCEMENT == "fail"
    assert sidecar_only_severity() == "FAIL"
    findings = check_paragraph_frontmatter_placement(
        {"type": "paragraph", "assumptions": [{"id": "a"}]},
        node_id="304.1.1-a",
    )
    assert findings == [
        ("FAIL", "assumptions belongs in execution block in primary YAML; migration required")
    ]


def test_sidecar_only_promotion_to_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy, "SIDECAR_ONLY_ENFORCEMENT", "fail")
    assert sidecar_only_severity() == "FAIL"
    findings = check_paragraph_frontmatter_placement(
        {"type": "paragraph", "parameter_defaults": {"c": []}},
        node_id="304.1.1-b",
    )
    assert any(level == "FAIL" and "parameter_defaults" in msg for level, msg in findings)


def test_duplicate_sidecar_surface_same_key() -> None:
    findings = check_paragraph_sidecar_surface(
        {"assumptions": [{"id": "a"}]},
        {"assumptions": [{"id": "b"}]},
        node_id="304.1.1-a",
    )
    assert any("Duplicate authoring surface" in msg and "assumptions" in msg for _, msg in findings)


def test_split_sidecar_surface_different_keys() -> None:
    findings = check_paragraph_sidecar_surface(
        {"applicability": {"applies_when": []}},
        {"conditions": [{"id": "x"}], "subsections": [{"id": "b"}]},
        node_id="304.1.2-a",
    )
    assert any("Execution metadata split across two authoring surfaces" in msg for _, msg in findings)


@pytest.mark.parametrize(
    ("target", "edge_type", "repo_index", "registry", "expected_severity"),
    [
        ("304.1.1-a", "related_to", {"304.1.1-a"}, frozenset(), None),
        ("328.5.4", "related_to", set(), EXTERNAL_UNMODELED_REF_REGISTRY, "INFO"),
        ("328.5.4", "related_to", set(), frozenset(), "WARN"),
        ("asme-b313-missing", "references_equation", set(), frozenset(), "FAIL"),
        ("", "related_to", set(), frozenset(), "FAIL"),
    ],
)
def test_classify_edge_target_matrix(
    target: str,
    edge_type: str,
    repo_index: set[str],
    registry: frozenset[str],
    expected_severity: str | None,
) -> None:
    findings = classify_edge_target(
        target, edge_type, repo_index=repo_index, external_registry=registry
    )
    if expected_severity is None:
        assert findings == []
    else:
        assert findings and findings[0][0] == expected_severity


def test_validator_forbidden_union_matches_policy() -> None:
    meta = {
        "execution": {"applicability": {"applies_when": []}},
        "runtime_value": 1,
        "assumptions": [{"id": "a"}],
    }
    messages = validator_fail_messages_for_frontmatter(meta)
    assert any("runtime_value" in m for m in messages)
    assert any("assumptions" in m for m in messages)
    assert not any("applicability" in m for m in messages)


def test_execution_sidecar_keys_subset_of_sidecar_only() -> None:
    assert set(EXECUTION_SIDECAR_KEYS) <= SIDECAR_ONLY_KEYS


def test_forbidden_sets_do_not_overlap_runtime_and_sidecar_only() -> None:
    assert not (FORBIDDEN_RUNTIME_STATE_KEYS & SIDECAR_ONLY_KEYS)
    assert "applicability" in SIDECAR_ONLY_KEYS
