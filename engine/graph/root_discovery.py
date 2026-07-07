"""Workflow root discovery helpers — specific lookup vs broad discovery."""

from __future__ import annotations

# Baseline confidence for broad discovery when no explicit workflow slug is given.
BROAD_DISCOVERY_BASE_CONFIDENCE = 0.4

# Confidence returned for an explicit slug / intent / node id match.
EXACT_WORKFLOW_MATCH_CONFIDENCE = 0.95

# Confidence for partial slug containment (typo-tolerant explicit lookup).
PARTIAL_SLUG_MATCH_CONFIDENCE = 0.9

# Confidence boost when broad-discovery keywords hit workflow metadata.
KEYWORD_MATCH_CONFIDENCE = 0.75


def is_specific_lookup(workflow: str | None) -> bool:
    """True when the caller supplied an explicit workflow slug or intent id."""
    return bool((workflow or "").strip())


def workflow_lookup_confidence(
    workflow_ref: str,
    *,
    slug: str,
    intent: str = "",
    node_id: str = "",
) -> float:
    """Return match confidence for explicit workflow lookup; 0.0 means no match."""
    ref = (workflow_ref or "").strip()
    if not ref:
        return 0.0

    for token in (slug, intent, node_id):
        if token and ref == token:
            return EXACT_WORKFLOW_MATCH_CONFIDENCE

    norm_ref = ref.replace("-", "_").lower()
    norm_slug = slug.replace("-", "_").lower()
    if norm_ref and norm_ref in norm_slug:
        return PARTIAL_SLUG_MATCH_CONFIDENCE

    return 0.0


def broad_discovery_confidence(
    *,
    keyword_text: str,
    intent: str = "",
    title: str = "",
    slug: str = "",
    node_id: str = "",
    purpose: str = "",
) -> float:
    """Score a workflow during broad discovery (no explicit slug)."""
    confidence = BROAD_DISCOVERY_BASE_CONFIDENCE
    if not keyword_text:
        return confidence

    for token in (intent, title, slug, node_id, purpose):
        if token and token.lower() in keyword_text:
            confidence = max(confidence, KEYWORD_MATCH_CONFIDENCE)
    return confidence
