"""Build active-node context and standards node source payloads for the desktop UI."""

from __future__ import annotations

import re
from typing import Any

from api.workflow_bootstrap import resolve_activated_definition_node
from engine.state.goal_projection import planning_projection
from engine.reference.equation_metadata import equation_paragraph_reference, equation_reference
from engine.reference.paragraph_hierarchy import (
    hierarchy_entries,
    paragraph_reference,
    resolve_hierarchy_chain,
    section_label,
)
from engine.reference.standards_reader import StandardsReader
from models.task import Task

_DEFAULT_STANDARD_LABEL = "ASME B31.3"


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _first_body_paragraph(body: str) -> str:
    lines = body.splitlines()
    paragraph_lines: list[str] = []
    in_paragraph = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_paragraph:
                break
            continue
        if stripped.startswith("#"):
            if in_paragraph:
                break
            continue
        if stripped.startswith("```"):
            if in_paragraph:
                break
            continue
        if stripped.startswith("|"):
            if in_paragraph:
                break
            continue
        in_paragraph = True
        paragraph_lines.append(stripped)

    if paragraph_lines:
        return _collapse_whitespace(" ".join(paragraph_lines))

    for subsection in ("(a)", "## (a)"):
        if subsection in body:
            chunk = body.split(subsection, 1)[-1]
            for line in chunk.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("```"):
                    return _collapse_whitespace(stripped)

    return ""


def _subsection_excerpt(metadata: dict[str, Any]) -> str:
    for item in metadata.get("subsections", []) or []:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if text:
            return _collapse_whitespace(text)
    return ""


def _authority_text(metadata: dict[str, Any], body: str) -> str:
    body_text = body.strip()
    if body_text:
        return body_text
    text_block = metadata.get("text") or {}
    if isinstance(text_block, dict):
        return str(text_block.get("original") or "").strip()
    if isinstance(text_block, str):
        return text_block.strip()
    return ""


def hover_excerpt_for_node(record) -> str:
    metadata = record.metadata
    excerpt = _subsection_excerpt(metadata)
    if excerpt:
        return excerpt
    body_excerpt = _first_body_paragraph(_authority_text(metadata, record.body))
    if body_excerpt:
        return body_excerpt
    purpose = str(metadata.get("purpose", "")).strip()
    return _collapse_whitespace(purpose)


def display_heading_for_node(
    metadata: dict[str, Any],
    *,
    standard_label: str = _DEFAULT_STANDARD_LABEL,
) -> str:
    explicit = str(metadata.get("display_heading", "")).strip()
    if explicit:
        return _collapse_whitespace(explicit)

    purpose = _collapse_whitespace(str(metadata.get("purpose", "")).strip())
    paragraph = paragraph_reference(metadata)
    if purpose and paragraph:
        return f"{purpose} (according to {standard_label} paragraph {paragraph})"
    if purpose:
        return purpose
    title = str(metadata.get("title", "")).strip()
    if title and paragraph:
        return f"{title} (according to {standard_label} paragraph {paragraph})"
    return title or str(metadata.get("id", ""))


def revision_year_from_metadata(metadata: dict[str, Any]) -> int | None:
    raw = metadata.get("revision_year")
    if raw is None or str(raw).strip() == "":
        nested = metadata.get("metadata") or {}
        if isinstance(nested, dict):
            raw = nested.get("source_revision_year")
    if raw is None or str(raw).strip() == "":
        return None
    return int(raw)


def _citation_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    node_type = str(metadata.get("type") or "")
    if node_type == "equation":
        paragraph = equation_paragraph_reference(metadata) or None
        return {
            "paragraph": paragraph,
            "paragraph_number": paragraph,
            "equation_number": equation_reference(metadata) or None,
        }
    paragraph = paragraph_reference(metadata) or None
    return {
        "paragraph": paragraph,
        "paragraph_number": paragraph,
        "equation_number": None,
    }


