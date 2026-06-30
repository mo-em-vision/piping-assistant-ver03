"""Build execution trace steps from task outputs."""

from __future__ import annotations

from typing import Any

from engine.inspection.models import ExecutionTraceStep, GraphEdgeRef
from engine.inspection.planner_decisions import build_planner_decisions
from engine.reference.standards_reader import StandardsReader
from models.execution import ExecutionPlan, NodeExecutionStatus


_STATUS_MAP = {
    NodeExecutionStatus.COMPLETED.value: "success",
    NodeExecutionStatus.ERROR.value: "failed",
    NodeExecutionStatus.SKIPPED.value: "skipped",
    NodeExecutionStatus.AWAITING_INPUT.value: "awaiting_input",
    NodeExecutionStatus.PENDING.value: "pending",
}


def build_execution_trace(
    task_outputs: dict[str, Any],
    *,
    reader: StandardsReader | None = None,
    workflow_id: str = "",
) -> list[ExecutionTraceStep]:
    """Normalize raw _execution_trace into ExecutionTraceStep records."""
    raw_trace = task_outputs.get("_execution_trace")
    if not isinstance(raw_trace, list):
        raw_trace = []

    workflow_id = workflow_id or str(
        task_outputs.get("workflow")
        or task_outputs.get("graph_root")
        or task_outputs.get("selected_root")
        or ""
    )

    edges = _resolve_edges(task_outputs)
    from engine.inspection.planner_decisions import planner_decisions_from_task_outputs

    stored_decisions = planner_decisions_from_task_outputs(task_outputs)
    steps: list[ExecutionTraceStep] = []

    for index, item in enumerate(raw_trace):
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id", ""))
        inspection = item.get("trace", {}).get("inspection", {})
        if not isinstance(inspection, dict):
            inspection = {}

        node_type = str(inspection.get("node_type") or _node_type(reader, node_id))
        status_raw = str(item.get("status", ""))
        status = _STATUS_MAP.get(status_raw, status_raw or "pending")

        incoming = _edge_from_dict(inspection.get("incoming_edge")) or _first_incoming(
            node_id, edges
        )
        outgoing = _edge_from_dict(inspection.get("outgoing_edge")) or _first_outgoing(
            node_id, edges
        )

        decision = stored_decisions.get(node_id)
        selection_reason = str(
            inspection.get("selection_reason")
            or (decision.why_selected if decision else "")
            or item.get("trace", {}).get("reason", "")
            or "dependency_satisfied"
        )

        timestamp = item.get("timestamp")
        ts_str = str(timestamp) if timestamp is not None else None

        steps.append(
            ExecutionTraceStep(
                step_index=int(inspection.get("step_index", index)),
                workflow_id=str(inspection.get("workflow_id", workflow_id)),
                node_id=node_id,
                node_type=node_type,
                incoming_edge=incoming,
                outgoing_edge=outgoing,
                selection_reason=selection_reason,
                inputs=dict(item.get("inputs") or {}),
                outputs=dict(item.get("outputs") or {}),
                duration_ms=_float_or_none(inspection.get("duration_ms")),
                status=status,
                timestamp=ts_str,
                errors=list(item.get("errors") or []),
                warnings=list(item.get("warnings") or []),
                trace=dict(item.get("trace") or {}),
            )
        )

    skipped = task_outputs.get("_skipped_trace")
    if isinstance(skipped, list):
        base_index = len(steps)
        for offset, item in enumerate(skipped):
            if not isinstance(item, dict):
                continue
            node_id = str(item.get("node_id", ""))
            steps.append(
                ExecutionTraceStep(
                    step_index=base_index + offset,
                    workflow_id=workflow_id,
                    node_id=node_id,
                    node_type=str(item.get("node_type", "")),
                    incoming_edge=_edge_from_dict(item.get("incoming_edge")),
                    outgoing_edge=None,
                    selection_reason=str(item.get("reason", "skipped")),
                    inputs={},
                    outputs={},
                    duration_ms=None,
                    status="skipped",
                    timestamp=None,
                )
            )

    return steps


