"""Canonical queue and exclusion reasons for graph traversal state."""

from __future__ import annotations

# Contract-aligned queue reasons (audits/contracts/Graph Engine Behavior.md §3).
QUEUE_REASON_READY_FOR_EXPANSION = "ready_for_expansion"
QUEUE_REASON_WAITING_FOR_USER_INPUT = "waiting_for_user_input"
QUEUE_REASON_WAITING_FOR_UPSTREAM_EQUATION = "waiting_for_upstream_equation"
QUEUE_REASON_WAITING_FOR_LOOKUP_RESULT = "waiting_for_lookup_result"
QUEUE_REASON_WAITING_FOR_DEPENDENCY = "waiting_for_dependency"
QUEUE_REASON_BRANCH_CONDITION_PENDING = "branch_condition_pending"

CANONICAL_QUEUE_REASONS = frozenset(
    {
        QUEUE_REASON_READY_FOR_EXPANSION,
        QUEUE_REASON_WAITING_FOR_USER_INPUT,
        QUEUE_REASON_WAITING_FOR_UPSTREAM_EQUATION,
        QUEUE_REASON_WAITING_FOR_LOOKUP_RESULT,
        QUEUE_REASON_WAITING_FOR_DEPENDENCY,
        QUEUE_REASON_BRANCH_CONDITION_PENDING,
    }
)

# Contract-aligned exclusion reasons (§4).
EXCLUSION_REASON_BRANCH_CONDITION_NOT_SATISFIED = "branch_condition_not_satisfied"
EXCLUSION_REASON_WORKFLOW_SCOPE_MISMATCH = "workflow_scope_mismatch"
EXCLUSION_REASON_NOT_APPLICABLE = "not_applicable"
EXCLUSION_REASON_DEPENDENCY_NOT_APPLICABLE = "dependency_not_applicable"
EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH = "superseded_by_selected_branch"

CANONICAL_EXCLUSION_REASONS = frozenset(
    {
        EXCLUSION_REASON_BRANCH_CONDITION_NOT_SATISFIED,
        EXCLUSION_REASON_WORKFLOW_SCOPE_MISMATCH,
        EXCLUSION_REASON_NOT_APPLICABLE,
        EXCLUSION_REASON_DEPENDENCY_NOT_APPLICABLE,
        EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH,
    }
)

# Legacy prose labels still accepted as input for normalization.
_PROSE_TO_QUEUE: dict[str, str] = {
    "awaiting parameter gathering": QUEUE_REASON_WAITING_FOR_UPSTREAM_EQUATION,
    "awaiting user input": QUEUE_REASON_WAITING_FOR_USER_INPUT,
    "waiting for user input": QUEUE_REASON_WAITING_FOR_USER_INPUT,
    "waiting for dependency": QUEUE_REASON_WAITING_FOR_DEPENDENCY,
    "ready for expansion": QUEUE_REASON_READY_FOR_EXPANSION,
    "blocked by condition": QUEUE_REASON_BRANCH_CONDITION_PENDING,
    "excluded by branch": EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH,
    "already satisfied": QUEUE_REASON_READY_FOR_EXPANSION,
}

_PROSE_TO_EXCLUSION: dict[str, str] = {
    "excluded by branch": EXCLUSION_REASON_SUPERSEDED_BY_SELECTED_BRANCH,
    "blocked by condition": EXCLUSION_REASON_BRANCH_CONDITION_NOT_SATISFIED,
    "not applicable": EXCLUSION_REASON_NOT_APPLICABLE,
}


def normalize_queue_reason(reason: str | None) -> str:
    """Map legacy prose or canonical token to a canonical queue reason."""
    if not reason:
        return QUEUE_REASON_WAITING_FOR_DEPENDENCY
    text = str(reason).strip()
    if text in CANONICAL_QUEUE_REASONS:
        return text
    lowered = text.lower()
    if lowered in _PROSE_TO_QUEUE:
        mapped = _PROSE_TO_QUEUE[lowered]
        if mapped in CANONICAL_EXCLUSION_REASONS:
            return QUEUE_REASON_BRANCH_CONDITION_PENDING
        return mapped
    if "parameter gathering" in lowered or "upstream equation" in lowered:
        return QUEUE_REASON_WAITING_FOR_UPSTREAM_EQUATION
    if "lookup" in lowered:
        return QUEUE_REASON_WAITING_FOR_LOOKUP_RESULT
    if "user input" in lowered or "awaiting" in lowered:
        return QUEUE_REASON_WAITING_FOR_USER_INPUT
    if "branch" in lowered or "condition" in lowered:
        return QUEUE_REASON_BRANCH_CONDITION_PENDING
    if "ready" in lowered or "expansion" in lowered:
        return QUEUE_REASON_READY_FOR_EXPANSION
    return QUEUE_REASON_WAITING_FOR_DEPENDENCY


def normalize_exclusion_reason(reason: str | None) -> str:
    """Map skip/prose text to a canonical exclusion reason."""
    if not reason:
        return EXCLUSION_REASON_NOT_APPLICABLE
    text = str(reason).strip()
    if text in CANONICAL_EXCLUSION_REASONS:
        return text
    lowered = text.lower()
    if lowered in _PROSE_TO_EXCLUSION:
        return _PROSE_TO_EXCLUSION[lowered]
    if "branch" in lowered or "when " in lowered or "not satisfied" in lowered:
        return EXCLUSION_REASON_BRANCH_CONDITION_NOT_SATISFIED
    if "not applicable" in lowered or "applicability" in lowered:
        return EXCLUSION_REASON_NOT_APPLICABLE
    if "scope" in lowered:
        return EXCLUSION_REASON_WORKFLOW_SCOPE_MISMATCH
    if "dependency" in lowered:
        return EXCLUSION_REASON_DEPENDENCY_NOT_APPLICABLE
    return EXCLUSION_REASON_NOT_APPLICABLE
