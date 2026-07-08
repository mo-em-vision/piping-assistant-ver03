"""Read-only reference chip resolution for API/Desktop presentation blocks."""

from __future__ import annotations

import re
from typing import Any

from api.node_context import display_heading_for_node
from engine.reference.equation_metadata import equation_reference
from engine.reference.paragraph_hierarchy import paragraph_reference
from engine.reference.standards_reader import StandardsReader
from engine.reference.table_metadata import table_paragraph_reference, table_reference

_GENERIC_LABEL = "Standard reference"
_REF_KEY_ORDER = ("node_id", "paragraph_id", "equation_id", "table_id")


def _display_paragraph_label(paragraph: str) -> str:
    text = str(paragraph or "").strip()
    if not text:
        return _GENERIC_LABEL
    display = re.sub(r"-[a-z]$", "", text) if re.search(r"-[a-z]$", text) else text
    return f"§{display}"


def _looks_like_raw_id(label: str, raw_id: str) -> bool:
    cleaned_label = str(label or "").strip()
    cleaned_id = str(raw_id or "").strip()
    if not cleaned_label or not cleaned_id:
        return False
    return cleaned_label == cleaned_id or cleaned_label in {
        cleaned_id,
        cleaned_id.replace("_", "-"),
        cleaned_id.replace("-", "_"),
    }


def _chip(
    *,
    ref_type: str,
    ref_id: str,
    label: str,
    target: dict[str, str],
    title: str | None = None,
) -> dict[str, Any]:
    chip: dict[str, Any] = {
        "ref_type": ref_type,
        "id": ref_id,
        "label": label or _GENERIC_LABEL,
        "target": target,
    }
    if title:
        chip["title"] = title
    return chip


def _chip_for_node(reader: StandardsReader, node_id: str, *, ref_type: str = "node") -> dict[str, Any]:
    node_id = str(node_id or "").strip()
    if not node_id:
        return _chip(
            ref_type=ref_type,
            ref_id="",
            label=_GENERIC_LABEL,
            target={},
        )

    target_key = "paragraph_id" if ref_type == "paragraph" else "node_id"
    try:
        record = reader.load(node_id)
        metadata = record.metadata
        node_type = str(metadata.get("type") or "").strip()
        if node_type == "equation":
            return _chip_for_equation(reader, node_id)
        if node_type in {"table", "lookup"}:
            return _chip_for_table(reader, node_id)

        paragraph = paragraph_reference(metadata)
        if paragraph:
            label = _display_paragraph_label(paragraph)
        else:
            heading = display_heading_for_node(metadata)
            label = heading if heading and not _looks_like_raw_id(heading, node_id) else _GENERIC_LABEL

        return _chip(
            ref_type=ref_type,
            ref_id=node_id,
            label=label,
            target={target_key: node_id},
            title=node_id if label == _GENERIC_LABEL else None,
        )
    except (FileNotFoundError, OSError):
        return _chip(
            ref_type=ref_type,
            ref_id=node_id,
            label=_GENERIC_LABEL,
            target={target_key: node_id},
            title=node_id,
        )


def _chip_for_equation(reader: StandardsReader, equation_id: str) -> dict[str, Any]:
    equation_id = str(equation_id or "").strip()
    if not equation_id:
        return _chip(
            ref_type="equation",
            ref_id="",
            label=_GENERIC_LABEL,
            target={},
        )

    try:
        record = reader.load(equation_id)
        metadata = record.metadata
        eq_number = equation_reference(metadata)
        if eq_number:
            label = f"Eq. ({eq_number})"
        else:
            heading = display_heading_for_node(metadata)
            label = heading if heading and not _looks_like_raw_id(heading, equation_id) else _GENERIC_LABEL
        return _chip(
            ref_type="equation",
            ref_id=equation_id,
            label=label,
            target={"equation_id": equation_id, "node_id": equation_id},
            title=equation_id if label == _GENERIC_LABEL else None,
        )
    except (FileNotFoundError, OSError):
        return _chip(
            ref_type="equation",
            ref_id=equation_id,
            label=_GENERIC_LABEL,
            target={"equation_id": equation_id, "node_id": equation_id},
            title=equation_id,
        )


