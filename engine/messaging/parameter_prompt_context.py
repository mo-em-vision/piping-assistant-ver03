"""Messaging-owned PARAM metadata access for user-facing prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.reference.parameter_keys import (
    canonical_parameter_key,
    load_parameter_node_metadata,
    param_node_id_for_input,
)
from engine.reference.standards_reader import StandardsReader


@dataclass(frozen=True)
class ParameterMetadataContext:
    """Read-only PARAM node fields used to assemble prompts."""

    parameter_id: str
    node_id: str
    name: str | None = None
    question: str | None = None
    description: str | None = None
    canonical_symbol: str | None = None
    allowed_units: tuple[str, ...] = ()
    composer_options: tuple[dict[str, Any], ...] = field(default_factory=tuple)


def parameter_metadata_context(
    reader: StandardsReader | None,
    parameter_id: str,
) -> ParameterMetadataContext | None:
    """Load PARAM metadata through existing reference accessors (read-only)."""
    canonical = canonical_parameter_key(parameter_id)
    node_id = param_node_id_for_input(canonical)
    metadata = load_parameter_node_metadata(node_id)

    if metadata is None and reader is not None:
        try:
            metadata = reader.load(node_id).metadata
        except FileNotFoundError:
            metadata = None

    if metadata is None:
        return None

    question = metadata.get("question")
    description = metadata.get("description")
    name = metadata.get("name")
    symbol = metadata.get("canonical_symbol")

    allowed_units: list[str] = []
    meta_block = metadata.get("metadata") or {}
    if isinstance(meta_block, dict):
        raw_units = meta_block.get("allowed_units") or []
        if isinstance(raw_units, list):
            allowed_units = [str(item) for item in raw_units if item]

    composer_options: list[dict[str, Any]] = []
    raw_options = meta_block.get("composer_options") if isinstance(meta_block, dict) else None
    if isinstance(raw_options, list):
        composer_options = [item for item in raw_options if isinstance(item, dict)]

    return ParameterMetadataContext(
        parameter_id=canonical,
        node_id=node_id,
        name=str(name).strip() if isinstance(name, str) and name.strip() else None,
        question=str(question).strip() if isinstance(question, str) and question.strip() else None,
        description=_normalize_description(description),
        canonical_symbol=str(symbol).strip() if isinstance(symbol, str) and symbol.strip() else None,
        allowed_units=tuple(allowed_units),
        composer_options=tuple(composer_options),
    )


def parameter_prompt_from_metadata(ctx: ParameterMetadataContext | None) -> str | None:
    """Return PARAM question, else trimmed description when useful."""
    if ctx is None:
        return None
    if ctx.question:
        return ctx.question
    if ctx.description and _is_useful_metadata_description(ctx.description):
        return ctx.description
    return None


def _is_useful_metadata_description(text: str) -> bool:
    """Thin PARAM descriptions should fall through to equation/catalog copy."""
    stripped = text.strip()
    if len(stripped) < 80:
        return False
    lowered = stripped.lower()
    if lowered in {
        "internal design gage pressure",
        "sum of the mechanical allowances.",
        "sum of the mechanical allowances",
    }:
        return False
    return True


def report_metadata_gaps(
    parameter_id: str,
    ctx: ParameterMetadataContext | None,
    *,
    required_fields: tuple[str, ...] = ("question", "description"),
) -> list[str]:
    """Report which PARAM fields are missing for prompt assembly."""
    if ctx is None:
        return [f"{param_node_id_for_input(parameter_id)}: node not found"]

    gaps: list[str] = []
    for field_name in required_fields:
        if field_name == "question" and not ctx.question:
            gaps.append(f"{ctx.node_id}: missing question")
        elif field_name == "description" and not ctx.description:
            gaps.append(f"{ctx.node_id}: missing description")
        elif field_name == "canonical_symbol" and not ctx.canonical_symbol:
            gaps.append(f"{ctx.node_id}: missing canonical_symbol")
        elif field_name == "allowed_units" and not ctx.allowed_units:
            gaps.append(f"{ctx.node_id}: missing allowed_units")
    return gaps


def _normalize_description(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split()).strip()
    return text or None
