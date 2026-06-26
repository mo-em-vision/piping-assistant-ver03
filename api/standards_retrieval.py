"""Retrieve relevant standards nodes and tables for task chat grounding."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from api.node_context import display_heading_for_node, hover_excerpt_for_node
from api.table_context import table_source_payload
from engine.reference.asme_b31_3_table_ids import (
    TABLE_302_3_5,
    TABLE_304_1_1,
    TABLE_A_1A,
    TABLE_A_1B,
    local_table_id,
)
from engine.reference.coefficient_resolver import lookup_y_coefficient
from engine.reference.standards_reader import StandardsReader

_DEFAULT_STANDARD_LABEL = "ASME B31.3"
_MAX_SOURCES = 3
_MAX_TABLE_ROWS = 20

_SYMBOL_ALIASES: dict[str, list[str]] = {
    "y": [
        "y",
        "temperature coefficient",
        "coefficient y",
        "temperature_coefficient",
        "coefficient from table 304.1.1",
    ],
    "w": [
        "w",
        "weld strength reduction",
        "weld_strength_reduction",
        "weld strength reduction factor",
    ],
    "e": [
        "e",
        "quality factor",
        "joint efficiency",
        "weld joint efficiency",
    ],
    "s": [
        "s",
        "allowable stress",
        "allowable_stress",
    ],
}

_TABLE_ALIASES: dict[str, list[str]] = {
    "table_304_1_1": ["304.1.1", "table 304.1.1", "temperature coefficient y"],
    "302.3.5": ["302.3.5", "table 302.3.5", "weld strength reduction"],
    "a-1": ["table a-1", "allowable stress"],
    "a-1a": ["table a-1a", "quality factor"],
    "a-1b": ["table a-1b"],
}


@dataclass
class RetrievedSource:
    kind: str
    id: str
    label: str
    standard: str = _DEFAULT_STANDARD_LABEL
    paragraph: str | None = None
    node_id: str | None = None
    table_id: str | None = None
    excerpt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "kind": self.kind,
            "id": self.id,
            "label": self.label,
            "standard": self.standard,
        }
        if self.paragraph:
            payload["paragraph"] = self.paragraph
        if self.node_id:
            payload["node_id"] = self.node_id
        if self.table_id:
            payload["table_id"] = self.table_id
        return payload


@dataclass
class RetrievalResult:
    sources: list[RetrievedSource] = field(default_factory=list)
    context_block: str = ""

    def source_dicts(self) -> list[dict[str, Any]]:
        return [source.to_dict() for source in self.sources]


@dataclass
class _IndexEntry:
    key: str
    kind: str
    node_id: str | None = None
    table_id: str | None = None
    label: str = ""
    paragraph: str | None = None
    keywords: list[str] = field(default_factory=list)
    boost: float = 0.0


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokenize(text: str) -> set[str]:
    normalized = _normalize_text(text)
    tokens = set(re.findall(r"[a-z0-9._-]+", normalized))
    tokens.update(part for part in normalized.split() if len(part) > 1)
    return tokens


def _collect_nomenclature_keywords(metadata: dict[str, Any]) -> list[tuple[str, str | None, str | None]]:
    """Return (symbol_or_input, table_id, node_id) tuples from nomenclature."""
    results: list[tuple[str, str | None, str | None]] = []
    for item in metadata.get("nomenclature", []) or []:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip()
        input_id = str(item.get("input_id", "")).strip()
        description = str(item.get("description", "")).strip()
        table_id: str | None = None
        node_id: str | None = None
        resolution = item.get("resolution")
        if isinstance(resolution, dict):
            table_id = str(resolution.get("table_id", "")).strip() or None
            node_id = str(resolution.get("node_id", "")).strip() or None
        elif isinstance(resolution, list):
            for branch in resolution:
                if isinstance(branch, dict) and branch.get("method") == "table_lookup":
                    table_id = str(branch.get("table_id", "")).strip() or table_id
                    break
        for ref in item.get("references", []) or []:
            if not isinstance(ref, dict):
                continue
            table_id = table_id or (str(ref.get("table_id", "")).strip() or None)
            node_id = node_id or (str(ref.get("node_id", "")).strip() or None)
        if symbol:
            results.append((symbol, table_id, node_id))
        if input_id:
            results.append((input_id, table_id, node_id))
        if description:
            results.append((description, table_id, node_id))
    return results


def _build_index(reader: StandardsReader) -> list[_IndexEntry]:
    if hasattr(reader, "_retrieval_index"):
        return reader._retrieval_index  # type: ignore[attr-defined]

    entries: list[_IndexEntry] = []
    nodes_dir = reader.nodes_dir
    if nodes_dir.is_dir():
        for path in sorted(nodes_dir.rglob("node.md")):
            record = reader.load_file(path)
            metadata = record.metadata
            node_id = record.node_id
            title = str(metadata.get("title", "")).strip()
            paragraph = str(metadata.get("paragraph", "")).strip() or None
            topic = str(metadata.get("topic", "")).strip()
            label = display_heading_for_node(metadata)
            keywords = [title, topic, node_id, label]
            if paragraph:
                keywords.append(paragraph)
                keywords.append(f"paragraph {paragraph}")

            for item in metadata.get("inputs", []) or []:
                if isinstance(item, dict):
                    keywords.extend(
                        str(item.get(key, "")).strip()
                        for key in ("id", "name", "description")
                        if item.get(key)
                    )
            for item in metadata.get("outputs", []) or []:
                if isinstance(item, dict):
                    keywords.extend(
                        str(item.get(key, "")).strip()
                        for key in ("id", "name", "description")
                        if item.get(key)
                    )
            for lookup in metadata.get("lookups", []) or []:
                if isinstance(lookup, dict):
                    table_id = str(lookup.get("table_id", "")).strip()
                    if table_id:
                        entries.append(
                            _IndexEntry(
                                key=f"table:{table_id}",
                                kind="table",
                                node_id=node_id,
                                table_id=table_id,
                                label=title or table_id,
                                paragraph=paragraph,
                                keywords=[table_id, title, topic],
                            )
                        )

            for symbol, table_id, linked_node in _collect_nomenclature_keywords(metadata):
                sym_keywords = [symbol]
                sym_lower = symbol.lower()
                if sym_lower in _SYMBOL_ALIASES:
                    sym_keywords.extend(_SYMBOL_ALIASES[sym_lower])
                entries.append(
                    _IndexEntry(
                        key=f"node:{node_id}:{symbol}",
                        kind="node",
                        node_id=node_id,
                        table_id=table_id,
                        label=label,
                        paragraph=paragraph,
                        keywords=sym_keywords + keywords,
                    )
                )
                if table_id:
                    entries.append(
                        _IndexEntry(
                            key=f"table:{table_id}",
                            kind="table",
                            node_id=linked_node or node_id,
                            table_id=table_id,
                            label=title or table_id,
                            paragraph=paragraph,
                            keywords=sym_keywords + [table_id],
                        )
                    )

            entries.append(
                _IndexEntry(
                    key=f"node:{node_id}",
                    kind="node",
                    node_id=node_id,
                    label=label,
                    paragraph=paragraph,
                    keywords=[kw for kw in keywords if kw],
                )
            )

    for table_id in reader.tables_database.list_table_ids():
        try:
            _, data = reader.load_table_by_id(table_id)
        except FileNotFoundError:
            continue
        title = str(data.get("title") or table_id).strip()
        aliases = _TABLE_ALIASES.get(local_table_id(table_id).lower(), [])
        entries.append(
            _IndexEntry(
                key=f"table:{table_id}",
                kind="table",
                table_id=table_id,
                label=title,
                keywords=[table_id, title, *aliases],
            )
        )

    reader._retrieval_index = entries  # type: ignore[attr-defined]
    return entries


def _score_entry(entry: _IndexEntry, query: str, query_tokens: set[str]) -> float:
    normalized_query = _normalize_text(query)
    score = entry.boost
    for keyword in entry.keywords:
        if not keyword:
            continue
        normalized_keyword = _normalize_text(keyword)
        if normalized_keyword in normalized_query:
            score += 8.0
        keyword_tokens = _tokenize(keyword)
        overlap = len(query_tokens & keyword_tokens)
        if overlap:
            score += overlap * 2.0
    return score


def _task_seed_boosts(task_state_payload: dict[str, Any] | None) -> dict[str, float]:
    boosts: dict[str, float] = {}
    if not task_state_payload:
        return boosts

    active_node = task_state_payload.get("active_node_context") or {}
    node_id = str(active_node.get("node_id") or "").strip()
    if node_id:
        boosts[f"node:{node_id}"] = 15.0

    inputs = task_state_payload.get("inputs") or {}
    if isinstance(inputs, dict):
        if inputs.get("design_temperature"):
            boosts[f"table:{TABLE_304_1_1}"] = max(boosts.get(f"table:{TABLE_304_1_1}", 0), 12.0)
            boosts["node:B313-table-304-1-1"] = 10.0
        if inputs.get("material") and inputs.get("joint_category"):
            boosts[f"table:{TABLE_A_1A}"] = max(boosts.get(f"table:{TABLE_A_1A}", 0), 8.0)
            boosts[f"table:{TABLE_A_1B}"] = max(boosts.get(f"table:{TABLE_A_1B}", 0), 8.0)
        if inputs.get("weld_joint_category") or inputs.get("joint_category"):
            boosts[f"table:{TABLE_302_3_5}"] = max(boosts.get(f"table:{TABLE_302_3_5}", 0), 8.0)

    return boosts


def _apply_boosts(entries: list[_IndexEntry], boosts: dict[str, float]) -> None:
    for entry in entries:
        for boost_key, value in boosts.items():
            if entry.key == boost_key or (
                entry.node_id and boost_key == f"node:{entry.node_id}"
            ):
                entry.boost = max(entry.boost, value)


def _format_table_excerpt(reader: StandardsReader, table_id: str) -> str:
    payload = table_source_payload(reader, table_id)
    rows = payload.get("rows") or []
    columns = payload.get("columns") or []
    title = payload.get("title") or table_id
    lines = [f"### {title} ({payload.get('standard', _DEFAULT_STANDARD_LABEL)})"]
    if columns:
        header = " | ".join(str(col.get("label") or col.get("key")) for col in columns)
        lines.append(f"| {header} |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        for row in rows[:_MAX_TABLE_ROWS]:
            cells = [str(row.get(str(col.get("key")), "")) for col in columns]
            lines.append(f"| {' | '.join(cells)} |")
        if len(rows) > _MAX_TABLE_ROWS:
            lines.append(f"_(Showing {_MAX_TABLE_ROWS} of {len(rows)} rows.)_")
    elif rows:
        lines.append("```json")
        lines.append(json.dumps(rows[:_MAX_TABLE_ROWS], indent=2, default=str))
        lines.append("```")
    return "\n".join(lines)


def _load_node_source(reader: StandardsReader, node_id: str) -> RetrievedSource | None:
    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return None
    metadata = record.metadata
    return RetrievedSource(
        kind="node",
        id=node_id,
        label=display_heading_for_node(metadata),
        paragraph=str(metadata.get("paragraph", "")).strip() or None,
        node_id=node_id,
        excerpt=hover_excerpt_for_node(record),
    )


def _load_table_source(
    reader: StandardsReader,
    table_id: str,
    *,
    node_id: str | None = None,
    paragraph: str | None = None,
) -> RetrievedSource | None:
    try:
        payload = table_source_payload(reader, table_id)
    except FileNotFoundError:
        return None
    title = str(payload.get("title") or table_id).strip()
    return RetrievedSource(
        kind="table",
        id=table_id,
        label=title,
        paragraph=paragraph,
        node_id=node_id,
        table_id=table_id,
        excerpt=_format_table_excerpt(reader, table_id),
    )


def _input_value(inputs: dict[str, Any], input_id: str) -> tuple[Any, str] | None:
    raw = inputs.get(input_id)
    if not isinstance(raw, dict):
        return None
    value = raw.get("value")
    if value is None:
        return None
    unit = str(raw.get("unit") or "F").strip() or "F"
    return value, unit


def _maybe_add_y_lookup(
    reader: StandardsReader,
    task_state_payload: dict[str, Any] | None,
    sources: list[RetrievedSource],
) -> None:
    if not task_state_payload:
        return
    inputs = task_state_payload.get("inputs") or {}
    if not isinstance(inputs, dict):
        return
    temp = _input_value(inputs, "design_temperature")
    if temp is None:
        return
    temp_value, temp_unit = temp
    try:
        y_value, interpolated = lookup_y_coefficient(
            reader.pack_root,
            design_temperature=float(temp_value),
            design_temperature_unit=temp_unit,
        )
    except (ValueError, FileNotFoundError):
        return

    interp_note = " (interpolated)" if interpolated else ""
    sources.append(
        RetrievedSource(
            kind="lookup_result",
            id="temperature_coefficient",
            label=f"Y = {y_value}{interp_note} at {temp_value} {temp_unit}",
            paragraph="304.1.1",
            node_id="B313-table-304-1-1",
            table_id=TABLE_304_1_1,
            excerpt=(
                f"Deterministic lookup from Table 304.1.1 at design temperature "
                f"{temp_value} {temp_unit}: Y = {y_value}{interp_note}."
            ),
        )
    )


def _build_context_block(sources: list[RetrievedSource]) -> str:
    if not sources:
        return "No matching standards sources were retrieved for this question."
    sections: list[str] = []
    for index, source in enumerate(sources, start=1):
        cite_parts = [source.standard]
        if source.paragraph:
            cite_parts.append(f"§{source.paragraph}")
        if source.table_id:
            local = local_table_id(source.table_id)
            cite_parts.append(f"Table {local.replace('table_', '').replace('_', '.')}")
        header = f"#### Source {index}: {source.label} ({', '.join(cite_parts)})"
        body = source.excerpt or source.label
        sections.append(f"{header}\n\n{body}")
    return "\n\n".join(sections)


def _finalize_sources(sources: list[RetrievedSource]) -> list[RetrievedSource]:
    lookup_results = [source for source in sources if source.kind == "lookup_result"]
    tables = [source for source in sources if source.kind == "table"]
    nodes = [source for source in sources if source.kind == "node"]
    ordered = lookup_results + tables + nodes

    finalized: list[RetrievedSource] = []
    seen: set[tuple[str, str]] = set()
    for source in ordered:
        key = (source.kind, source.id)
        if key in seen:
            continue
        seen.add(key)
        finalized.append(source)
        if len(finalized) >= _MAX_SOURCES:
            break
    return finalized


def retrieve_standards_context(
    query: str,
    *,
    reader: StandardsReader,
    task_state_payload: dict[str, Any] | None = None,
) -> RetrievalResult:
    """Find relevant standards nodes/tables and optional deterministic lookup values."""
    text = query.strip()
    if not text:
        return RetrievalResult()

    entries = _build_index(reader)
    boosts = _task_seed_boosts(task_state_payload)
    _apply_boosts(entries, boosts)

    query_tokens = _tokenize(text)
    scored: list[tuple[float, _IndexEntry]] = []
    for entry in entries:
        score = _score_entry(entry, text, query_tokens)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda item: item[0], reverse=True)

    sources: list[RetrievedSource] = []
    seen: set[str] = set()

    for _, entry in scored:
        if len(sources) >= _MAX_SOURCES:
            break
        if entry.kind == "table" and entry.table_id:
            key = f"table:{entry.table_id}"
            if key in seen:
                continue
            seen.add(key)
            loaded = _load_table_source(
                reader,
                entry.table_id,
                node_id=entry.node_id,
                paragraph=entry.paragraph,
            )
            if loaded:
                sources.append(loaded)
        elif entry.kind == "node" and entry.node_id:
            key = f"node:{entry.node_id}"
            if key in seen:
                continue
            seen.add(key)
            loaded = _load_node_source(reader, entry.node_id)
            if loaded:
                sources.append(loaded)
                if entry.table_id and f"table:{entry.table_id}" not in seen and len(sources) < _MAX_SOURCES:
                    table_loaded = _load_table_source(
                        reader,
                        entry.table_id,
                        node_id=entry.node_id,
                        paragraph=entry.paragraph,
                    )
                    if table_loaded:
                        seen.add(f"table:{entry.table_id}")
                        sources.append(table_loaded)

    normalized = _normalize_text(text)
    y_related = any(
        alias in normalized
        for alias in _SYMBOL_ALIASES["y"] + _TABLE_ALIASES.get("table_304_1_1", [])
    )
    if y_related and task_state_payload:
        _maybe_add_y_lookup(reader, task_state_payload, sources)

    finalized = _finalize_sources(sources)
    context_block = _build_context_block(finalized)
    return RetrievalResult(sources=finalized, context_block=context_block)
