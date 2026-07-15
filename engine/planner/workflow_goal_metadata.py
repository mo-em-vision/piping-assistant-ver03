"""Load goal field classification from workflow node metadata and sidecars."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.graph.graph_engine import GraphEngine, normalize_root_id, resolve_workflow_node_id
from engine.reference.parameter_keys import param_node_id_for_input
from engine.reference.standards_reader import StandardsReader
from engine.reference.workflow_sidecar import _param_to_field


_DEFAULT_SELECTION_FIELDS = frozenset({"pressure_loading"})
_DEFAULT_LOOKUP_FIELDS = frozenset(
    {
        "allowable_stress",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
    }
)


@dataclass(frozen=True)
class RootGoalCompletionSpec:
    """Workflow completion criteria from goal_expansion.root_goal.completion."""

    when: str
    status: str


@dataclass(frozen=True)
class RootGoalSpec:
    """Root calculation goal identity resolved from workflow node metadata."""

    id: str
    key: str
    title: str
    target_parameter: str
    target_field: str
    completion: RootGoalCompletionSpec | None = None


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


def _root_goal_config(metadata: dict[str, Any]) -> dict[str, Any]:
    goal_expansion = metadata.get("goal_expansion") or {}
    if not isinstance(goal_expansion, dict):
        return {}
    root_goal = goal_expansion.get("root_goal") or {}
    return dict(root_goal) if isinstance(root_goal, dict) else {}


def _workflow_title(metadata: dict[str, Any], *, workflow_id: str) -> str:
    for key in ("title", "name", "purpose"):
        value = str(metadata.get(key) or "").strip()
        if value:
            return value
    description = str(metadata.get("description") or "").strip()
    if description:
        return description.splitlines()[0].strip()
    documentation = metadata.get("documentation") or {}
    if isinstance(documentation, dict):
        summary = str(documentation.get("summary") or "").strip()
        if summary:
            return summary.splitlines()[0].strip()
    return workflow_id.replace("_", " ")


def _derive_goal_key(target_field: str) -> str:
    return f"calculate-{target_field.replace('_', '-')}"


def _derive_goal_id(key: str) -> str:
    return f"GOAL-{key}"


def _parse_completion_spec(root_goal_cfg: dict[str, Any]) -> RootGoalCompletionSpec | None:
    completion = root_goal_cfg.get("completion")
    if not isinstance(completion, dict):
        return None
    when = str(completion.get("when") or "").strip()
    status = str(completion.get("status") or "").strip()
    if not when and not status:
        return None
    return RootGoalCompletionSpec(when=when, status=status)


def resolve_root_goal_spec(
    reader: StandardsReader,
    workflow_id: str,
    *,
    fallback_target_field: str = "required_wall_thickness",
) -> RootGoalSpec:
    """Resolve root goal id/key/title/target from workflow node metadata."""
    metadata = _workflow_node_metadata(reader, workflow_id)
    root_goal_cfg = _root_goal_config(metadata)

    target_param = str(root_goal_cfg.get("target_parameter") or "").strip()
    if target_param:
        target_field = _param_to_field(target_param)
        target_parameter = (
            target_param if target_param.startswith("PARAM-") else param_node_id_for_input(target_field)
        )
    else:
        goal_output = metadata.get("goal_output")
        if goal_output:
            target_field = _param_to_field(str(goal_output))
        else:
            target_field = fallback_target_field.replace("-", "_")
        target_parameter = param_node_id_for_input(target_field)

    key = str(root_goal_cfg.get("key") or "").strip() or _derive_goal_key(target_field)
    goal_id = str(root_goal_cfg.get("id") or "").strip() or _derive_goal_id(key)
    title = (
        str(root_goal_cfg.get("title") or root_goal_cfg.get("name") or "").strip()
        or _workflow_title(metadata, workflow_id=workflow_id)
    )

    return RootGoalSpec(
        id=goal_id,
        key=key,
        title=title,
        target_parameter=target_parameter,
        target_field=target_field,
        completion=_parse_completion_spec(root_goal_cfg),
    )


def workflow_title_for_goal(reader: StandardsReader, workflow_id: str) -> str:
    """Human-readable workflow title for root goal naming."""
    metadata = _workflow_node_metadata(reader, workflow_id)
    return _workflow_title(metadata, workflow_id=workflow_id)


def workflow_display_title_from_node(reader: StandardsReader, workflow_id: str) -> str:
    """User-facing workflow title from workflow node metadata only."""
    metadata = _workflow_node_metadata(reader, workflow_id)
    for key in ("title", "name"):
        value = str(metadata.get(key) or "").strip()
        if value:
            return value
    return ""


def workflow_display_description_from_node(reader: StandardsReader, workflow_id: str) -> str:
    """User-facing workflow description from workflow node ``description`` field only."""
    metadata = _workflow_node_metadata(reader, workflow_id)
    return str(metadata.get("description") or "").strip()


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
    spec = resolve_root_goal_spec(
        reader,
        workflow_id,
        fallback_target_field=fallback.replace("-", "_"),
    )
    return spec.target_field
