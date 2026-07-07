"""Flow Guidance Layer — traversal narration resolver."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from models.presentation import GuidanceBlock, GuidanceContext

_GUIDANCE_ROOT = Path(__file__).resolve().parents[2] / "presentation" / "guidance" / "workflows"

# Patterns that must not appear in guidance YAML text (presentation contract only).
_FORBIDDEN_FORMULA_MARKERS = re.compile(
    r"(\\frac\b|t\s*=\s*\\frac|=\s*\([^)]*P[^)]*\)|\\sqrt\b)",
    re.IGNORECASE,
)
_FORBIDDEN_PARAMETER_PROMPT_MARKERS = re.compile(
    r"(please provide:|enter the nominal pipe size|select the pipe material|"
    r"is the pipe subject to internal or external pressure)",
    re.IGNORECASE,
)

_MATCH_KEYS = (
    "current_phase",
    "active_node_id",
    "node_role",
    "traversal_event",
    "edge_reason",
)


class GuidanceValidationError(ValueError):
    """Raised when guidance YAML content violates presentation-only rules."""


def validate_guidance_text(text: str, *, refs: dict[str, str] | None = None) -> None:
    """Reject guidance text that duplicates formulas or parameter prompt copy."""
    if _FORBIDDEN_FORMULA_MARKERS.search(text):
        raise GuidanceValidationError("guidance text must not duplicate formula text")
    if _FORBIDDEN_PARAMETER_PROMPT_MARKERS.search(text):
        raise GuidanceValidationError(
            "guidance text must not duplicate deterministic parameter prompt copy"
        )
    refs = refs or {}
    if "equation_id" in refs and _FORBIDDEN_FORMULA_MARKERS.search(text):
        raise GuidanceValidationError(
            "guidance with equation_id reference must not embed formula text"
        )


def guidance_workflows_root() -> Path:
    return _GUIDANCE_ROOT


def _normalize_workflow_id(workflow_id: str) -> str:
    return workflow_id.strip().replace("-", "_").lower()


def _workflow_guidance_path(workflow_id: str, *, guidance_root: Path) -> Path:
    slug = _normalize_workflow_id(workflow_id)
    return guidance_root / f"{slug}.yaml"


def _context_value(context: GuidanceContext, key: str) -> str | None:
    value = getattr(context, key, None)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _entry_matches(context: GuidanceContext, match: dict[str, Any]) -> bool:
    if not isinstance(match, dict):
        return False
    for key in _MATCH_KEYS:
        expected = match.get(key)
        if expected is None:
            continue
        actual = _context_value(context, key)
        if actual is None or str(expected).strip() != actual:
            return False

    when = match.get("when")
    if isinstance(when, dict):
        for fact_key, expected in when.items():
            actual = context.task_facts.get(fact_key)
            if actual != expected:
                return False
    return True


def _match_specificity(match: dict[str, Any]) -> int:
    if not isinstance(match, dict):
        return 0
    score = sum(1 for key in _MATCH_KEYS if match.get(key) is not None)
    when = match.get("when")
    if isinstance(when, dict):
        score += len(when)
    return score


def _entry_to_block(entry: dict[str, Any]) -> GuidanceBlock:
    entry_id = str(entry.get("id") or "guidance")
    text = str(entry.get("text") or "").strip()
    refs_raw = entry.get("refs") or {}
    refs = {str(key): str(value) for key, value in refs_raw.items() if value is not None}
    validate_guidance_text(text, refs=refs)
    return GuidanceBlock(
        block_id=entry_id,
        text=text,
        refs=refs,
    )


def guidance_context_from_navigation(
    *,
    workflow_id: str,
    current_phase: str | None,
    phase_missing: dict[str, list[str]] | None = None,
    active_node_id: str | None = None,
    node_role: str | None = None,
    traversal_event: str | None = None,
    task_facts: dict[str, Any] | None = None,
) -> GuidanceContext:
    """Build resolver context from navigation metadata — not planner message text."""
    edge_reason: str | None = None
    if current_phase and phase_missing:
        fields = phase_missing.get(current_phase) or []
        if fields:
            edge_reason = str(fields[0])

    event = traversal_event
    if event is None and current_phase in {
        "expansion_assumptions",
        "path_decisions",
    }:
        event = "branch_decision_required"
    if event is None and active_node_id:
        event = "node_selected"

    return GuidanceContext(
        workflow_id=workflow_id,
        current_phase=current_phase,
        active_node_id=active_node_id,
        node_role=node_role,
        traversal_event=event,
        edge_reason=edge_reason,
        task_facts=dict(task_facts or {}),
    )


class GuidanceResolver:
    """Retrieve traversal narration blocks from presentation guidance YAML."""

    def __init__(self, *, guidance_root: Path | None = None) -> None:
        self._guidance_root = guidance_root or _GUIDANCE_ROOT
        self._cache: dict[str, dict[str, Any]] = {}

    def resolve(self, context: GuidanceContext) -> tuple[GuidanceBlock, ...]:
        """Return guidance blocks for the given traversal context."""
        payload = self.load_workflow_guidance(context.workflow_id)
        entries = payload.get("entries") or []
        if not isinstance(entries, list):
            return ()

        best: dict[str, Any] | None = None
        best_score = -1
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            match = entry.get("match") or {}
            if not _entry_matches(context, match):
                continue
            score = _match_specificity(match)
            if score > best_score:
                best = entry
                best_score = score

        if best is None:
            return ()
        return (_entry_to_block(best),)

    def load_workflow_guidance(self, workflow_id: str) -> dict[str, Any]:
        """Load raw guidance YAML for a workflow."""
        slug = _normalize_workflow_id(workflow_id)
        if slug in self._cache:
            return self._cache[slug]

        path = _workflow_guidance_path(workflow_id, guidance_root=self._guidance_root)
        if not path.is_file():
            self._cache[slug] = {"workflow_id": slug, "entries": []}
            return self._cache[slug]

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise GuidanceValidationError(f"guidance workflow file must be a mapping: {path}")

        entries = raw.get("entries") or []
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                text = str(entry.get("text") or "").strip()
                refs_raw = entry.get("refs") or {}
                refs = {
                    str(key): str(value)
                    for key, value in refs_raw.items()
                    if value is not None
                }
                validate_guidance_text(text, refs=refs)

        self._cache[slug] = raw
        return raw
