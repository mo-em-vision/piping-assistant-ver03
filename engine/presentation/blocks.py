"""Canonical presentation block builders."""

from __future__ import annotations

from typing import Any

from models.node_documentation import NodeDocumentation
from models.workflow_lifecycle import WorkflowLifecycleEventType
from models.workflow_state import WorkflowParameter, WorkflowState

_WORKFLOW_ROOT_ALIASES: dict[str, str] = {
    "pipe_wall_thickness_design": "B313-WF-PIPE-WALL-THICKNESS",
    "mawp_design": "B313-WF-MAWP",
    "B313-PIPE-WALL-THICKNESS-DESIGN": "B313-WF-PIPE-WALL-THICKNESS",
}

_PENDING_PARAMETER_STATUSES = frozenset({"pending", "proposed_default"})


def paragraph_block(
    node_id: str,
    role: str,
    text: str,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    return {
        "type": "paragraph",
        "node_id": node_id,
        "role": role,
        "title": title,
        "text": text.strip(),
    }


def warning_block(message: str, *, index: int = 0) -> dict[str, Any]:
    return {
        "type": "warning",
        "warning_id": f"warning-{index}",
        "text": message.strip(),
    }


def parameter_request_block(param: WorkflowParameter) -> dict[str, Any]:
    return {
        "type": "parameter_request",
        "parameter_id": param.name,
        "param_node_id": param.param_node_id,
        "symbol": param.symbol,
        "name": param.name,
        "dimension": param.dimension,
        "unit": param.unit,
        "canonical_unit": param.canonical_unit,
        "allowed_units": list(param.allowed_units),
        "status": param.status,
        "value": param.value,
    }


def lookup_result_block(lookup_id: str, value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "type": "lookup_result",
            "lookup_id": lookup_id,
            "table": value.get("table"),
            "value": value.get("value"),
            "unit": value.get("unit"),
            "raw": value,
        }
    return {
        "type": "lookup_result",
        "lookup_id": lookup_id,
        "value": value,
    }


def _doc_text(doc: NodeDocumentation, *fields: str) -> str:
    for field in fields:
        value = getattr(doc, field, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def resolve_workflow_root_id(workflow_id: str, store) -> str | None:
    slug = workflow_id.strip()
    if not slug:
        return None
    resolved = _WORKFLOW_ROOT_ALIASES.get(slug, slug)
    if store.get_node(resolved) is not None:
        return resolved
    return None


def render_workflow_documentation(
    workflow_state: WorkflowState,
    store,
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    rendered_nodes: set[str] = set()

    root_id = resolve_workflow_root_id(workflow_state.workflow_id, store)
    if root_id and root_id in workflow_state.node_documentation:
        doc = workflow_state.node_documentation[root_id]
        body = _doc_text(doc, "summary", "description", "before_enter")
        if body:
            blocks.append(
                paragraph_block(
                    root_id,
                    "workflow_doc",
                    body,
                    title=_doc_text(doc, "title") or None,
                )
            )
            rendered_nodes.add(root_id)

    if workflow_state.current_documentation and workflow_state.current_node:
        node_id = workflow_state.current_node
        if node_id not in rendered_nodes:
            doc = workflow_state.current_documentation
            body = _doc_text(doc, "description", "instructions", "summary", "before_enter")
            if body:
                blocks.append(
                    paragraph_block(
                        node_id,
                        "current_step",
                        body,
                        title=_doc_text(doc, "title") or None,
                    )
                )
                rendered_nodes.add(node_id)

    return blocks


def render_lifecycle_context(workflow_state: WorkflowState) -> list[dict[str, Any]]:
    current = workflow_state.current_node
    if not current:
        return []

    for event in reversed(workflow_state.execution_events):
        if (
            event.node_id == current
            and event.event == WorkflowLifecycleEventType.BEFORE_ENTER
            and event.message.strip()
        ):
            return [
                paragraph_block(
                    current,
                    "before_enter",
                    event.message,
                )
            ]
    return []


def render_parameter_requests(workflow_state: WorkflowState) -> list[dict[str, Any]]:
    ordered = sorted(
        workflow_state.parameters.items(),
        key=lambda item: (item[1].priority, item[0]),
    )
    blocks: list[dict[str, Any]] = []
    for _name, param in ordered:
        if param.status not in _PENDING_PARAMETER_STATUSES:
            continue
        if param.value is not None and param.status != "proposed_default":
            continue
        blocks.append(parameter_request_block(param))
    return blocks


def render_warnings(workflow_state: WorkflowState) -> list[dict[str, Any]]:
    return [
        warning_block(message, index=index)
        for index, message in enumerate(workflow_state.warnings)
    ]


def render_lookup_results(workflow_state: WorkflowState) -> list[dict[str, Any]]:
    return [
        lookup_result_block(lookup_id, value)
        for lookup_id, value in sorted(workflow_state.lookup_results.items())
    ]


def _equation_result_from_history(history_entry: dict[str, Any]) -> dict[str, Any] | None:
    if history_entry.get("status") != "completed":
        return None
    node_result = history_entry.get("result")
    if not isinstance(node_result, dict):
        return None
    trace = node_result.get("trace")
    if not isinstance(trace, dict):
        trace = {}
    outputs = node_result.get("outputs")
    if not isinstance(outputs, dict):
        outputs = {}
    if not trace and not outputs:
        return None
    payload: dict[str, Any] = {
        "substitution": trace.get("substitution"),
        "result": trace.get("result_text"),
        "outputs": outputs,
    }
    render_steps = trace.get("render_steps")
    if isinstance(render_steps, dict) and render_steps:
        payload["render_steps"] = render_steps
    equation_display_trace = trace.get("equation_display_trace")
    if isinstance(equation_display_trace, dict) and equation_display_trace:
        payload["equation_display_trace"] = equation_display_trace
    return payload


def render_equation_blocks(
    workflow_state: WorkflowState,
    store,
    inputs: dict,
) -> list[dict[str, Any]]:
    from engine.graph.display_emitter import emit_equation_blocks

    history_by_node = {
        str(entry.get("node_id", "")): entry
        for entry in workflow_state.history
        if entry.get("node_id")
    }

    node_ids: list[str] = list(workflow_state.visited_nodes)
    if workflow_state.current_node and workflow_state.current_node not in node_ids:
        node_ids.append(workflow_state.current_node)

    blocks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node_id in node_ids:
        if node_id in seen:
            continue
        if store.node_type(node_id) != "equation":
            continue
        seen.add(node_id)
        history_entry = history_by_node.get(node_id, {})
        result = _equation_result_from_history(history_entry)
        blocks.extend(
            emit_equation_blocks(
                store,
                node_id,
                inputs,
                result=result,
            )
        )
    return blocks
