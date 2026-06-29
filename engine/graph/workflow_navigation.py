"""Load workflow navigation phase definitions from micro-graph workflow metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id
from engine.reference.standards_reader import StandardsReader
from models.planning import NavigationPhase

_LEGACY_SLUG_ALIASES = {
    "pipe_wall_thickness_design": "B313-WF-PIPE-WALL-THICKNESS",
    "mawp_design": "B313-WF-MAWP",
}

_PIPE_WALL_NAVIGATION: dict[str, Any] = {
    "assumption_gate_fields": ["straight_pipe_section", "pressure_loading"],
    "phases": {
        NavigationPhase.EXPANSION_ASSUMPTIONS.value: ["straight_pipe_section"],
        NavigationPhase.PATH_DECISIONS.value: ["pressure_loading"],
        NavigationPhase.PARAMETER_GATHERING.value: [
            "design_pressure",
            "nominal_pipe_size",
            "outside_diameter",
            "material",
            "design_temperature",
            "external_design_pressure",
        ],
        NavigationPhase.COEFFICIENT_RESOLUTION.value: [
            "joint_category",
            "weld_joint_efficiency",
            "weld_strength_reduction",
            "temperature_coefficient",
        ],
        NavigationPhase.EXECUTION_ASSUMPTIONS.value: [],
        NavigationPhase.DEFINITION_EQUATION_COMPLETION.value: ["corrosion_allowance"],
    },
}

_MAWP_NAVIGATION: dict[str, Any] = {
    "assumption_gate_fields": ["straight_pipe_section", "geometry_input_mode"],
    "phases": {
        NavigationPhase.EXPANSION_ASSUMPTIONS.value: ["straight_pipe_section"],
        NavigationPhase.PATH_DECISIONS.value: ["geometry_input_mode"],
        NavigationPhase.PARAMETER_GATHERING.value: [
            "nominal_pipe_size",
            "pipe_schedule",
            "outside_diameter",
            "actual_wall_thickness",
            "corrosion_allowance",
            "material",
            "design_temperature",
        ],
        NavigationPhase.COEFFICIENT_RESOLUTION.value: [
            "joint_category",
            "weld_joint_efficiency",
            "weld_strength_reduction",
            "temperature_coefficient",
        ],
        NavigationPhase.EXECUTION_ASSUMPTIONS.value: [],
        NavigationPhase.DEFINITION_EQUATION_COMPLETION.value: [],
    },
}

_DEFAULT_BY_SLUG: dict[str, dict[str, Any]] = {
    "pipe_wall_thickness_design": _PIPE_WALL_NAVIGATION,
    "B313-PIPE-WALL-THICKNESS-DESIGN": _PIPE_WALL_NAVIGATION,
    "B313-WF-PIPE-WALL-THICKNESS": _PIPE_WALL_NAVIGATION,
    "mawp_design": _MAWP_NAVIGATION,
    "B313-WF-MAWP": _MAWP_NAVIGATION,
}


@dataclass(frozen=True)
class WorkflowNavigationConfig:
    """Declarative field ordering for phased parameter gathering."""

    workflow_id: str
    assumption_gate_fields: frozenset[str]
    phase_order: tuple[tuple[NavigationPhase, tuple[str, ...]], ...]

    def fields_for_phase(self, phase: NavigationPhase) -> frozenset[str]:
        for nav_phase, fields in self.phase_order:
            if nav_phase == phase:
                return frozenset(fields)
        return frozenset()

    def ordered_fields_for_phase(self, phase: NavigationPhase) -> tuple[str, ...]:
        for nav_phase, fields in self.phase_order:
            if nav_phase == phase:
                return fields
        return ()

    def phase_allowlists(self) -> dict[str, list[str]]:
        return {phase.value: list(fields) for phase, fields in self.phase_order}


def _parse_navigation_block(raw: dict[str, Any], *, workflow_id: str) -> WorkflowNavigationConfig:
    gate_fields = raw.get("assumption_gate_fields") or []
    assumption_gate_fields = frozenset(str(item) for item in gate_fields if str(item).strip())

    phases_raw = raw.get("phases") or {}
    phase_order: list[tuple[NavigationPhase, tuple[str, ...]]] = []
    for phase in NavigationPhase:
        if phase == NavigationPhase.READY:
            continue
        entries = phases_raw.get(phase.value)
        if entries is None:
            continue
        if not isinstance(entries, list):
            continue
        fields = tuple(str(item) for item in entries if str(item).strip())
        phase_order.append((phase, fields))

    return WorkflowNavigationConfig(
        workflow_id=workflow_id,
        assumption_gate_fields=assumption_gate_fields,
        phase_order=tuple(phase_order),
    )


def _config_from_defaults(slug: str) -> WorkflowNavigationConfig | None:
    raw = _DEFAULT_BY_SLUG.get(slug)
    if raw is None:
        return None
    return _parse_navigation_block(raw, workflow_id=slug)


def load_workflow_navigation(
    reader: StandardsReader,
    workflow_id: str,
) -> WorkflowNavigationConfig:
    """Resolve navigation config from workflow node metadata or built-in defaults."""
    slug = normalize_root_id(workflow_id)
    resolved_id = resolve_workflow_node_id(slug)

    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    if micro is not None:
        for candidate in (resolved_id, slug):
            node = micro.store.get_node(candidate)
            if node is None or node.node_type != "workflow":
                continue
            navigation = node.metadata.get("navigation")
            if isinstance(navigation, dict):
                return _parse_navigation_block(navigation, workflow_id=candidate)

    fallback = _config_from_defaults(slug) or _config_from_defaults(resolved_id)
    if fallback is not None:
        return fallback

    return _parse_navigation_block(_PIPE_WALL_NAVIGATION, workflow_id=slug)
