"""Messaging-owned PARAM metadata access for user-facing prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.reference.parameter_keys import (
    canonical_parameter_key,
    load_parameter_node_metadata,
    param_node_id_for_input,
)
from engine.reference.parameter_metadata import normalize_allowed_units, prepare_parameter_metadata
from engine.reference.standards_reader import StandardsReader
from engine.units.unit_ids import symbol_from_unit_id

_MIN_USEFUL_DESCRIPTION_CHARS = 80


@dataclass(frozen=True)
class ParameterMetadataContext:
    """Read-only PARAM node fields used to assemble prompts."""

    parameter_id: str
    node_id: str
    name: str | None = None
    question: str | None = None
    description: str | None = None
    canonical_symbol: str | None = None
    default_value: Any | None = None
    short_question: str | None = None
    input_examples: tuple[str, ...] = ()
    allowed_units: tuple[str, ...] = ()
    composer_options: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    prompt_use_description: bool = True


def _merge_param_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    return prepare_parameter_metadata(raw)


def _load_normalized_metadata(
    reader: StandardsReader | None,
    node_id: str,
) -> dict[str, Any] | None:
    metadata = load_parameter_node_metadata(node_id)
    if metadata is None and reader is not None:
        try:
            metadata = reader.load(node_id).metadata
        except FileNotFoundError:
            metadata = None
    if metadata is None:
        return None
    return _merge_param_metadata(metadata)


def parameter_metadata_context(
    reader: StandardsReader | None,
    parameter_id: str,
) -> ParameterMetadataContext | None:
    """Load PARAM metadata through normalized reference accessors (read-only)."""
    canonical = canonical_parameter_key(parameter_id)
    node_id = param_node_id_for_input(canonical)
    metadata = _load_normalized_metadata(reader, node_id)

    if metadata is None:
        return None

    question = metadata.get("question")
    description = metadata.get("description")
    name = metadata.get("name") or metadata.get("title")
    symbol = metadata.get("canonical_symbol") or metadata.get("symbol")

    default_value = metadata.get("default_value")
    if default_value is None:
        default_value = metadata.get("default")

    short_question = metadata.get("short_question")
    prompt_use_description = metadata.get("prompt_use_description")
    use_description = True
    if prompt_use_description is False:
        use_description = False

    input_examples: list[str] = []
    raw_examples = metadata.get("input_examples")
    if isinstance(raw_examples, list):
        input_examples = [str(item).strip() for item in raw_examples if str(item).strip()]

    allowed_unit_ids = normalize_allowed_units(metadata)
    allowed_units = tuple(symbol_from_unit_id(unit_id) or unit_id for unit_id in allowed_unit_ids)

    composer_options: list[dict[str, Any]] = []
    raw_options = metadata.get("composer_options")
    if isinstance(raw_options, list):
        composer_options = [item for item in raw_options if isinstance(item, dict)]

    return ParameterMetadataContext(
        parameter_id=canonical,
        node_id=node_id,
        name=str(name).strip() if isinstance(name, str) and name.strip() else None,
        question=str(question).strip() if isinstance(question, str) and question.strip() else None,
        description=_normalize_description(description),
        canonical_symbol=str(symbol).strip() if isinstance(symbol, str) and symbol.strip() else None,
        default_value=default_value,
        short_question=(
            str(short_question).strip()
            if isinstance(short_question, str) and short_question.strip()
            else None
        ),
        input_examples=tuple(input_examples),
        allowed_units=allowed_units,
        composer_options=tuple(composer_options),
        prompt_use_description=use_description,
    )


def parameter_prompt_from_metadata(ctx: ParameterMetadataContext | None) -> str | None:
    """Return PARAM question, else trimmed description when useful."""
    if ctx is None:
        return None
    if ctx.question:
        return ctx.question
    if ctx.description and ctx.prompt_use_description and _is_useful_metadata_description(ctx.description):
        return ctx.description
    return None


def short_prompt_from_metadata(ctx: ParameterMetadataContext | None) -> str | None:
    """Return PARAM short_question or a derived one-line headline."""
    if ctx is None:
        return None
    if ctx.short_question:
        return ctx.short_question
    if not ctx.name:
        return None
    headline = f"Enter {ctx.name}"
    if ctx.canonical_symbol:
        headline += f" ({ctx.canonical_symbol})"
    return headline + "."


def composer_option_label(ctx: ParameterMetadataContext | None, value: str) -> str:
    """Resolve a display label for a composer/interaction option value."""
    normalized = str(value).strip().lower()
    if ctx is not None:
        for option in ctx.composer_options:
            option_value = str(option.get("value", "")).strip().lower()
            if option_value == normalized:
                label = option.get("label")
                if isinstance(label, str) and label.strip():
                    return label.strip()
    return str(value).replace("_", " ").title()


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
        elif field_name == "description":
            if not ctx.description:
                gaps.append(f"{ctx.node_id}: missing description")
            elif len(ctx.description.strip()) < _MIN_USEFUL_DESCRIPTION_CHARS:
                gaps.append(
                    f"{ctx.node_id}: description too short "
                    f"({len(ctx.description.strip())} < {_MIN_USEFUL_DESCRIPTION_CHARS})"
                )
        elif field_name == "canonical_symbol" and not ctx.canonical_symbol:
            gaps.append(f"{ctx.node_id}: missing canonical_symbol")
        elif field_name == "allowed_units" and not ctx.allowed_units:
            gaps.append(f"{ctx.node_id}: missing allowed_units")
    return gaps


def _is_useful_metadata_description(text: str) -> bool:
    """PARAM descriptions should be stable definitions, not one-word placeholders."""
    stripped = text.strip()
    return len(stripped) >= _MIN_USEFUL_DESCRIPTION_CHARS


def _normalize_description(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split()).strip()
    return text or None