def _chip_for_table(reader: StandardsReader, table_id: str) -> dict[str, Any]:
    table_id = str(table_id or "").strip()
    if not table_id:
        return _chip(
            ref_type="table",
            ref_id="",
            label=_GENERIC_LABEL,
            target={},
        )

    try:
        record = reader.load(table_id)
        metadata = record.metadata
        table_number = table_reference(metadata)
        paragraph = table_paragraph_reference(metadata)
        if table_number:
            label = f"Table {table_number}"
        elif paragraph:
            label = _display_paragraph_label(paragraph)
        else:
            heading = display_heading_for_node(metadata)
            label = heading if heading and not _looks_like_raw_id(heading, table_id) else _GENERIC_LABEL
        return _chip(
            ref_type="table",
            ref_id=table_id,
            label=label,
            target={"table_id": table_id, "node_id": table_id},
            title=table_id if label == _GENERIC_LABEL else None,
        )
    except (FileNotFoundError, OSError):
        return _chip(
            ref_type="table",
            ref_id=table_id,
            label=_GENERIC_LABEL,
            target={"table_id": table_id, "node_id": table_id},
            title=table_id,
        )


def resolve_reference_chips(
    refs: dict[str, str] | None,
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    """Resolve guidance-style refs into presentation reference chips."""
    if not isinstance(refs, dict):
        return []

    chips: list[dict[str, Any]] = []
    for key in _REF_KEY_ORDER:
        raw = refs.get(key)
        if raw is None:
            continue
        ref_id = str(raw).strip()
        if not ref_id:
            continue
        if key == "equation_id":
            chips.append(_chip_for_equation(reader, ref_id))
        elif key == "table_id":
            chips.append(_chip_for_table(reader, ref_id))
        elif key == "paragraph_id":
            chips.append(_chip_for_node(reader, ref_id, ref_type="paragraph"))
        else:
            chips.append(_chip_for_node(reader, ref_id, ref_type="node"))

    return dedupe_reference_chips(chips)


def resolve_reference_chips_from_legacy_links(
    links: list[dict[str, Any]] | None,
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    """Adapt legacy reference_links / value_reference shapes to reference chips."""
    if not isinstance(links, list):
        return []

    chips: list[dict[str, Any]] = []
    for link in links:
        if not isinstance(link, dict):
            continue
        node_id = str(link.get("node_id") or "").strip()
        if not node_id:
            continue

        reference_kind = str(link.get("reference_kind") or "").strip().lower()
        if reference_kind == "table":
            chip = _chip_for_table(reader, node_id)
        else:
            chip = _chip_for_node(reader, node_id, ref_type="node")

        legacy_label = str(link.get("label") or "").strip()
        if legacy_label and _looks_like_raw_id(chip["label"], node_id):
            if not _looks_like_raw_id(legacy_label, node_id):
                chip = {**chip, "label": legacy_label}

        chips.append(chip)

    return dedupe_reference_chips(chips)


def dedupe_reference_chips(chips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable dedup by ref_type + id."""
    ordered: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for chip in chips:
        if not isinstance(chip, dict):
            continue
        ref_type = str(chip.get("ref_type") or "").strip()
        ref_id = str(chip.get("id") or "").strip()
        if not ref_type or not ref_id:
            continue
        key = (ref_type, ref_id)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(chip)
    return ordered


def enrich_presentation_block_dict(
    block: dict[str, Any],
    reader: StandardsReader,
) -> dict[str, Any]:
    """Add reference_chips to a presentation/transcript block dict (projection only)."""
    if not isinstance(block, dict):
        return block

    enriched = dict(block)
    refs = block.get("refs")
    chips = resolve_reference_chips(refs if isinstance(refs, dict) else None, reader)
    if chips:
        enriched["reference_chips"] = chips
    return enriched


def _chips_from_source_ref(
    source_ref: dict[str, Any] | None,
    reader: StandardsReader,
) -> list[dict[str, Any]]:
    if not isinstance(source_ref, dict):
        return []
    refs: dict[str, str] = {}
    for key in _REF_KEY_ORDER:
        raw = source_ref.get(key)
        if raw is not None and str(raw).strip():
            refs[key] = str(raw).strip()
    node_id = str(source_ref.get("node_id") or "").strip()
    if node_id and "node_id" not in refs:
        refs["node_id"] = node_id
    return resolve_reference_chips(refs or None, reader)


def enrich_row_provenance_dict(
    row: dict[str, Any],
    reader: StandardsReader,
    *,
    task: Any | None = None,
) -> dict[str, Any]:
    """Enrich a single equation input row with value_provenance chips (projection only)."""
    if not isinstance(row, dict):
        return row

    row_copy = dict(row)
    if task is not None and row_copy.get("parameter_id") and not row_copy.get("value_provenance"):
        row_copy = apply_value_provenance_to_row(
            row_copy,
            reader,
            str(row_copy["parameter_id"]),
            task,
            display_value=str(row_copy.get("value") or ""),
        )

    provenance = row_copy.get("value_provenance")
    if isinstance(provenance, dict):
        prov_copy = dict(provenance)
        chips = _chips_from_source_ref(provenance.get("source_ref"), reader)
        if not chips:
            value_reference = row_copy.get("value_reference")
            if isinstance(value_reference, dict):
                chips = resolve_reference_chips_from_legacy_links([value_reference], reader)
        if chips:
            prov_copy["reference_chips"] = dedupe_reference_chips(chips)
        row_copy["value_provenance"] = prov_copy

    row_chips: list[dict[str, Any]] = []
    nested = row_copy.get("value_provenance")
    if isinstance(nested, dict) and isinstance(nested.get("reference_chips"), list):
        row_chips.extend(nested["reference_chips"])
    for key in ("value_reference", "definition_reference"):
        ref = row_copy.get(key)
        if isinstance(ref, dict):
            row_chips.extend(resolve_reference_chips_from_legacy_links([ref], reader))
    if row_chips:
        row_copy["reference_chips"] = dedupe_reference_chips(row_chips)

    return row_copy


def enrich_display_output_dict(
    block: dict[str, Any],
    reader: StandardsReader,
    *,
    task: Any | None = None,
) -> dict[str, Any]:
    """Add reference_chips to a display output block dict (projection only)."""
    if not isinstance(block, dict):
        return block

    enriched = dict(block)
    chips: list[dict[str, Any]] = []

    refs = block.get("refs")
    if isinstance(refs, dict):
        chips.extend(resolve_reference_chips(refs, reader))

    reference_links = block.get("reference_links")
    if isinstance(reference_links, list):
        chips.extend(resolve_reference_chips_from_legacy_links(reference_links, reader))

    for key in ("value_reference", "definition_reference", "nomenclature_reference"):
        ref = block.get(key)
        if isinstance(ref, dict):
            chips.extend(resolve_reference_chips_from_legacy_links([ref], reader))

    inputs = block.get("inputs")
    if isinstance(inputs, list):
        new_inputs: list[dict[str, Any]] = []
        for row in inputs:
            if not isinstance(row, dict):
                new_inputs.append(row)
                continue
            new_inputs.append(enrich_row_provenance_dict(row, reader, task=task))
        enriched["inputs"] = new_inputs

    input_table = block.get("input_table")
    if isinstance(input_table, dict):
        rows = input_table.get("rows")
        if isinstance(rows, list):
            enriched["input_table"] = {
                **input_table,
                "rows": [
                    enrich_row_provenance_dict(row, reader, task=task) if isinstance(row, dict) else row
                    for row in rows
                ],
            }

    deduped = dedupe_reference_chips(chips)
    if deduped:
        enriched["reference_chips"] = deduped
    return enriched


def enrich_flow_guidance_payload(
    payload: dict[str, Any],
    reader: StandardsReader,
) -> dict[str, Any]:
    """Add reference_chips to flow_guidance API payload blocks."""
    if not isinstance(payload, dict):
        return payload

    enriched = dict(payload)
    for key in ("transcript_blocks", "presentation_blocks"):
        blocks = payload.get(key)
        if not isinstance(blocks, list):
            continue
        enriched[key] = [
            enrich_presentation_block_dict(item, reader) for item in blocks if isinstance(item, dict)
        ]

    active_prompt = payload.get("active_prompt")
    if isinstance(active_prompt, dict):
        enriched["active_prompt"] = enrich_presentation_block_dict(active_prompt, reader)

    return enriched
