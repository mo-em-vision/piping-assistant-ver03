"""Build compact node provenance payloads for dev-mode UI tooltips."""

from __future__ import annotations

from typing import Any

from api.node_context import display_heading_source_field, hover_excerpt_for_node
from engine.reference.paragraph_hierarchy import paragraph_reference
from api.workflow_bootstrap import resolve_activated_definition_node
from engine.messaging.parameter_input_prompt import build_parameter_input_prompt, interaction_for_parameter
from engine.reference.standards_reader import StandardsReader
from engine.state.workflow_parameters import _param_nodes_by_input_id, _resolve_active_nodes
from models.task import Task

_DEFAULT_STANDARD_LABEL = "ASME B31.3"

_CALCULATION_STEP_IDS = frozenset({"thickness", "mawp"})


def provenance_for_node(
    reader: StandardsReader,
    node_id: str,
    *,
    source_field: str | None = None,
) -> dict[str, Any] | None:
    """Return compact provenance for a standards graph node, or None if not found."""
    try:
        record = reader.load(str(node_id))
    except FileNotFoundError:
        return None

    metadata = record.metadata
    paragraph = paragraph_reference(metadata) or None
    title = str(metadata.get("title", "")).strip() or None
    excerpt = hover_excerpt_for_node(record)
    if not excerpt:
        purpose = str(metadata.get("purpose", "")).strip()
        excerpt = purpose or title or record.node_id

    payload: dict[str, Any] = {
        "node_id": record.node_id,
        "title": title,
        "standard": _DEFAULT_STANDARD_LABEL,
        "paragraph": paragraph,
        "paragraph_number": paragraph,
        "hover_excerpt": excerpt,
    }
    if source_field:
        payload["source_field"] = source_field

    upstream, downstream = _graph_neighbors(reader, node_id)
    if upstream:
        payload["generated_by"] = upstream[0]
    if downstream:
        payload["consumed_by"] = downstream
    return payload


def _graph_neighbors(reader: StandardsReader, node_id: str) -> tuple[list[str], list[str]]:
    store = reader.graph_store
    if not store.available:
        return [], []
    store.load()
    upstream = [edge.from_id for edge in store.incoming(node_id)]
    downstream = [edge.to_id for edge in store.outgoing(node_id)]
    return upstream, downstream


def attach_provenance(
    block: dict[str, Any],
    reader: StandardsReader,
    node_id: str | None,
    *,
    source_field: str | None = None,
) -> dict[str, Any]:
    if not node_id or block.get("provenance"):
        return block
    resolved_field = source_field or _source_field_for_block(block)
    if resolved_field in {None, "purpose"}:
        try:
            resolved_field = display_heading_source_field(reader.load(str(node_id)).metadata)
        except FileNotFoundError:
            resolved_field = resolved_field or "title"
    provenance = provenance_for_node(reader, node_id, source_field=resolved_field)
    if provenance:
        block["provenance"] = provenance
    return block


def _source_field_for_block(block: dict[str, Any]) -> str | None:
    block_type = str(block.get("type") or "")
    block_id = str(block.get("id", ""))

    if block_id.startswith("node-activation-assumptions-"):
        return "assumptions"
    if block_type == "equation":
        if block.get("display"):
            return "display_latex"
        return "sympy"
    if block_type == "reference":
        return "purpose"
    if block_type == "result":
        return "title"
    if block_type == "text":
        if block.get("variant") == "assumption":
            return "assumptions"
        return "body"
    if block_type == "table":
        return "title"
    if block_type == "graph":
        return "title"
    return None


def _node_id_from_block(block: dict[str, Any]) -> str | None:
    source_node = block.get("source_node")
    if source_node:
        return str(source_node)

    nomenclature = block.get("nomenclature_reference")
    if isinstance(nomenclature, dict) and nomenclature.get("node_id"):
        return str(nomenclature["node_id"])

    reference_links = block.get("reference_links")
    if isinstance(reference_links, list) and reference_links:
        first = reference_links[0]
        if isinstance(first, dict) and first.get("node_id"):
            return str(first["node_id"])

    block_id = str(block.get("id", ""))
    prefixes = (
        "node-activation-assumptions-",
        "node-activation-equation-",
        "path-preview-equation-",
        "path-preview-intro-",
        "equation-",
        "reference-",
        "table-steps-",
        "table-intermediates-",
    )
    for prefix in prefixes:
        if block_id.startswith(prefix):
            return block_id[len(prefix) :]

    if block_id in {"mawp-pressure-design-equation", "mawp-formula-equation", "mawp-substituted-equation"}:
        return "B313-MAWP-CALCULATION"
    if block_id == "mawp-conclusion":
        return "B313-MAWP-CALCULATION"

    return None


