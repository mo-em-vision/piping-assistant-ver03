"""Workflow-scoped adapters for graph engine hooks.

Generic graph engine code shall not hardcode workflow-specific node ids or
branch field names. Workflow-specific compatibility lives here.
"""

from __future__ import annotations

from typing import Any

from engine.router import MAWP_DESIGN

# Legacy slug → compiled micro-graph workflow node id.
LEGACY_ROOT_ALIASES: dict[str, str] = {
    "pipe_wall_thickness_design": "B313-WF-PIPE-WALL-THICKNESS",
    "mawp_design": "B313-WF-MAWP",
    "B313-PIPE-WALL-THICKNESS-DESIGN": "B313-WF-PIPE-WALL-THICKNESS",
}

# Branch-driving task fields (paragraph applicability uses these).
PATH_DECISION_FIELDS: frozenset[str] = frozenset({"pressure_loading"})

# Parameters collected in the definition-equation completion phase.
DEFINITION_PHASE_INPUTS: frozenset[str] = frozenset({"corrosion_allowance"})


def resolve_workflow_node_id(root_ref: str, *, normalize) -> str:
    """Map legacy workflow slug to compiled workflow node id when applicable."""
    slug = normalize(root_ref)
    return LEGACY_ROOT_ALIASES.get(slug, slug)


def apply_workflow_planning_defaults(task: Any, workflow_id: str) -> None:
    """Apply workflow-specific and graph-driven defaults before expansion."""
    from engine.graph.resolution_branches import apply_resolution_branch_defaults

    apply_resolution_branch_defaults(task)

    if workflow_id != MAWP_DESIGN:
        return
    from engine.executor.mawp_geometry_resolver import apply_mawp_pressure_loading_default

    apply_mawp_pressure_loading_default(task)
