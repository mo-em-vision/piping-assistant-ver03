"""Build planner decision records from execution plan metadata."""

from __future__ import annotations

from typing import Any

from engine.inspection.models import GraphEdgeRef, PlannerDecision
from models.execution import ExecutionPlan


def build_planner_decisions(plan: ExecutionPlan) -> dict[str, PlannerDecision]:
    """Derive per-node planner explanations from plan structure."""
    decisions: dict[str, PlannerDecision] = {}
    edges = list(plan.dependencies)
    if plan.graph_version and plan.graph_version.edges:
        edges = list(plan.graph_version.edges)

    skipped_by_id = {
        str(item.get("node_id", "")): item
        for item in plan.skipped_nodes
        if item.get("node_id")
    }

    rejected_pool: list[dict[str, str]] = []
    for node_id, item in skipped_by_id.items():
        rejected_pool.append(
            {
                "node_id": node_id,
                "reason": str(item.get("reason", "skipped")),
            }
        )

    completed: set[str] = set()
    for node_id in plan.execution_order:
        incoming = _first_incoming(node_id, edges, completed)
        trigger = incoming.from_node if incoming else None
        why = _why_selected(node_id, trigger, skipped_by_id)
        rule = "topological_sort" if not skipped_by_id.get(node_id) else "when_clause"

        decisions[node_id] = PlannerDecision(
            node_id=node_id,
            why_selected=why,
            trigger_dependency=trigger,
            edge_followed=incoming,
            rule_fired=rule,
            rejected_candidates=[
                item for item in rejected_pool if item["node_id"] != node_id
            ],
        )
        completed.add(node_id)

    for node_id, item in skipped_by_id.items():
        if node_id in decisions:
            continue
        decisions[node_id] = PlannerDecision(
            node_id=node_id,
            why_selected=str(item.get("reason", "condition_not_met")),
            trigger_dependency=str(item.get("field", "")) or None,
            edge_followed=None,
            rule_fired="when_clause",
            rejected_candidates=[],
        )

    return decisions


def planner_decisions_from_task_outputs(outputs: dict[str, Any]) -> dict[str, PlannerDecision]:
    stored = outputs.get("_planner_decisions")
    if isinstance(stored, dict):
        result: dict[str, PlannerDecision] = {}
        for node_id, raw in stored.items():
            if not isinstance(raw, dict):
                continue
            edge_raw = raw.get("edge_followed")
            edge = None
            if isinstance(edge_raw, dict):
                edge = GraphEdgeRef(
                    from_node=str(edge_raw.get("from_node", "")),
                    to_node=str(edge_raw.get("to_node", "")),
                    edge_type=str(edge_raw.get("edge_type", "")),
                )
            rejected = raw.get("rejected_candidates")
            result[str(node_id)] = PlannerDecision(
                node_id=str(node_id),
                why_selected=str(raw.get("why_selected", "")),
                trigger_dependency=raw.get("trigger_dependency"),
                edge_followed=edge,
                rule_fired=str(raw.get("rule_fired", "")),
                rejected_candidates=list(rejected) if isinstance(rejected, list) else [],
            )
        return result
    return {}


def planner_decisions_to_dict(decisions: dict[str, PlannerDecision]) -> dict[str, dict[str, Any]]:
    return {node_id: decision.to_dict() for node_id, decision in decisions.items()}


def _first_incoming(
    node_id: str,
    edges: list[Any],
    completed: set[str],
) -> GraphEdgeRef | None:
    for edge in edges:
        to_node = getattr(edge, "to_node", None) or edge.get("to_node") if isinstance(edge, dict) else edge.to_node
        if to_node != node_id:
            continue
        from_node = getattr(edge, "from_node", None) or (edge.get("from_node") if isinstance(edge, dict) else "")
        if from_node in completed or not completed:
            edge_type = getattr(edge, "type", None)
            if edge_type is not None and hasattr(edge_type, "value"):
                edge_type_str = edge_type.value
            elif isinstance(edge, dict):
                edge_type_str = str(edge.get("type", edge.get("edge_type", "requires")))
            else:
                edge_type_str = str(getattr(edge, "type", "requires"))
            return GraphEdgeRef(
                from_node=str(from_node),
                to_node=str(to_node),
                edge_type=edge_type_str,
            )
    return None


def _why_selected(
    node_id: str,
    trigger: str | None,
    skipped: dict[str, dict[str, Any]],
) -> str:
    if node_id in skipped:
        return str(skipped[node_id].get("reason", "skipped"))
    if trigger:
        return f"dependency_satisfied:{trigger}"
    return "dependency_satisfied"
