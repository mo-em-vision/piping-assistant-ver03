"""Parameter node metadata helpers (no graph store dependency)."""

from __future__ import annotations

from typing import Any

from engine.units.unit_ids import symbol_from_unit_id, unit_id_from_legacy_symbol

_NESTED_PARAMETER_META_KEYS = frozenset(
    {
        "allowed_units",
        "canonical_unit",
        "unit",
        "composer_input",
        "composer_options",
        "table_options",
        "default",
        "default_value",
        "input_examples",
        "lookup_conditionals",
        "resolution",
        "resolution_branches",
        "user_prompt",
        "prompt_use_description",
    }
)

_LEGACY_PROMPT_FIELDS = frozenset({"question", "short_question"})


def _strip_legacy_prompt_fields(meta: dict[str, Any]) -> None:
    for field in _LEGACY_PROMPT_FIELDS:
        meta.pop(field, None)
    nested = meta.get("metadata")
    if isinstance(nested, dict):
        nested.pop("short_question", None)


def _first_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    for separator in (". ", ".\n"):
        index = stripped.find(separator)
        if index > 0:
            return stripped[: index + 1].strip()
    return stripped


def normalize_user_prompt(metadata: dict[str, Any]) -> dict[str, Any]:
    """Normalize PARAM user-facing prompt metadata to canonical ``user_prompt``."""
    meta = dict(metadata)
    nested = meta.get("metadata")
    nested_short: str | None = None
    if isinstance(nested, dict):
        raw_nested_short = nested.get("short_question")
        if isinstance(raw_nested_short, str) and raw_nested_short.strip():
            nested_short = raw_nested_short.strip()

    raw_user_prompt = meta.get("user_prompt")
    if isinstance(raw_user_prompt, dict):
        prompt = str(raw_user_prompt.get("prompt") or "").strip()
        help_text = raw_user_prompt.get("help_text")
        normalized_help = (
            str(help_text).strip()
            if isinstance(help_text, str) and str(help_text).strip()
            else None
        )
        if prompt:
            meta["user_prompt"] = {"prompt": prompt}
            if normalized_help:
                meta["user_prompt"]["help_text"] = normalized_help
        else:
            meta.pop("user_prompt", None)
        _strip_legacy_prompt_fields(meta)
        return meta

    legacy_question = meta.get("question")
    legacy_short = meta.get("short_question")
    question_text = (
        str(legacy_question).strip()
        if isinstance(legacy_question, str) and str(legacy_question).strip()
        else None
    )
    short_text = (
        str(legacy_short).strip()
        if isinstance(legacy_short, str) and str(legacy_short).strip()
        else nested_short
    )

    if not question_text and not short_text:
        _strip_legacy_prompt_fields(meta)
        return meta

    prompt = short_text or (question_text and _first_sentence(question_text)) or ""
    help_text = question_text if question_text and question_text != prompt else None
    if help_text and short_text and help_text.strip() == short_text.strip():
        help_text = None

    if prompt:
        user_prompt: dict[str, str] = {"prompt": prompt}
        if help_text:
            user_prompt["help_text"] = help_text
        meta["user_prompt"] = user_prompt

    _strip_legacy_prompt_fields(meta)
    return meta


def parameter_user_prompt(metadata: dict[str, Any]) -> dict[str, str] | None:
    """Return normalized ``user_prompt`` mapping when present."""
    user_prompt = metadata.get("user_prompt")
    if not isinstance(user_prompt, dict):
        return None
    prompt = str(user_prompt.get("prompt") or "").strip()
    if not prompt:
        return None
    result = {"prompt": prompt}
    help_text = user_prompt.get("help_text")
    if isinstance(help_text, str) and help_text.strip():
        result["help_text"] = help_text.strip()
    return result


def parameter_prompt_text(metadata: dict[str, Any]) -> str | None:
    """Return the brief PARAM prompt headline from prepared metadata."""
    user_prompt = parameter_user_prompt(metadata)
    if user_prompt is None:
        return None
    return user_prompt["prompt"]


def parameter_help_text(metadata: dict[str, Any]) -> str | None:
    """Return optional PARAM help text from prepared metadata."""
    user_prompt = parameter_user_prompt(metadata)
    if user_prompt is None:
        return None
    return user_prompt.get("help_text")


