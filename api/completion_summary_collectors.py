"""Collect applied paragraphs and graph-derived assumptions for completion summaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.equation_display_registry import source_node_id_for_equation
from api.paragraph_display import paragraph_reference_label
from engine.graph.assumption_checker import (
    applicability_expansion_satisfied,
    field_value,
    normalize_assumption_value,
)
from engine.reference.paragraph_sidecar import merge_paragraph_sidecar_metadata
from engine.reference.standards_reader import StandardsReader
from models.task import Task

APPLIED_STANDARD_HEADER = "Applied standard:"
APPLIED_STANDARDS_HEADER = "Applied standards:"
ASSUMPTIONS_INTRO = "The following assumptions have been made in the calculation:"


@dataclass(frozen=True)
class AppliedParagraph:
    node_id: str
    label: str
    authority: str


@dataclass(frozen=True)
class CompletionAssumption:
    phrase: str
    source_node_id: str
    reference_label: str


def _paragraph_metadata(reader: StandardsReader, node_id: str) -> dict[str, Any] | None:
    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return None
    if str(record.metadata.get("type") or "") != "paragraph":
        return None
    return merge_paragraph_sidecar_metadata(
        record.metadata,
        record_path=record.path,
        node_id=node_id,
    )


def _presentation_meta(metadata: dict[str, Any]) -> dict[str, Any]:
    raw = metadata.get("presentation")
    return raw if isinstance(raw, dict) else {}


def _execution_block(metadata: dict[str, Any]) -> dict[str, Any]:
    execution = metadata.get("execution")
    return execution if isinstance(execution, dict) else {}


def _metadata_list(metadata: dict[str, Any], *keys: str) -> list[Any]:
    execution = _execution_block(metadata)
    for key in keys:
        raw = metadata.get(key)
        if raw is None:
            raw = execution.get(key)
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
    return []


def _metadata_for_applicability(metadata: dict[str, Any]) -> dict[str, Any]:
    execution = _execution_block(metadata)
    applicability = execution.get("applicability") or metadata.get("applicability")
    if not isinstance(applicability, dict):
        return metadata
    merged = dict(metadata)
    merged["applicability"] = applicability
    return merged


def _paragraph_node_ids_from_trace(
    trace: list[Any] | None,
    reader: StandardsReader,
) -> list[str]:
    if not isinstance(trace, list):
        return []

    node_ids: list[str] = []
    seen: set[str] = set()
    for entry in trace:
        if not isinstance(entry, dict):
            continue
        node_id = str(entry.get("node_id") or "").strip()
        if not node_id or node_id in seen:
            continue
        try:
            node_type = str(reader.load(node_id).metadata.get("type") or "")
        except FileNotFoundError:
            continue

        resolved = node_id
        if node_type == "equation":
            resolved = source_node_id_for_equation(reader, node_id)
            try:
                resolved_type = str(reader.load(resolved).metadata.get("type") or "")
            except FileNotFoundError:
                continue
            if resolved_type != "paragraph":
                continue
        elif node_type != "paragraph":
            continue

        if resolved in seen:
            continue
        seen.add(resolved)
        node_ids.append(resolved)
    return node_ids


def collect_applied_paragraphs(
    task: Task,
    reader: StandardsReader,
) -> tuple[str, list[AppliedParagraph]]:
    """Return applied-standard header and visited paragraph citations from execution trace."""
    trace = task.outputs.get("_execution_trace")
    node_ids = _paragraph_node_ids_from_trace(trace, reader)

    paragraphs: list[AppliedParagraph] = []
    authorities: set[str] = set()
    for node_id in node_ids:
        metadata = _paragraph_metadata(reader, node_id)
        if metadata is None:
            continue
        label = paragraph_reference_label(metadata, node_id)
        if not label:
            continue
        authority = str(metadata.get("authority") or "").strip()
        if authority:
            authorities.add(authority)
        paragraphs.append(
            AppliedParagraph(
                node_id=node_id,
                label=label,
                authority=authority,
            )
        )

    header = APPLIED_STANDARDS_HEADER if len(authorities) > 1 else APPLIED_STANDARD_HEADER
    return header, paragraphs


def _active_paragraph_node_ids(task: Task, reader: StandardsReader) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    for node_id in task.active_nodes or []:
        node_id = str(node_id).strip()
        if not node_id or node_id in seen:
            continue
        metadata = _paragraph_metadata(reader, node_id)
        if metadata is None:
            continue
        seen.add(node_id)
        ordered.append(node_id)

    for node_id in _paragraph_node_ids_from_trace(task.outputs.get("_execution_trace"), reader):
        if node_id not in seen:
            seen.add(node_id)
            ordered.append(node_id)

    return ordered


def collect_completion_assumptions(
    task: Task,
    reader: StandardsReader,
) -> list[CompletionAssumption]:
    """Collect graph-authored assumptions satisfied on the active calculation path."""
    inputs = task.fact_store.active_facts()
    assumptions: list[CompletionAssumption] = []
    seen: set[tuple[str, str]] = set()

    def append(phrase: str, source_node_id: str, reference_label: str) -> None:
        phrase = str(phrase or "").strip()
        source_node_id = str(source_node_id or "").strip()
        reference_label = str(reference_label or "").strip()
        if not phrase or not source_node_id:
            return
        key = (phrase, source_node_id)
        if key in seen:
            return
        seen.add(key)
        assumptions.append(
            CompletionAssumption(
                phrase=phrase,
                source_node_id=source_node_id,
                reference_label=reference_label or source_node_id,
            )
        )

    for node_id in _active_paragraph_node_ids(task, reader):
        metadata = _paragraph_metadata(reader, node_id)
        if metadata is None:
            continue
        ref_label = paragraph_reference_label(metadata, node_id)
        execution = _execution_block(metadata)

        for item in _metadata_list(metadata, "assumptions"):
            field = str(item.get("field") or "").strip()
            if not field:
                continue
            value = field_value(field, inputs)
            if value is None:
                continue
            blocks = item.get("blocks_expansion_on") or []
            if blocks and normalize_assumption_value(value) in {
                normalize_assumption_value(v) for v in blocks
            }:
                continue
            if isinstance(item.get("allowed_values"), list) and item.get("allowed_values"):
                allowed = {normalize_assumption_value(v) for v in item["allowed_values"]}
                if value not in allowed:
                    continue
            description = str(item.get("description") or "").strip()
            if description:
                append(description, node_id, ref_label)

        for item in _metadata_list(metadata, "provisional_assumptions"):
            field = str(item.get("field") or "").strip()
            if not field:
                continue
            if field_value(field, inputs) is None and task.outputs.get(field) is None:
                continue
            description = str(item.get("description") or "").strip()
            if description:
                append(description, node_id, ref_label)

        applicability = metadata.get("applicability") or execution.get("applicability") or {}
        if isinstance(applicability, dict):
            applies_when = applicability.get("applies_when") or []
            if applies_when and applicability_expansion_satisfied(
                _metadata_for_applicability(metadata),
                inputs,
            ):
                display_label = str(_presentation_meta(metadata).get("display_label") or "").strip()
                if display_label:
                    append(display_label, node_id, ref_label)

    return assumptions
