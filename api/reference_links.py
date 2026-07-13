"""Read-only reference chip resolution for API/Desktop presentation blocks."""

from __future__ import annotations

import re
from typing import Any

from api.node_context import display_heading_for_node
from engine.reference.equation_metadata import equation_reference
from engine.reference.parameter_value_source import apply_value_provenance_to_row
from engine.reference.paragraph_hierarchy import paragraph_reference
from engine.reference.standards_reader import StandardsReader
from engine.reference.table_metadata import (
    format_table_citation,
    resolve_table_db_id,
    table_reference,
)

_GENERIC_LABEL = "Standard reference"
_DEFAULT_STANDARD_LABEL = "ASME B31.3"
_REF_KEY_ORDER = ("node_id", "paragraph_id", "equation_id", "table_id")


def _standard_display_label() -> str:
    return _DEFAULT_STANDARD_LABEL


def _with_standard_prefix(label: str) -> str:
    text = str(label or "").strip()
    if not text or text == _GENERIC_LABEL:
        return text
    standard_label = _standard_display_label()
    if text.startswith(standard_label):
        return text
    return f"{standard_label} {text}"


def _display_paragraph_label(paragraph: str) -> str:
    text = str(paragraph or "").strip()
    if not text:
        return _GENERIC_LABEL
    display = re.sub(r"-[a-z]$", "", text) if re.search(r"-[a-z]$", text) else text
    return _with_standard_prefix(f"§{display}")


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
            if label != _GENERIC_LABEL:
                label = _with_standard_prefix(label)

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
            label = _with_standard_prefix(f"Eq. ({eq_number})")
        else:
            heading = display_heading_for_node(metadata)
            label = heading if heading and not _looks_like_raw_id(heading, equation_id) else _GENERIC_LABEL
            if label != _GENERIC_LABEL:
                label = _with_standard_prefix(label)
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


def _resolve_table_node(reader: StandardsReader, table_id: str) -> tuple[Any, str] | tuple[None, None]:
    """Resolve a table db ref or graph node id to a loadable standards record."""
    from engine.reference.table_metadata import resolve_lookup_node_id

    table_id = str(table_id or "").strip()
    if not table_id:
        return None, None

    for candidate in (table_id, resolve_lookup_node_id(reader, table_id)):
        if not candidate:
            continue
        try:
            return reader.load(candidate), candidate
        except (FileNotFoundError, OSError):
            continue

    tables_db = getattr(reader, "tables_database", None)
    if tables_db is not None:
        resolved = tables_db.resolve_table_id(table_id)
        if resolved:
            node_id = resolve_lookup_node_id(reader, resolved)
            if node_id:
                try:
                    return reader.load(node_id), node_id
                except (FileNotFoundError, OSError):
                    pass
    return None, None