def parameter_prompt_or_description(metadata: dict[str, Any]) -> str | None:
    """Return PARAM prompt, else description fallback for graph hints."""
    prompt = parameter_prompt_text(metadata)
    if prompt:
        return prompt
    description = metadata.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def _merge_nested_parameter_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Lift composer/runtime fields from nested ``metadata:`` blocks on PARAM nodes."""
    merged = dict(metadata)
    nested = metadata.get("metadata")
    if not isinstance(nested, dict):
        return merged
    for key in _NESTED_PARAMETER_META_KEYS:
        if key in nested and key not in merged:
            merged[key] = nested[key]
    return merged


def _parameter_dimension_id(metadata: dict[str, Any]) -> str | None:
    dimension = metadata.get("dimension")
    if isinstance(dimension, str) and dimension.strip().startswith("DIM-"):
        return dimension.strip()
    for edge in metadata.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        if str(edge.get("type") or "") != "has_dimension":
            continue
        target = str(edge.get("target") or "").strip()
        if target.startswith("DIM-"):
            return target
    return None


def _enrich_parameter_from_dimension(metadata: dict[str, Any]) -> dict[str, Any]:
    """Copy canonical unit and allowed units from a referenced global dimension node."""
    meta = dict(metadata)
    if meta.get("canonical_unit") or meta.get("unit"):
        return meta
    dimension_id = _parameter_dimension_id(meta)
    if not dimension_id:
        return meta

    from engine.reference.graph_edge_schema import dimension_allowed_unit_ids
    from engine.reference.nomenclature_resolver import _load_dimension_node

    dim_meta = _load_dimension_node(dimension_id)
    if dim_meta is None:
        return meta

    raw_canonical = dim_meta.get("canonical_unit")
    if raw_canonical is not None:
        canonical = str(raw_canonical).strip()
        if canonical and canonical.lower() != "null":
            meta.setdefault("canonical_unit", canonical)

    if not meta.get("allowed_units"):
        allowed = dimension_allowed_unit_ids(dim_meta)
        if allowed:
            meta["allowed_units"] = allowed

    return meta


def parameter_defined_in(metadata: dict[str, Any]) -> tuple[str, ...]:
    """Section or definition nodes where this parameter symbol is introduced."""
    defined = metadata.get("defined_in")
    if isinstance(defined, str) and defined.strip():
        return (defined.strip(),)
    if isinstance(defined, list):
        nodes = [str(item).strip() for item in defined if str(item).strip()]
        if nodes:
            return tuple(nodes)
    located = metadata.get("located_in")
    if isinstance(located, str) and located.strip():
        return (located.strip(),)
    if isinstance(located, list):
        nodes = [str(item).strip() for item in located if str(item).strip()]
        if nodes:
            return tuple(nodes)
    introduced = metadata.get("introduced_by")
    if isinstance(introduced, str) and introduced.strip():
        return (introduced.strip(),)
    if isinstance(introduced, list):
        nodes = [str(item).strip() for item in introduced if str(item).strip()]
        if nodes:
            return tuple(nodes)
    return ()


def parameter_concept_id(metadata: dict[str, Any]) -> str | None:
    """Shared engineering concept id when multiple parameter nodes are aliases."""
    concept = metadata.get("concept_id") or metadata.get("concept")
    if concept is None:
        return None
    text = str(concept).strip()
    return text or None


def normalize_allowed_units(metadata: dict[str, Any]) -> list[str]:
    """Normalize parameter allowed_units to canonical UNIT-* ids."""
    raw = metadata.get("allowed_units")
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not item:
            continue
        text = str(item).strip()
        if not text:
            continue
        unit_id = text if text.startswith("UNIT-") else unit_id_from_legacy_symbol(text)
        if unit_id and unit_id not in seen:
            seen.add(unit_id)
            normalized.append(unit_id)
    return normalized


def prepare_parameter_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Normalize parameter node metadata at graph compile time."""
    meta = _merge_nested_parameter_metadata(metadata)
    meta.pop("priority", None)

    if not str(meta.get("symbol") or "").strip():
        canonical_symbol = str(meta.get("canonical_symbol") or "").strip()
        if canonical_symbol:
            meta["symbol"] = canonical_symbol
    if not str(meta.get("title") or "").strip():
        name = str(meta.get("name") or "").strip()
        if name:
            meta["title"] = name

    meta = _enrich_parameter_from_dimension(meta)

    canonical = meta.get("canonical_unit")
    legacy_unit = meta.get("unit")
    if canonical:
        canonical_text = str(canonical).strip()
        meta["canonical_unit"] = canonical_text
        if not legacy_unit:
            meta["unit"] = symbol_from_unit_id(canonical_text)
    elif legacy_unit is not None:
        unit_id = unit_id_from_legacy_symbol(str(legacy_unit))
        if unit_id:
            meta["canonical_unit"] = unit_id

    defined = parameter_defined_in(meta)
    if defined:
        meta["defined_in"] = list(defined)
        meta.setdefault("located_in", list(defined))
    return normalize_user_prompt(meta)


ALLOWED_PARAMETER_ROLES = frozenset({"path_decision"})


def parameter_role(metadata: dict[str, Any] | None) -> str | None:
    """Return authored ``metadata.role`` when present."""
    if not isinstance(metadata, dict):
        return None
    nested = metadata.get("metadata")
    if not isinstance(nested, dict):
        return None
    role = str(nested.get("role") or "").strip()
    return role or None


def is_path_decision_parameter(metadata: dict[str, Any] | None) -> bool:
    return parameter_role(metadata) == "path_decision"


def is_workflow_scoped_parameter(metadata: dict[str, Any] | None) -> bool:
    """Path-decision parameters are scoped to one workflow execution."""
    return is_path_decision_parameter(metadata)
