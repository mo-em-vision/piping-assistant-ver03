"""Graph-derived planning structure snapshots for refresh gating."""

from __future__ import annotations

import json
from typing import Any

from engine.graph.assumption_checker import AssumptionEvaluation
from engine.graph.navigation_phases import PhasedNavigation
from models.execution import ExecutionPlan

STRUCTURAL_SIGNATURE_KEYS: tuple[str, ...] = (
    "execution_order",
    "active_nodes",
    "current_phase",
    "active_branch_decisions",
    "expansion_gate_state",
    "path_decision_state",
)


def _sorted_unique(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    return sorted({str(item) for item in values if item is not None and str(item).strip()})


def _normalize_path_decision(path_decision: Any) -> dict[str, str]:
    if not isinstance(path_decision, dict):
        return {}
    normalized: dict[str, str] = {}
    for key in ("field", "parameter", "value", "choice", "selected_node"):
        raw = path_decision.get(key)
        if raw is not None and str(raw).strip():
            normalized[key] = str(raw).strip()
    return normalized


def _blocked_requirement_ids(*evaluations: AssumptionEvaluation) -> list[str]:
    blocked: list[str] = []
    for evaluation in evaluations:
        for block in evaluation.blocked:
            for candidate in (block.field, getattr(block, "assumption_id", None), block.value):
                if candidate is not None and str(candidate).strip():
                    blocked.append(str(candidate).strip())
                    break
    return _sorted_unique(blocked)


def _active_branch_decisions(
    expansion_eval: AssumptionEvaluation,
    path_decision: dict[str, str],
) -> list[str]:
    branches = _sorted_unique(expansion_eval.missing_fields)
    field = path_decision.get("field") or path_decision.get("parameter")
    if field and field not in branches:
        branches.append(field)
    return sorted(set(branches))


def build_planning_structure_snapshot(
    *,
    preview: ExecutionPlan,
    active_nodes: list[str],
    phased: PhasedNavigation,
    path_decision: dict[str, Any] | None,
    expansion_eval: AssumptionEvaluation,
    assumption_eval: AssumptionEvaluation,
    execution_eval: AssumptionEvaluation,
    missing_inputs: list[str] | set[str],
    expansion_gate_ready: bool,
    lazy_plan: bool,
    submittable_parameters: list[str] | None = None,
) -> dict[str, Any] | None:
    """Build a full planning structure snapshot. Returns None on uncertainty."""
    try:
        if not preview.execution_order:
            return None
        path_state = _normalize_path_decision(path_decision)
        phase_key = phased.current_phase.value
        phase_submittable = _sorted_unique(phased.phase_missing.get(phase_key) or [])
        submittable = _sorted_unique(submittable_parameters or phase_submittable)
        next_input = None
        if phased.all_missing:
            next_input = str(phased.all_missing[0])
        elif submittable:
            next_input = submittable[0]
        elif missing_inputs:
            ordered_missing = _sorted_unique(missing_inputs)
            next_input = ordered_missing[0] if ordered_missing else None

        return {
            "execution_order": list(preview.execution_order),
            "active_nodes": list(active_nodes),
            "current_phase": phase_key,
            "next_input": next_input,
            "missing_inputs": _sorted_unique(missing_inputs),
            "missing_assumptions": _sorted_unique(
                list(assumption_eval.missing_fields) + list(expansion_eval.missing_fields)
            ),
            "submittable_parameters": submittable,
            "blocked_requirement_ids": _blocked_requirement_ids(
                expansion_eval,
                assumption_eval,
                execution_eval,
            ),
            "active_branch_decisions": _active_branch_decisions(expansion_eval, path_state),
            "expansion_gate_state": {
                "workflow_gate_ready": bool(expansion_gate_ready),
                "lazy_plan": bool(lazy_plan),
                "expansion_missing_fields": _sorted_unique(expansion_eval.missing_fields),
                "assumption_missing_fields": _sorted_unique(assumption_eval.missing_fields),
            },
            "path_decision_state": path_state,
        }
    except Exception:
        return None


def structure_unchanged_for_skip(
    stored: dict[str, Any] | None,
    new_snapshot: dict[str, Any],
) -> bool:
    """Return True when structural fields are unchanged (safe to skip goal-tree rebuild)."""
    if not isinstance(stored, dict):
        return False
    for key in STRUCTURAL_SIGNATURE_KEYS:
        if stored.get(key) != new_snapshot.get(key):
            return False
    return True


def snapshot_signature_text(snapshot: dict[str, Any]) -> str:
    """Stable text form for logging/tests."""
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
