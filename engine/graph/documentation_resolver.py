"""Resolve structured node documentation from graph sources."""

from __future__ import annotations

from typing import Any

from engine.graph.doc_templates import build_doc_context, render_doc_template
from engine.graph.graph_store import GraphStore
from engine.reference.standards_reader import StandardsReader
from models.node_documentation import NodeDocumentation
from models.task import Task
from models.workflow_state import WorkflowParameter

_LEGACY_ROOT_ALIASES: dict[str, str] = {
    "pipe_wall_thickness_design": "B313-WF-PIPE-WALL-THICKNESS",
    "mawp_design": "B313-WF-MAWP",
    "B313-PIPE-WALL-THICKNESS-DESIGN": "B313-WF-PIPE-WALL-THICKNESS",
}

_DOC_KEY_ALIASES = {
    "beforeEnter": "before_enter",
    "afterExit": "after_exit",
    "reportSummary": "report_summary",
}

_STRING_FIELDS = (
    "title",
    "summary",
    "description",
    "before_enter",
    "after_exit",
    "instructions",
    "report_summary",
)
_LIST_FIELDS = ("warnings", "tips", "references")


def _normalize_doc_key(key: str) -> str:
    return _DOC_KEY_ALIASES.get(key, key)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple)):
        return len(value) == 0
    return False


def _coerce_string_list(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    if isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return tuple(items)
    text = str(value).strip()
    return (text,) if text else ()


def _legacy_documentation_fields(metadata: dict[str, Any], body: str) -> dict[str, Any]:
    title = str(metadata.get("title") or metadata.get("name") or "").strip()
    summary = str(metadata.get("summary") or metadata.get("purpose") or "").strip()
    description = str(metadata.get("description") or "").strip()
    if not description and body:
        description = body.strip()

    instructions = str(metadata.get("instructions") or metadata.get("question") or "").strip()
    before_enter = str(metadata.get("before_enter") or metadata.get("beforeEnter") or "").strip()
    after_exit = str(metadata.get("after_exit") or metadata.get("afterExit") or "").strip()
    report_summary = str(
        metadata.get("report_summary") or metadata.get("reportSummary") or ""
    ).strip()

    references_raw = metadata.get("references") or metadata.get("defined_in")
    return {
        "title": title,
        "summary": summary,
        "description": description,
        "before_enter": before_enter,
        "after_exit": after_exit,
        "instructions": instructions,
        "warnings": metadata.get("warnings"),
        "tips": metadata.get("tips"),
        "references": references_raw,
        "report_summary": report_summary,
    }


def extract_raw_documentation(metadata: dict[str, Any], body: str = "") -> dict[str, Any]:
    """Extract documentation fields from node metadata and optional body."""
    raw_doc = metadata.get("documentation")
    if isinstance(raw_doc, dict):
        base: dict[str, Any] = {}
        for key, value in raw_doc.items():
            base[_normalize_doc_key(str(key))] = value
        legacy = _legacy_documentation_fields(metadata, body)
        for key, value in legacy.items():
            if key not in base or _is_empty(base[key]):
                base[key] = value
        return base
    return _legacy_documentation_fields(metadata, body)


def resolve_node_documentation(
    store: GraphStore,
    node_id: str,
    *,
    context: dict[str, Any] | None = None,
) -> NodeDocumentation:
    """Resolve one node's documentation with optional template substitution."""
    node = store.get_node(node_id)
    if node is None:
        return NodeDocumentation(node_id=node_id)

    raw = extract_raw_documentation(node.metadata, node.body or "")
    template_context = context or {}

    rendered_strings = {
        field: render_doc_template(str(raw.get(field) or ""), template_context)
        for field in _STRING_FIELDS
    }
    return NodeDocumentation(
        node_id=node_id,
        title=rendered_strings["title"],
        summary=rendered_strings["summary"],
        description=rendered_strings["description"],
        before_enter=rendered_strings["before_enter"],
        after_exit=rendered_strings["after_exit"],
        instructions=rendered_strings["instructions"],
        warnings=_coerce_string_list(raw.get("warnings")),
        tips=_coerce_string_list(raw.get("tips")),
        references=_coerce_string_list(raw.get("references")),
        report_summary=rendered_strings["report_summary"],
    )


def _resolve_workflow_ref(root_ref: str) -> str:
    slug = root_ref.strip()
    return _LEGACY_ROOT_ALIASES.get(slug, slug)


def _workflow_root_id(task: Task, store: GraphStore) -> str | None:
    for key in ("graph_root", "selected_root"):
        value = task.outputs.get(key)
        if value and store.get_node(str(value)) is not None:
            return str(value)
    workflow_ref = str(
        task.outputs.get("workflow")
        or task.outputs.get("selected_root")
        or task.outputs.get("graph_root")
        or ""
    ).strip()
    if not workflow_ref:
        return None
    resolved = _resolve_workflow_ref(workflow_ref)
    if store.get_node(resolved) is not None:
        return resolved
    return None


def resolve_workflow_documentation(
    reader: StandardsReader,
    task: Task,
    *,
    node_ids: set[str] | frozenset[str],
    parameters: dict[str, WorkflowParameter] | None = None,
) -> dict[str, NodeDocumentation]:
    """Resolve documentation for workflow-related nodes."""
    store = reader.graph_store
    if not store.available:
        return {}

    context = build_doc_context(task, parameters=parameters, inputs=task.inputs)
    targets = set(node_ids)
    root_id = _workflow_root_id(task, store)
    if root_id:
        targets.add(root_id)

    resolved: dict[str, NodeDocumentation] = {}
    for node_id in sorted(targets):
        if not node_id or store.get_node(node_id) is None:
            continue
        resolved[node_id] = resolve_node_documentation(store, node_id, context=context)
    return resolved
