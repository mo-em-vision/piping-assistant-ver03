"""Constants and helpers for workflow expansion projection JSON."""

from __future__ import annotations

from models.planning import NavigationPhase

PIPE_WALL_WORKFLOWS = frozenset(
    {
        "pipe_wall_thickness_design",
        "B313-PIPE-WALL-THICKNESS-DESIGN",
        "B313-WF-PIPE-WALL-THICKNESS",
        "WF-PIPE-WALL-THICKNESS",
    }
)

INTERNAL_PRESSURE_BRANCH = "304.1.2-a"
EXTERNAL_PRESSURE_BRANCH = "304.1.3"
WORKFLOW_ROOT = "WF-PIPE-WALL-THICKNESS"

PIPE_WALL_TIMELINE_PHASES: tuple[str, ...] = (
    NavigationPhase.EXPANSION_ASSUMPTIONS.value,
    NavigationPhase.PATH_DECISIONS.value,
    NavigationPhase.PARAMETER_GATHERING.value,
    NavigationPhase.COEFFICIENT_RESOLUTION.value,
    NavigationPhase.EXECUTION_ASSUMPTIONS.value,
)

PIPE_WALL_PHASE_FIELDS: dict[str, tuple[str, ...]] = {
    NavigationPhase.EXPANSION_ASSUMPTIONS.value: ("straight_pipe_section",),
    NavigationPhase.PATH_DECISIONS.value: ("pressure_loading",),
    NavigationPhase.PARAMETER_GATHERING.value: (
        "design_pressure",
        "nominal_pipe_size",
        "outside_diameter",
        "material",
        "design_temperature",
    ),
    NavigationPhase.COEFFICIENT_RESOLUTION.value: (
        "joint_category",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
    ),
    NavigationPhase.EXECUTION_ASSUMPTIONS.value: (),
    NavigationPhase.DEFINITION_EQUATION_COMPLETION.value: ("corrosion_allowance",),
}

NODE_STATUSES = frozenset(
    {
        "hidden",
        "preview",
        "awaiting_expansion_assumption",
        "awaiting_decision",
        "pending_condition",
        "expanded",
        "active",
        "awaiting_input",
        "blocked",
        "ready",
        "executed",
        "skipped",
        "failed",
        "invalidated",
        "unknown",
    }
)

EDGE_TYPES = frozenset(
    {
        "active",
        "inactive",
        "conditional",
        "skipped",
        "blocked",
        "reference",
        "dependency",
    }
)

TIMELINE_ITEM_STATUSES = frozenset(
    {"missing", "current", "confirmed", "skipped", "not_reached"}
)

DEPENDENCY_EDGE_TYPES = frozenset(
    {
        "requires",
        "uses",
        "depends_on",
        "uses_table",
        "accepts",
        "requires_parameter",
        "implements",
        "calculates",
        "outputs",
        "defines",
        "derived_from",
        "next",
        "next_step",
    }
)

REFERENCE_EDGE_TYPES = frozenset(
    {
        "related_to",
        "references",
        "contains",
        "contains_paragraph",
        "starts_from_paragraph",
        "may_use_equation",
        "located_in",
        "anchors_to",
    }
)
