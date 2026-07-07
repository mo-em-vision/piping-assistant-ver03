"""Load workflow navigation phase definitions from micro-graph workflow metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id
from engine.reference.standards_reader import StandardsReader
from models.planning import NavigationPhase


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


def _empty_navigation_config(workflow_id: str) -> WorkflowNavigationConfig:
    return WorkflowNavigationConfig(
        workflow_id=workflow_id,
        assumption_gate_fields=frozenset(),
        phase_order=(),
    )


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


def _navigation_from_workflow_node(
    reader: StandardsReader,
    workflow_id: str,
) -> WorkflowNavigationConfig | None:
    slug = normalize_root_id(workflow_id)
    resolved_id = resolve_workflow_node_id(slug)

    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    if micro is None:
        return None

    for candidate in (resolved_id, slug):
        node = micro.store.get_node(candidate)
        if node is None or node.node_type != "workflow":
            continue
        navigation = node.metadata.get("navigation")
        if isinstance(navigation, dict):
            return _parse_navigation_block(navigation, workflow_id=candidate)
    return None


def load_workflow_navigation(
    reader: StandardsReader,
    workflow_id: str,
) -> WorkflowNavigationConfig:
    """Resolve navigation config from workflow node metadata (runtime sidecar)."""
    config = _navigation_from_workflow_node(reader, workflow_id)
    if config is not None:
        return config
    slug = normalize_root_id(workflow_id)
    return _empty_navigation_config(slug)


def workflow_collection_field_order(
    reader: StandardsReader,
    workflow_id: str,
) -> tuple[str, ...]:
    """Phase-ordered field list from workflow navigation metadata (ordering only)."""
    config = load_workflow_navigation(reader, workflow_id)
    ordered: list[str] = []
    seen: set[str] = set()
    for _phase, fields in config.phase_order:
        for field in fields:
            if field not in seen:
                seen.add(field)
                ordered.append(field)
    return tuple(ordered)