def _chip_for_table(reader: StandardsReader, table_id: str) -> dict[str, Any]:
    table_id = str(table_id or "").strip()
    if not table_id:
        return _chip(
            ref_type="table",
            ref_id="",
            label=_GENERIC_LABEL,
            target={},
        )

    record, _resolved_node_id = _resolve_table_node(reader, table_id)
    if record is not None:
        metadata = record.metadata
        table_number = table_reference(metadata)
        db_table_id = resolve_table_db_id(reader, metadata, table_ref=table_id)
        if table_number:
            label = format_table_citation(
                standard_label=_standard_display_label(),
                table_number=table_number,
            )
        else:
            heading = display_heading_for_node(metadata)
            label = heading if heading and not _looks_like_raw_id(heading, table_id) else _GENERIC_LABEL
            if label != _GENERIC_LABEL:
                label = _with_standard_prefix(label)
        return _chip(
            ref_type="table",
            ref_id=db_table_id,
            label=label,
            target={"table_id": db_table_id, "node_id": db_table_id},
            title=db_table_id if label == _GENERIC_LABEL else None,
        )

    tables_db = getattr(reader, "tables_database", None)
    resolved_db_id = table_id
    if tables_db is not None:
        resolved = tables_db.resolve_table_id(table_id)
        if resolved:
            resolved_db_id = resolved
    return _chip(
        ref_type="table",
        ref_id=resolved_db_id,
        label=_GENERIC_LABEL,
        target={"table_id": resolved_db_id, "node_id": resolved_db_id},
        title=resolved_db_id,
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
                chip = {**chip, "label": _with_standard_prefix(legacy_label)}
        elif legacy_label and not legacy_label.startswith(_standard_display_label()):
            chip = {**chip, "label": _with_standard_prefix(legacy_label)}

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


_CHIP_TYPE_PRIORITY = ("equation", "table", "paragraph", "node")


def select_primary_reference_chip(chips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return at most one primary chip for visible table-cell display."""
    deduped = dedupe_reference_chips(chips)
    if not deduped:
        return []
    if len(deduped) == 1:
        return deduped

    def rank(chip: dict[str, Any]) -> tuple[int, str]:
        ref_type = str(chip.get("ref_type") or "").strip().lower()
        try:
            priority = _CHIP_TYPE_PRIORITY.index(ref_type)
        except ValueError:
            priority = len(_CHIP_TYPE_PRIORITY)
        return (priority, str(chip.get("label") or ""))

    deduped.sort(key=rank)
    return [deduped[0]]


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
    provenance = row_copy.get("value_provenance")
    if task is not None and row_copy.get("parameter_id") and not provenance:
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
        source_type = str(provenance.get("source_type") or "")
        chips = _chips_from_source_ref(provenance.get("source_ref"), reader)
        if not chips:
            value_reference = row_copy.get("value_reference")
            if isinstance(value_reference, dict):
                chips = resolve_reference_chips_from_legacy_links([value_reference], reader)
        if source_type == "equation_output" and chips:
            paragraph_chips = [
                chip for chip in chips if str(chip.get("ref_type") or "") == "paragraph"
            ]
            chips = paragraph_chips or select_primary_reference_chip(chips)
        elif chips:
            chips = select_primary_reference_chip(chips)
        if chips:
            prov_copy["reference_chips"] = chips
        row_copy["value_provenance"] = prov_copy

    nested = row_copy.get("value_provenance")
    if isinstance(nested, dict) and nested.get("reference_chips"):
        row_copy.pop("reference_chips", None)
    else:
        row_chips: list[dict[str, Any]] = []
        for key in ("value_reference",):
            ref = row_copy.get(key)
            if isinstance(ref, dict):
                row_chips.extend(resolve_reference_chips_from_legacy_links([ref], reader))
        if row_chips:
            row_copy["reference_chips"] = select_primary_reference_chip(row_chips)

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

    block_type = str(block.get("type") or "")
    equation_node_id = str(block.get("equation_node_id") or "").strip()
    input_table = block.get("input_table")
    has_input_table = isinstance(input_table, dict) and bool(input_table.get("rows"))

    if block_type == "equation" and equation_node_id:
        try:
            eq_record = reader.load(equation_node_id)
            eq_number = equation_reference(eq_record.metadata)
            if eq_number:
                enriched["equation_number"] = eq_number
        except (FileNotFoundError, OSError):
            pass
        if not has_input_table:
            chips = [_chip_for_equation(reader, equation_node_id)]
    else:
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

    input_table = block.get("input_table")
    row_chip_ids: set[tuple[str, str]] = set()
    if isinstance(input_table, dict):
        rows = input_table.get("rows")
        if isinstance(rows, list):
            enriched_rows: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    enriched_rows.append(row)
                    continue
                enriched_row = enrich_row_provenance_dict(row, reader, task=task)
                enriched_rows.append(enriched_row)
                provenance = enriched_row.get("value_provenance")
                if isinstance(provenance, dict):
                    for chip in provenance.get("reference_chips") or []:
                        if isinstance(chip, dict):
                            row_chip_ids.add(
                                (
                                    str(chip.get("ref_type") or ""),
                                    str(chip.get("id") or ""),
                                )
                            )
            enriched["input_table"] = {**input_table, "rows": enriched_rows}

    deduped = select_primary_reference_chip(chips)
    if deduped and not row_chip_ids:
        enriched["reference_chips"] = deduped
    elif deduped:
        footer = [
            chip
            for chip in deduped
            if (str(chip.get("ref_type") or ""), str(chip.get("id") or "")) not in row_chip_ids
        ]
        if footer:
            enriched["reference_chips"] = footer
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
