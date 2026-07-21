"""Build center-panel blocks from planner traversal activation state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.equation_evaluation_display import build_equation_evaluation_block
from api.node_display import build_activated_node_blocks
from api.paragraph_display import build_paragraph_display_block
from engine.planner.plan_selection import engineering_plan_for_task
from engine.reference.standards_reader import StandardsReader
from models.display_role import DisplayRole
from models.engineering_plan import EngineeringPlan, PlannerTraversalState
from models.task import Task

_SKIP_TRAVERSAL_NODE_TYPES = frozenset({"parameter", "workflow"})
_PARAGRAPH_NODE_TYPES = frozenset({"paragraph", "text", "definition"})


@dataclass(frozen=True)
class TraversalDisplayNode:
    node_id: str
    node_type: str
    bucket: str


def collect_traversal_display_nodes(plan: EngineeringPlan | None) -> list[TraversalDisplayNode]:
    """Return structural nodes activated in planner traversal, in display order."""
    if plan is None or plan.traversal is None:
        return []

    traversal: PlannerTraversalState = plan.traversal
    ordered: list[TraversalDisplayNode] = []
    seen: set[str] = set()

    def append(node_id: str, node_type: str, bucket: str) -> None:
        node_id = str(node_id or "").strip()
        node_type = str(node_type or "").strip().lower()
        if not node_id or node_id in seen:
            return
        if node_type in _SKIP_TRAVERSAL_NODE_TYPES:
            return
        seen.add(node_id)
        ordered.append(
            TraversalDisplayNode(
                node_id=node_id,
                node_type=node_type,
                bucket=bucket,
            )
        )

    expanded = sorted(
        list(traversal.expanded_nodes),
        key=lambda item: int(item.expanded_at_order or 0),
    )
    for item in expanded:
        append(item.node_id, item.node_type, "expanded")

    for item in traversal.pending_expansion_nodes:
        append(item.node_id, item.node_type, "pending")

    active = traversal.current_active_node
    if active is not None:
        append(active.node_id, active.node_type, "active")

    return ordered


def traversal_equation_node_ids(task: Task) -> frozenset[str]:
    """Equation node ids currently activated in planner traversal."""
    plan = engineering_plan_for_task(task)
    if plan is None:
        return frozenset()
    return frozenset(
        item.node_id
        for item in collect_traversal_display_nodes(plan)
        if item.node_type == "equation"
    )


def build_display_blocks_for_traversal_node(
    reader: StandardsReader,
    task: Task,
    node_id: str,
    node_type: str,
    *,
    planning: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Dispatch a planner-activated node to the appropriate center-panel block builder."""
    node_id = str(node_id or "").strip()
    node_type = str(node_type or "").strip().lower()
    if not node_id or node_type in _SKIP_TRAVERSAL_NODE_TYPES:
        return []

    if node_type in _PARAGRAPH_NODE_TYPES:
        if node_type == "definition":
            return build_activated_node_blocks(reader, node_id)
        block = build_paragraph_display_block(
            reader,
            node_id,
            display_role=DisplayRole.paragraph_context.value,
            task_outputs=task.outputs if isinstance(task.outputs, dict) else None,
        )
        return [block] if block is not None else []

    if node_type == "equation":
        from api.equation_display_registry import _definition_equation_upstream_prerequisites_met

        try:
            record = reader.load(node_id)
        except FileNotFoundError:
            return []
        execution_phase = str(record.metadata.get("execution_phase", "")).strip()
        if execution_phase == "definition" and not _definition_equation_upstream_prerequisites_met(
            task,
            reader,
            node_id,
        ):
            return []
        block = build_equation_evaluation_block(
            task,
            reader,
            node_id,
            attach_paragraph_context=True,
        )
        return [block] if block is not None else []

    # lookup / table / validation_rule — no dedicated scroll block in phase 1
    return []


def build_planner_traversal_display_blocks(
    task: Task,
    reader: StandardsReader,
    *,
    planning: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Emit center-panel blocks for every structural node in planner traversal."""
    plan = engineering_plan_for_task(task)
    nodes = collect_traversal_display_nodes(plan)
    resolved_planning = planning if isinstance(planning, dict) else {}

    blocks: list[dict[str, Any]] = []
    built_equation_ids: set[str] = set()

    for item in nodes:
        node_blocks = build_display_blocks_for_traversal_node(
            reader,
            task,
            item.node_id,
            item.node_type,
            planning=resolved_planning,
        )
        for block in node_blocks:
            if str(block.get("type") or "") == "equation":
                equation_node_id = str(block.get("equation_node_id") or "").strip()
                if equation_node_id:
                    built_equation_ids.add(equation_node_id)
        blocks.extend(node_blocks)

    from api.equation_display_registry import discover_equation_display_entries

    for equation_node_id, source_node_id in discover_equation_display_entries(
        task,
        reader,
        resolved_planning,
    ):
        if equation_node_id in built_equation_ids:
            continue
        block = build_equation_evaluation_block(
            task,
            reader,
            equation_node_id,
            attach_paragraph_context=True,
        )
        if block is not None and str(block.get("equation_node_id") or "") == equation_node_id:
            blocks.append(block)
            built_equation_ids.add(equation_node_id)

    return blocks