def enrich_display_blocks_provenance(
    blocks: list[dict[str, Any]],
    reader: StandardsReader,
    *,
    default_node_id: str | None = None,
) -> None:
    """Attach provenance to display output blocks in place when a source node can be resolved."""
    for block in blocks:
        if block.get("provenance"):
            continue
        node_id = _node_id_from_block(block)
        if not node_id and default_node_id and block.get("type") == "result":
            node_id = default_node_id
        attach_provenance(block, reader, node_id)


def param_node_index(reader: StandardsReader, task: Task) -> dict[str, str]:
    store = reader.graph_store
    if not store.available:
        return {}
    active = _resolve_active_nodes(task, None)
    return _param_nodes_by_input_id(store, active)


def parameter_input_provenance(
    reader: StandardsReader,
    task: Task,
    parameter_id: str,
) -> dict[str, Any] | None:
    """Provenance for a workflow parameter prompt (interaction, param node, or equation)."""
    from engine.messaging.decision_interaction_resolver import (
        is_node_owned_decision_key,
        resolve_decision_interaction,
    )
    from engine.graph.resolution_branches import resolution_branch_fact_key

    canonical = parameter_id
    decision_key = canonical
    if is_node_owned_decision_key(canonical):
        decision_key = canonical
    elif canonical == "outside_diameter":
        decision_key = resolution_branch_fact_key("outside_diameter")

    if is_node_owned_decision_key(decision_key):
        view = resolve_decision_interaction(reader, task, decision_key)
        if view is not None:
            source_field = (
                "metadata.resolution_branches"
                if view.requesting_node_id.startswith("PARAM-")
                else "execution.interactions"
            )
            provenance = provenance_for_node(
                reader,
                view.requesting_node_id,
                source_field=source_field,
            )
            if provenance:
                return provenance

    spec = interaction_for_parameter(reader, task, parameter_id)
    if spec is not None:
        provenance = provenance_for_node(reader, spec.node_id, source_field="user_prompt.prompt")
        if provenance:
            return provenance

    param_index = param_node_index(reader, task)
    param_node_id = param_index.get(parameter_id)
    if param_node_id:
        prompt = build_parameter_input_prompt(reader, task, parameter_id)
        source_field = "user_prompt.prompt" if prompt else "title"
        provenance = provenance_for_node(reader, param_node_id, source_field=source_field)
        if provenance:
            return provenance

    definition_id = definition_node_id_for_task(task, reader, None)
    if definition_id:
        try:
            source_field = display_heading_source_field(reader.load(definition_id).metadata)
        except FileNotFoundError:
            source_field = "title"
        provenance = provenance_for_node(reader, definition_id, source_field=source_field)
        if provenance:
            return provenance

    return None


def definition_node_id_for_task(
    task: Task,
    reader: StandardsReader,
    planning: dict[str, Any] | None = None,
) -> str | None:
    planning = planning if isinstance(planning, dict) else {}
    node_id = planning.get("active_definition_node")
    if node_id:
        return str(node_id)

    workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
    if workflow_id:
        resolved = resolve_activated_definition_node(reader, workflow_id)
        if resolved:
            return resolved

    for candidate in task.active_nodes:
        try:
            if str(reader.load(candidate).metadata.get("type", "")) == "definition":
                return candidate
        except FileNotFoundError:
            continue
    return None


def step_provenance(
    reader: StandardsReader,
    task: Task,
    step_id: str,
    planning: dict[str, Any] | None = None,
    *,
    for_display_value: bool = False,
) -> dict[str, Any] | None:
    planning = planning if isinstance(planning, dict) else {}

    if step_id in _CALCULATION_STEP_IDS:
        definition_id = definition_node_id_for_task(task, reader, planning)
        if definition_id:
            try:
                source_field = display_heading_source_field(reader.load(definition_id).metadata)
            except FileNotFoundError:
                source_field = "title"
            return provenance_for_node(reader, definition_id, source_field=source_field)
        return None

    param_index = param_node_index(reader, task)
    param_node_id = param_index.get(step_id)
    if param_node_id:
        source_field = "input_id" if for_display_value else "title"
        return provenance_for_node(reader, param_node_id, source_field=source_field)

    return None


def provenance_from_active_context(active_context: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(active_context, dict):
        return None
    node_id = str(active_context.get("node_id") or "").strip()
    if not node_id:
        return None
    excerpt = str(active_context.get("hover_excerpt") or "").strip()
    if not excerpt:
        return None
    payload: dict[str, Any] = {
        "node_id": node_id,
        "title": None,
        "standard": active_context.get("standard"),
        "paragraph": active_context.get("paragraph"),
        "hover_excerpt": excerpt,
    }
    source_field = active_context.get("source_field")
    if source_field:
        payload["source_field"] = source_field
    return payload
