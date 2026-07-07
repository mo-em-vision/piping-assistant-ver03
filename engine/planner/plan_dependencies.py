"""Build centralized engineering_plan.dependencies from requirement templates."""

from __future__ import annotations

from engine.planner.pipe_wall_plan import (
    PIPE_WALL_WORKFLOW,
    _ALT_NPS_LOOKUP,
    req_id,
)
from engine.router import PIPE_WALL_THICKNESS_DESIGN
from models.engineering_plan import PlanDependency, PlanRequirement

_PIPE_WALL_WORKFLOW_IDS = frozenset(
    {
        PIPE_WALL_WORKFLOW,
        PIPE_WALL_THICKNESS_DESIGN,
        "pipe-wall-thickness",
        "B313-PIPE-WALL-THICKNESS-DESIGN",
    }
)

_PIPE_WALL_STRUCTURAL_EDGES: tuple[tuple[str, str, str], ...] = (
    ("REQ-outside_diameter_lookup", "REQ-diameter_resolution", "resolves"),
    (_ALT_NPS_LOOKUP, req_id("nominal_pipe_size"), "activates"),
)


def build_plan_dependencies(
    requirements: dict[str, PlanRequirement],
    *,
    workflow_id: str,
) -> list[PlanDependency]:
    """Derive plan dependency edges from requirements and workflow-specific structure."""
    normalized = str(workflow_id or "").strip()
    if normalized in _PIPE_WALL_WORKFLOW_IDS or normalized.replace("-", "_") in {
        PIPE_WALL_WORKFLOW,
        PIPE_WALL_THICKNESS_DESIGN.replace("-", "_"),
    }:
        return _build_pipe_wall_plan_dependencies(requirements)
    return []


def _infer_dependency_type(source: PlanRequirement, target: PlanRequirement) -> str:
    if target.requirement_class == "report_output":
        return "requires"
    if target.requirement_class == "equation_result":
        return "equation_input"
    if target.requirement_class == "table_lookup":
        return "lookup_input"
    return "requires"


def _edges_from_depends_on(requirements: dict[str, PlanRequirement]) -> list[PlanDependency]:
    edges: list[PlanDependency] = []
    for target in requirements.values():
        for dep_id in target.depends_on:
            source = requirements.get(dep_id)
            if source is None:
                continue
            edges.append(
                PlanDependency(
                    from_id=dep_id,
                    to_id=target.id,
                    type=_infer_dependency_type(source, target),
                )
            )
    return edges


def _structural_edges(
    templates: tuple[tuple[str, str, str], ...],
) -> list[PlanDependency]:
    return [
        PlanDependency(from_id=from_id, to_id=to_id, type=edge_type)
        for from_id, to_id, edge_type in templates
    ]


def _dedupe_edges(edges: list[PlanDependency]) -> list[PlanDependency]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[PlanDependency] = []
    for edge in edges:
        key = (edge.from_id, edge.to_id, edge.type)
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)
    return unique


def _build_pipe_wall_plan_dependencies(
    requirements: dict[str, PlanRequirement],
) -> list[PlanDependency]:
    edges = _edges_from_depends_on(requirements)
    edges.extend(_structural_edges(_PIPE_WALL_STRUCTURAL_EDGES))
    return _dedupe_edges(edges)