def enrich_execution_result_trace(
    result_dict: dict[str, Any],
    *,
    step_index: int,
    workflow_id: str,
    node_type: str,
    duration_ms: float,
    incoming_edge: GraphEdgeRef | None,
    outgoing_edge: GraphEdgeRef | None,
    selection_reason: str,
) -> dict[str, Any]:
    """Attach inspection metadata to a serialized NodeExecutionResult."""
    trace = dict(result_dict.get("trace") or {})
    trace["inspection"] = {
        "step_index": step_index,
        "workflow_id": workflow_id,
        "node_type": node_type,
        "duration_ms": round(duration_ms, 3),
        "incoming_edge": incoming_edge.to_dict() if incoming_edge else None,
        "outgoing_edge": outgoing_edge.to_dict() if outgoing_edge else None,
        "selection_reason": selection_reason,
    }
    result_dict["trace"] = trace
    return result_dict


def _resolve_edges(outputs: dict[str, Any]) -> list[GraphEdgeRef]:
    edges: list[GraphEdgeRef] = []
    graph_version = outputs.get("graph_version")
    if isinstance(graph_version, dict):
        for item in graph_version.get("edges") or []:
            if isinstance(item, dict):
                edges.append(
                    GraphEdgeRef(
                        from_node=str(item.get("from_node", "")),
                        to_node=str(item.get("to_node", "")),
                        edge_type=str(item.get("type", item.get("edge_type", "requires"))),
                    )
                )
    plan_edges = outputs.get("_plan_edges")
    if isinstance(plan_edges, list):
        for item in plan_edges:
            if isinstance(item, dict):
                edges.append(
                    GraphEdgeRef(
                        from_node=str(item.get("from_node", "")),
                        to_node=str(item.get("to_node", "")),
                        edge_type=str(item.get("edge_type", "requires")),
                    )
                )
    return edges


def _node_type(reader: StandardsReader | None, node_id: str) -> str:
    if reader is None or not node_id:
        return ""
    try:
        return str(reader.load(node_id).metadata.get("type", ""))
    except FileNotFoundError:
        return ""


def _edge_from_dict(raw: Any) -> GraphEdgeRef | None:
    if not isinstance(raw, dict):
        return None
    from_node = str(raw.get("from_node", ""))
    to_node = str(raw.get("to_node", ""))
    if not from_node or not to_node:
        return None
    return GraphEdgeRef(
        from_node=from_node,
        to_node=to_node,
        edge_type=str(raw.get("edge_type", "requires")),
    )


def _first_incoming(node_id: str, edges: list[GraphEdgeRef]) -> GraphEdgeRef | None:
    for edge in edges:
        if edge.to_node == node_id:
            return edge
    return None


def _first_outgoing(node_id: str, edges: list[GraphEdgeRef]) -> GraphEdgeRef | None:
    for edge in edges:
        if edge.from_node == node_id:
            return edge
    return None


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def persist_plan_metadata(
    outputs: dict[str, Any],
    plan: ExecutionPlan,
) -> None:
    """Store plan edges and planner decisions on task outputs for inspection."""
    edges = []
    if plan.graph_version:
        for edge in plan.graph_version.edges:
            edge_type = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
            edges.append(
                {
                    "from_node": edge.from_node,
                    "to_node": edge.to_node,
                    "edge_type": edge_type,
                }
            )
    outputs["_plan_edges"] = edges

    decisions = build_planner_decisions(plan)
    from engine.inspection.planner_decisions import planner_decisions_to_dict

    outputs["_planner_decisions"] = planner_decisions_to_dict(decisions)

    skipped_trace = []
    for item in plan.skipped_nodes:
        node_id = str(item.get("node_id", ""))
        if not node_id:
            continue
        skipped_trace.append(
            {
                "node_id": node_id,
                "reason": str(item.get("reason", "skipped")),
                "node_type": "",
                "incoming_edge": None,
            }
        )
    outputs["_skipped_trace"] = skipped_trace
