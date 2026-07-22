"""Derive planner requirement collection order from graph expansion and dependencies."""

from __future__ import annotations

from dataclasses import dataclass

from engine.graph.graph_engine import GraphEngine
from engine.graph.param_priority import parameter_collection_priority
from engine.reference.standards_reader import StandardsReader
from models.engineering_plan import PlanRequirement


@dataclass(frozen=True)
class RequirementOrderContext:
    """Sort keys for planner requirement ordering within a navigation phase."""

    field_index: dict[str, int]
    dependency_depth: dict[str, int]
    graph_priority: dict[str, int]
    requirement_index: dict[str, int]


def _param_field(store, param_node_id: str) -> str:
    from engine.planner.graph_requirements import _param_field as graph_param_field

    return graph_param_field(store, param_node_id)


def _dependency_depths(requirements: dict[str, PlanRequirement]) -> dict[str, int]:
    depths: dict[str, int] = {}

    def depth(req_id: str, visiting: set[str]) -> int:
        cached = depths.get(req_id)
        if cached is not None:
            return cached
        if req_id in visiting:
            return 0
        visiting.add(req_id)
        req = requirements.get(req_id)
        if req is None or not req.depends_on:
            depths[req_id] = 0
            visiting.discard(req_id)
            return 0
        dep_depths = [
            depth(dep_id, visiting)
            for dep_id in req.depends_on
            if dep_id in requirements
        ]
        value = (max(dep_depths) + 1) if dep_depths else 0
        depths[req_id] = value
        visiting.discard(req_id)
        return value

    for req_id in requirements:
        depth(req_id, set())
    return depths


def _field_index_from_graph(
    reader: StandardsReader,
    execution_order: list[str],
    requirements: dict[str, PlanRequirement],
) -> dict[str, int]:
    gatherable_fields = {
        str(req.field).strip()
        for req in requirements.values()
        if req.requirement_class in {"user_input", "branch_decision"} and str(req.field).strip()
    }
    if not gatherable_fields:
        return {}

    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    if micro is None:
        return _field_index_from_requirements(requirements)

    store = micro.store
    active_nodes = set(execution_order)
    candidates: list[tuple[int, int, str]] = []
    seen_fields: set[str] = set()
    for exec_index, node_id in enumerate(execution_order):
        node = store.get_node(node_id)
        if node is None or node.node_type != "parameter":
            continue
        field = _param_field(store, node_id)
        if field not in gatherable_fields or field in seen_fields:
            continue
        seen_fields.add(field)
        graph_pri = parameter_collection_priority(store, node_id, active_nodes)
        candidates.append((graph_pri, exec_index, field))

    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    indexed = {field: seq for seq, (_, _, field) in enumerate(candidates)}

    seq = len(indexed)
    for req in requirements.values():
        field = str(req.field or "").strip()
        if field and field in gatherable_fields and field not in indexed:
            indexed[field] = seq
            seq += 1
    return indexed


def _field_index_from_requirements(
    requirements: dict[str, PlanRequirement],
) -> dict[str, int]:
    indexed: dict[str, int] = {}
    seq = 0
    for req in requirements.values():
        field = str(req.field or "").strip()
        if field and field not in indexed:
            indexed[field] = seq
            seq += 1
    return indexed


def _graph_priority_by_field(
    reader: StandardsReader,
    execution_order: list[str],
) -> dict[str, int]:
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    if micro is None or not execution_order:
        return {}

    store = micro.store
    active_nodes = set(execution_order)
    priorities: dict[str, int] = {}
    for node_id in execution_order:
        node = store.get_node(node_id)
        if node is None or node.node_type != "parameter":
            continue
        field = _param_field(store, node_id)
        if not field:
            continue
        priority = parameter_collection_priority(store, node_id, active_nodes)
        existing = priorities.get(field)
        if existing is None or priority < existing:
            priorities[field] = priority
    return priorities


def build_requirement_order_context(
    requirements: dict[str, PlanRequirement],
    *,
    reader: StandardsReader | None = None,
    execution_order: list[str] | None = None,
) -> RequirementOrderContext:
    """Build ordering context from graph expansion order and requirement dependencies."""
    execution_order = list(execution_order or [])
    field_index: dict[str, int] = {}
    graph_priority: dict[str, int] = {}

    if reader is not None:
        field_index = _field_index_from_graph(reader, execution_order, requirements)
        graph_priority = _graph_priority_by_field(reader, execution_order)

    if not field_index:
        field_index = _field_index_from_requirements(requirements)

    requirement_index = {
        req_id: index for index, req_id in enumerate(requirements.keys())
    }

    return RequirementOrderContext(
        field_index=field_index,
        dependency_depth=_dependency_depths(requirements),
        graph_priority=graph_priority,
        requirement_index=requirement_index,
    )


def requirement_sort_key(
    req_id: str,
    req: PlanRequirement,
    order_context: RequirementOrderContext | None,
    *,
    strategy_field_name: str | None = None,
) -> tuple:
    """Stable planner sort key: dependency depth, emission order, expansion order, graph priority."""
    field = strategy_field_name or req.field
    if order_context is None:
        priority = req.question_spec.priority if req.question_spec else 999
        return (priority, req_id)

    return (
        order_context.dependency_depth.get(req_id, 0),
        order_context.requirement_index.get(req_id, 9999),
        order_context.field_index.get(field, 9999),
        order_context.graph_priority.get(field, 100),
        req_id,
    )


def sync_question_spec_priorities(
    requirements: dict[str, PlanRequirement],
    order_context: RequirementOrderContext,
) -> None:
    """Mirror graph-derived order into question_spec.priority for inspector display."""
    for req_id, req in requirements.items():
        if req.question_spec is None:
            continue
        field = req.field
        expansion = order_context.field_index.get(field, 9999)
        depth = order_context.dependency_depth.get(req_id, 0)
        emission = order_context.requirement_index.get(req_id, 9999)
        graph_pri = order_context.graph_priority.get(field, 100)
        req.question_spec.priority = depth * 1_000_000 + emission * 1_000 + expansion * 10 + min(graph_pri, 9)
