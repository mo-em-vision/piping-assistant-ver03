"""Build centralized engineering_plan.dependencies from requirement templates."""

from __future__ import annotations

from engine.planner.graph_requirements import (
    _DIAMETER_RESOLUTION_ID,
    lookup_requirement_id,
    requirement_id,
)
from models.engineering_plan import PlanDependency, PlanRequirement


def build_plan_dependencies(
    requirements: dict[str, PlanRequirement],
    *,
    workflow_id: str,
) -> list[PlanDependency]:
    """Derive plan dependency edges from requirements and alternative structure."""
    del workflow_id
    edges = _edges_from_depends_on(requirements)
    edges.extend(_alternative_structural_edges(requirements))
    return _dedupe_edges(edges)


def _infer_dependency_type(source: PlanRequirement, target: PlanRequirement) -> str:
    if target.requirement_class == "report_output":
        return "requires"
    if target.requirement_class == "equation_result":
        return "equation_input"
    if target.requirement_class == "table_lookup":
        return "lookup_input"
    return "requires"


def _lookup_requirement_for_field(
    requirements: dict[str, PlanRequirement],
    field: str,
) -> str | None:
    lookup_id = lookup_requirement_id(field)
    if lookup_id in requirements:
        return lookup_id
    for req in requirements.values():
        if req.requirement_class == "table_lookup" and req.field == field:
            return req.id
    return None


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


def _alternative_structural_edges(
    requirements: dict[str, PlanRequirement],
) -> list[PlanDependency]:
    edges: list[PlanDependency] = []
    for req in requirements.values():
        for alt in req.alternatives or []:
            for field in alt.fields:
                target_id = requirement_id(field)
                if target_id in requirements:
                    edges.append(
                        PlanDependency(from_id=alt.id, to_id=target_id, type="activates")
                    )
            if alt.method != "lookup" or not alt.resolves:
                continue
            lookup_id = _lookup_requirement_for_field(requirements, alt.resolves)
            if lookup_id is not None:
                edges.append(
                    PlanDependency(
                        from_id=lookup_id,
                        to_id=req.id,
                        type="resolves",
                    )
                )

    if (
        _lookup_requirement_for_field(requirements, "outside_diameter")
        == "REQ-outside_diameter_lookup"
        and _DIAMETER_RESOLUTION_ID in requirements
        and "REQ-outside_diameter_lookup" in requirements
    ):
        edges.append(
            PlanDependency(
                from_id="REQ-outside_diameter_lookup",
                to_id=_DIAMETER_RESOLUTION_ID,
                type="resolves",
            )
        )
    return edges


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