def node_source_payload(reader: StandardsReader, node_id: str) -> dict[str, Any]:
    record = reader.load(node_id)
    metadata = record.metadata
    hierarchy = resolve_hierarchy_chain(reader, record.node_id)
    return {
        "node_id": record.node_id,
        "title": str(metadata.get("title", "")).strip(),
        "standard": _DEFAULT_STANDARD_LABEL,
        **_citation_fields(metadata),
        "section": section_label({**metadata, "hierarchy_chain": hierarchy}),
        "hierarchy": hierarchy,
        "revision_year": revision_year_from_metadata(metadata),
        "body": _authority_text(metadata, record.body),
        "hover_excerpt": hover_excerpt_for_node(record),
    }


def subsection_source_payload(
    reader: StandardsReader,
    node_id: str,
    subsection_id: str,
) -> dict[str, Any]:
    """Build a focused node-subsection payload for the desktop reference tab."""
    record = reader.load(node_id)
    parent_metadata = record.metadata
    subsection = reader.load_subsection(node_id, subsection_id)
    subsection_meta = subsection.metadata if isinstance(subsection.metadata, dict) else {}

    title = str(subsection_meta.get("title", "")).strip()
    paragraph = str(subsection.paragraph or subsection_meta.get("paragraph", "")).strip() or None
    body = subsection.body.strip()
    purpose = str(subsection_meta.get("purpose", "")).strip()
    hover_excerpt = _first_body_paragraph(body) if body else _collapse_whitespace(title or purpose)
    hierarchy = resolve_hierarchy_chain(reader, record.node_id)

    return {
        "node_id": record.node_id,
        "title": str(parent_metadata.get("title", "")).strip(),
        "standard": _DEFAULT_STANDARD_LABEL,
        "paragraph": paragraph,
        "section": section_label({**parent_metadata, "hierarchy_chain": hierarchy}),
        "hierarchy": hierarchy,
        "subsection_id": subsection.subsection_id,
        "subsection_title": title or None,
        "subsection_paragraph": paragraph,
        "revision_year": revision_year_from_metadata(parent_metadata),
        "body": body,
        "hover_excerpt": hover_excerpt,
    }


def display_heading_source_field(metadata: dict[str, Any]) -> str:
    """Return the metadata key that supplies ``display_heading_for_node``."""
    explicit = str(metadata.get("display_heading", "")).strip()
    if explicit:
        return "display_heading"
    purpose = str(metadata.get("purpose", "")).strip()
    if purpose:
        return "purpose"
    title = str(metadata.get("title", "")).strip()
    if title:
        return "title"
    return "id"


def active_context_source_field(metadata: dict[str, Any]) -> str:
    return display_heading_source_field(metadata)


def active_node_context_for_task(
    task: Task,
    reader: StandardsReader,
) -> dict[str, Any] | None:
    planning = planning_projection(task)
    if not isinstance(planning, dict):
        planning = {}

    node_id = planning.get("active_definition_node")
    if not node_id:
        workflow_id = str(task.outputs.get("workflow") or task.outputs.get("selected_root") or "")
        if workflow_id:
            node_id = resolve_activated_definition_node(reader, workflow_id)
    if not node_id and task.active_nodes:
        for candidate in task.active_nodes:
            try:
                if str(reader.load(candidate).metadata.get("type", "")) == "definition":
                    node_id = candidate
                    break
            except FileNotFoundError:
                continue
    if not node_id:
        return None

    try:
        record = reader.load(str(node_id))
    except FileNotFoundError:
        return None

    metadata = record.metadata
    citations = _citation_fields(metadata)
    hierarchy = resolve_hierarchy_chain(reader, record.node_id)
    return {
        "node_id": record.node_id,
        "standard": _DEFAULT_STANDARD_LABEL,
        "paragraph": citations["paragraph"],
        "paragraph_number": citations["paragraph_number"],
        "equation_number": citations["equation_number"],
        "hierarchy": hierarchy,
        "display_heading": display_heading_for_node(metadata),
        "hover_excerpt": hover_excerpt_for_node(record),
        "source_field": active_context_source_field(metadata),
    }
