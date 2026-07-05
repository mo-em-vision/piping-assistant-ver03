"""Load goal field classification from workflow node metadata and sidecars."""

from __future__ import annotations

from typing import Any

from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id
from engine.reference.standards_reader import StandardsReader
from engine.reference.workflow_sidecar import _param_to_field

_DEFAULT_SELECTION_FIELDS = frozenset({"pressure_loading", "geometry_input_mode", "d_input_mode"})
_DEFAULT_LOOKUP_FIELDS = frozenset(
    {
        "allowable_stress",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
    }
)


def _workflow_node_metadata(reader: StandardsReader, workflow_id: str) -> dict[str, Any]:
    slug = normalize_root_id(workflow_id)
    resolved_id = resolve_workflow_node_id(slug)
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    if micro is None:
        return {}
    for candidate in (resolved_id, slug):
        node = micro.store.get_node(candidate)
        if node is not None and node.node_type == "workflow":
            metadata = node.metadata
            return metadata if isinstance(metadata, dict) else {}
    return {}


def selection_fields_for_workflow(reader: StandardsReader, workflow_id: str) -> frozenset[str]:
    metadata = _workflow_node_metadata(reader, workflow_id)
    fields = set(_DEFAULT_SELECTION_FIELDS)
    for item in metadata.get("interactions") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("mode") or "") == "decision" and item.get("variable"):
            fields.add(str(item["variable"]))
    goal_expansion = metadata.get("goal_expansion") or {}
    if isinstance(goal_expansion, dict):
        for tmpl in goal_expansion.get("child_goal_templates") or []:
            if not isinstance(tmpl, dict):
                continue
            if str(tmpl.get("goal_class") or "") == "selection_goal":
                param = tmpl.get("target_parameter")
                if param:
                    fields.add(_param_to_field(str(param)))
    return frozenset(fields)


def lookup_fields_for_workflow(reader: StandardsReader, workflow_id: str) -> frozenset[str]:
    metadata = _workflow_node_metadata(reader, workflow_id)
    fields = set(_DEFAULT_LOOKUP_FIELDS)
    goal_expansion = metadata.get("goal_expansion") or {}
    if isinstance(goal_expansion, dict):
        for tmpl in goal_expansion.get("child_goal_templates") or []:
            if not isinstance(tmpl, dict):
                continue
            if str(tmpl.get("goal_class") or "") == "lookup_goal":
                param = tmpl.get("target_parameter")
                if param:
                    fields.add(_param_to_field(str(param)))
    return frozenset(fields)


def root_target_for_workflow(
    reader: StandardsReader,
    workflow_id: str,
    *,
    fallback: str,
) -> str:
    metadata = _workflow_node_metadata(reader, workflow_id)
    goal_expansion = metadata.get("goal_expansion") or {}
    if isinstance(goal_expansion, dict):
        root_goal = goal_expansion.get("root_goal") or {}
        if isinstance(root_goal, dict):
            target = root_goal.get("target_parameter")
            if target:
                return _param_to_field(str(target))
    goal_output = metadata.get("goal_output")
    if goal_output:
        return _param_to_field(str(goal_output))
    return fallback
