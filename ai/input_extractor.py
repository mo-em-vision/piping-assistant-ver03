"""Deterministic extraction of pipe wall thickness inputs from chat messages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Sequence

from ai.interaction_specs import default_pipe_wall_thickness_decision_interactions
from ai.user_response_extractor import (
    extract_confirmation_intent,
    extract_interaction_responses,
    resolve_pending_value_responses,
)
from engine.executor.unit_manager import normalize_unit
from models.fact import Fact, FactClass, ValidationStatus, fact_from_user_submission, fact_scalar_value, fact_unit
from engine.reference.parameter_keys import MATERIAL_GRADE_KEY
from engine.reference.material_ids import ASTM_A106_GR_B
from engine.reference.parameter_keys import MATERIAL_GRADE_KEY
from engine.graph.node_interaction import NodeInteractionSpec

_DEFAULT_SYMBOL_MAP: dict[str, str] = {
    "P": "design_pressure",
    "D": "outside_diameter",
    "NPS": "nominal_pipe_size",
    "S": "allowable_stress",
    "E": "weld_joint_efficiency",
    "W": "weld_joint_strength_reduction_factor_W",
    "Y": "temperature_coefficient_Y",
    "c": "corrosion_allowance",
}

_PRESSURE_UNITS = frozenset({"psi", "bar", "mpa", "kpa", "pa", "barg"})
_LENGTH_UNITS = frozenset({"in", "inch", "mm", '"'})
_TEMP_UNITS = frozenset({"c", "f", "celsius", "celcius", "fahrenheit", "degc", "degf", "°c", "°f"})

_MATERIAL_LABEL = re.compile(
    r"(?:material|grade)\s*[:=]?\s*"
    r"(astm\s+a\d+(?:\s*(?:gr(?:ade)?\s*)?[a-z])?|sa[\s-]*\d+[a-z]?|a\d+(?:\s*gr(?:ade)?\s*[a-z])?)",
    re.IGNORECASE,
)
_MATERIAL_BARE = re.compile(
    r"\b(astm\s+a\d+(?:\s*(?:gr(?:ade)?\s*)?[a-z])?|sa[\s-]*\d+[a-z]?)\b",
    re.IGNORECASE,
)
_TEMPERATURE = re.compile(
    r"(?:design\s+)?(?:temp(?:erature)?)\s*[:=]?\s*"
    r"(\d+(?:\.\d+)?)\s*"
    r"(c|f|celsius|celcius|fahrenheit|degc|degf|°c|°f)\b",
    re.IGNORECASE,
)
_PRESSURE_LABELED = re.compile(
    r"(?:design\s+)?pressure\s*[:=]?\s*"
    r"(\d+(?:\.\d+)?)\s*"
    r"(\S+)",
    re.IGNORECASE,
)
_DIAMETER = re.compile(
    r"(?:outside\s+)?(?:diameter|od)\s*[:=]?\s*"
    r"(\d+(?:\.\d+)?)\s*"
    r'(in(?:ch(?:es)?)?|mm|")',
    re.IGNORECASE,
)
_NPS = re.compile(
    r"(?:nps|nominal\s+pipe\s+size)\s*[:=]?\s*"
    r'(\d+(?:\.\d+)?(?:\s*[/\-]\s*\d+)?)\s*"?',
    re.IGNORECASE,
)
_NPS_BARE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:inch|in)\s+pipe\b",
    re.IGNORECASE,
)
_DIAMETER_BARE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(?:in(?:ch(?:es)?)?|mm)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InputRejection:
    input_id: str
    raw_value: str
    reason: str


@dataclass
class ExtractionResult:
    extracted: dict[str, Fact] = field(default_factory=dict)
    rejected: list[InputRejection] = field(default_factory=list)


def extract_pipe_wall_thickness_inputs(
    message: str,
    *,
    task_id: str = "",
    pending_interactions: Sequence[NodeInteractionSpec] | None = None,
    pending_value_confirmations: Sequence[NodeInteractionSpec] | None = None,
    existing_inputs: dict[str, Fact] | None = None,
    allowed_fields: frozenset[str] | None = None,
    symbol_map: dict[str, str] | None = None,
) -> ExtractionResult:
    """Parse labeled and bare engineering values from a user message."""
    result = ExtractionResult()
    if not message.strip():
        return result

    existing = existing_inputs or {}
    _extract_symbol_labeled_inputs(
        message,
        result,
        task_id=task_id,
        symbol_map=symbol_map or _DEFAULT_SYMBOL_MAP,
        allowed_fields=allowed_fields,
        existing_inputs=existing,
    )

    interactions = pending_interactions
    if interactions is None:
        interactions = default_pipe_wall_thickness_decision_interactions()
    for input_id, inp in extract_interaction_responses(
        message,
        interactions,
        existing_inputs=existing,
    ).items():
        if allowed_fields is None or input_id in allowed_fields:
            result.extracted[input_id] = inp

    decision_confirmed = extract_confirmation_intent(message) and bool(result.extracted)
    if pending_value_confirmations and not decision_confirmed:
        for input_id, inp in resolve_pending_value_responses(
            message,
            pending_value_confirmations,
            existing,
        ).items():
            if input_id not in result.extracted:
                if allowed_fields is None or input_id in allowed_fields:
                    result.extracted[input_id] = inp

    _extract_straight_section(message, result, allowed_fields=allowed_fields, task_id=task_id)
    _extract_material(message, result, allowed_fields=allowed_fields, task_id=task_id)
    _extract_temperature(message, result, allowed_fields=allowed_fields, task_id=task_id)
    _extract_pressure(message, result, allowed_fields=allowed_fields, task_id=task_id)
    _extract_nps(message, result, allowed_fields=allowed_fields, task_id=task_id)
    _extract_diameter(message, result, allowed_fields=allowed_fields, task_id=task_id)
    for input_id, inp in list(result.extracted.items()):
        result.extracted[input_id] = _normalize_extracted_input(inp, task_id=task_id)
    return result


def _normalize_extracted_input(inp: Fact, *, task_id: str) -> Fact:
    if inp.key != "straight_pipe_section":
        return inp
    if isinstance(fact_scalar_value(inp), bool):
        return inp
    text = str(fact_scalar_value(inp)).strip().lower()
    if text in {"true", "yes", "y", "1"}:
        return fact_from_user_submission(key=inp.key, value=True, unit=fact_unit(inp), task_id=task_id, original_value=inp.original_value)
    if text in {"false", "no", "n", "2"}:
        return fact_from_user_submission(key=inp.key, value=False, unit=fact_unit(inp), task_id=task_id, original_value=inp.original_value)
    return inp


def _field_allowed(field_id: str, allowed_fields: frozenset[str] | None) -> bool:
    return allowed_fields is None or field_id in allowed_fields


def _extract_symbol_labeled_inputs(
    message: str,
    result: ExtractionResult,
    *,
    task_id: str,
    symbol_map: dict[str, str],
    allowed_fields: frozenset[str] | None,
    existing_inputs: dict[str, Fact],
) -> None:
    """Parse symbol-labeled assignments such as ``P: 8 bar, D: 4inch``."""
    symbols = sorted(symbol_map.keys(), key=len, reverse=True)
    if not symbols:
        return
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(s) for s in symbols) + r")\s*[:=]\s*([^,;]+)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(message):
        symbol_key = next(
            (s for s in symbols if s.lower() == match.group(1).lower()),
            match.group(1),
        )
        input_id = symbol_map.get(symbol_key) or symbol_map.get(symbol_key.upper())
        if not input_id or not _field_allowed(input_id, allowed_fields):
            continue
        if input_id in result.extracted:
            continue
        raw_value = match.group(2).strip().rstrip(".")

        parsed = _parse_symbol_assignment(
            symbol_key,
            input_id,
            raw_value,
            existing_inputs.get(input_id),
            task_id=task_id,
        )
        if parsed is None:
            continue
        if isinstance(parsed, InputRejection):
            result.rejected.append(parsed)
            continue
        result.extracted[input_id] = parsed
        if input_id == "outside_diameter" and "d_input_mode" not in result.extracted:
            result.extracted["d_input_mode"] = fact_from_user_submission(key="d_input_mode", value="direct_od", unit="dimensionless", task_id=task_id, original_value="direct_od")
        if input_id == "nominal_pipe_size" and "d_input_mode" not in result.extracted:
            result.extracted["d_input_mode"] = fact_from_user_submission(key="d_input_mode", value="nps_lookup", unit="dimensionless", task_id=task_id, original_value="nps_lookup")


def _parse_symbol_assignment(
    symbol: str,
    input_id: str,
    raw_value: str,
    existing: Fact | None,
    *,
    task_id: str,
) -> Fact | InputRejection | None:
    if input_id == "design_pressure":
        return _parse_pressure_symbol(raw_value, task_id=task_id)
    if input_id == "outside_diameter":
        return _parse_length_symbol(input_id, raw_value, task_id=task_id)
    if input_id == "corrosion_allowance":
        return _parse_length_symbol(input_id, raw_value, task_id=task_id)
    if input_id == "allowable_stress":
        return _parse_stress_symbol(raw_value, task_id=task_id)
    if input_id == "nominal_pipe_size":
        return fact_from_user_submission(
            key=input_id,
            value=raw_value.strip().strip('"'),
            unit="NPS",
            task_id=task_id,
            original_value=raw_value,
            original_unit="NPS",
        )
    if input_id in {
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
    }:
        return _parse_dimensionless_symbol(input_id, raw_value, existing, task_id=task_id)
    return None


def _parse_pressure_symbol(raw_value: str, *, task_id: str) -> Fact | InputRejection | None:
    parts = raw_value.split(None, 1)
    if len(parts) < 2:
        return None
    value = float(parts[0])
    unit_raw = parts[1].rstrip(".,;")
    unit = normalize_unit(unit_raw)
    raw_display = f"{parts[0]} {unit_raw}"
    if unit in _LENGTH_UNITS or unit_raw.lower() in ("in", "inch", "inches", "mm"):
        return InputRejection(
            input_id="design_pressure",
            raw_value=raw_display,
            reason="inch is a length unit, not a pressure unit",
        )
    if unit not in _PRESSURE_UNITS:
        return InputRejection(
            input_id="design_pressure",
            raw_value=raw_display,
            reason="unrecognized pressure unit; please use psi, bar, mpa, kpa, or pa",
        )
    return fact_from_user_submission(key="design_pressure", value=value, unit=unit if unit != "barg" else "bar", task_id=task_id, original_value=value, original_unit=unit)


def _parse_length_symbol(
    input_id: str,
    raw_value: str,
    *,
    task_id: str,
) -> Fact | None:
    parts = raw_value.split(None, 1)
    if len(parts) == 1:
        token = parts[0].lower()
        if token.endswith("inch") or token.endswith("in"):
            num = token.replace("inch", "").replace("in", "").strip()
            if num:
                value = float(num)
                unit = "in"
            else:
                return None
        elif token.endswith("mm"):
            value = float(token.replace("mm", "").strip())
            unit = "mm"
        else:
            return None
    else:
        value = float(parts[0])
        unit = _normalize_length_unit(parts[1])
    return fact_from_user_submission(key=input_id, value=value, unit=unit, task_id=task_id, original_value=value, original_unit=unit)


def _parse_stress_symbol(raw_value: str, *, task_id: str) -> Fact | None:
    parts = raw_value.split(None, 1)
    if len(parts) < 2:
        return None
    value = float(parts[0])
    unit = normalize_unit(parts[1].rstrip(".,;"))
    return fact_from_user_submission(key="allowable_stress", value=value, unit=unit, task_id=task_id, original_value=value, original_unit=unit)


def _parse_dimensionless_symbol(
    input_id: str,
    raw_value: str,
    existing: Fact | None,
    *,
    task_id: str,
) -> Fact | None:
    try:
        value = float(raw_value.split()[0])
    except ValueError:
        return None
    validation_status = ValidationStatus.CONFIRMED
    if existing is not None and existing.fact_class == FactClass.DEFAULT_CONFIRMED:
        if existing.validation.status == ValidationStatus.PENDING:
            validation_status = ValidationStatus.CONFIRMED
    return fact_from_user_submission(
        key=input_id,
        value=value,
        unit="dimensionless",
        task_id=task_id,
        original_value=raw_value,
        validation_status=validation_status,
    )


def _extract_straight_section(
    message: str,
    result: ExtractionResult,
    *,
    task_id: str = "",
    allowed_fields: frozenset[str] | None = None,
) -> None:
    if "straight_pipe_section" in result.extracted:
        return
    if not _field_allowed("straight_pipe_section", allowed_fields):
        return
    lowered = message.strip().lower()
    positive = (
        lowered in {"yes", "y", "true", "straight", "straight section", "straight pipe", "1", "option 1"}
        or "straight section" in lowered
        or "straight pipe" in lowered
    )
    negative = (
        lowered in {"no", "n", "false", "2", "option 2"}
        or "not straight" in lowered
        or "non-straight" in lowered
        or "non straight" in lowered
    )
    if positive and not negative:
        result.extracted["straight_pipe_section"] = fact_from_user_submission(
            key="straight_pipe_section", value=True, unit="dimensionless", task_id=task_id
        )
    elif negative and not positive:
        result.extracted["straight_pipe_section"] = fact_from_user_submission(
            key="straight_pipe_section", value=False, unit="dimensionless", task_id=task_id
        )


def _extract_material(
    message: str,
    result: ExtractionResult,
    *,
    task_id: str = "",
    allowed_fields: frozenset[str] | None = None,
) -> None:
    if MATERIAL_GRADE_KEY in result.extracted:
        return
    if not _field_allowed(MATERIAL_GRADE_KEY, allowed_fields):
        return
    match = _MATERIAL_LABEL.search(message) or _MATERIAL_BARE.search(message)
    if not match:
        return
    raw = match.group(1).strip()
    normalized = _normalize_material(raw)
    result.extracted[MATERIAL_GRADE_KEY] = fact_from_user_submission(
        key=MATERIAL_GRADE_KEY,
        value=normalized,
        unit="dimensionless",
        task_id=task_id,
        original_value=raw,
    )


def _normalize_material(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw.strip())
    upper = text.upper().replace(" ", "")
    if upper in {"ASTMA106", "A106"}:
        return ASTM_A106_GR_B
    if re.fullmatch(r"ASTM\s*A106", text, re.IGNORECASE):
        return ASTM_A106_GR_B
    return text


def _extract_temperature(
    message: str,
    result: ExtractionResult,
    *,
    task_id: str = "",
    allowed_fields: frozenset[str] | None = None,
) -> None:
    if "design_temperature" in result.extracted:
        return
    if not _field_allowed("design_temperature", allowed_fields):
        return
    match = _TEMPERATURE.search(message)
    if not match:
        return
    value = float(match.group(1))
    unit = _normalize_temp_unit(match.group(2))
    result.extracted["design_temperature"] = fact_from_user_submission(key="design_temperature", value=value, unit=unit, task_id=task_id, original_value=value, original_unit=unit)


def _normalize_temp_unit(unit: str) -> str:
    u = normalize_unit(unit)
    if u in ("c", "celsius", "celcius", "degc", "°c"):
        return "C"
    if u in ("f", "fahrenheit", "degf", "°f"):
        return "F"
    return unit.upper()


def _extract_pressure(
    message: str,
    result: ExtractionResult,
    *,
    task_id: str = "",
    allowed_fields: frozenset[str] | None = None,
) -> None:
    if "design_pressure" in result.extracted:
        return
    if not _field_allowed("design_pressure", allowed_fields):
        return
    if _symbol_labeled_present(message, "P"):
        return
    match = _PRESSURE_LABELED.search(message)
    if not match:
        return
    value = float(match.group(1))
    unit_raw = match.group(2).rstrip(".,;")
    unit = normalize_unit(unit_raw)
    raw_display = f"{match.group(1)} {unit_raw}"

    if unit in _LENGTH_UNITS or unit_raw.lower() in ("in", "inch", "inches", "mm"):
        result.rejected.append(
            InputRejection(
                input_id="design_pressure",
                raw_value=raw_display,
                reason="inch is a length unit, not a pressure unit",
            )
        )
        return

    if unit not in _PRESSURE_UNITS:
        result.rejected.append(
            InputRejection(
                input_id="design_pressure",
                raw_value=raw_display,
                reason="unrecognized pressure unit; please use psi, bar, mpa, kpa, or pa",
            )
        )
        return

    result.extracted["design_pressure"] = fact_from_user_submission(key="design_pressure", value=value, unit=unit if unit != "barg" else "bar", task_id=task_id, original_value=value, original_unit=unit)


def _extract_nps(
    message: str,
    result: ExtractionResult,
    *,
    task_id: str = "",
    allowed_fields: frozenset[str] | None = None,
) -> None:
    if "nominal_pipe_size" in result.extracted:
        return
    if not _field_allowed("nominal_pipe_size", allowed_fields):
        return
    match = _NPS.search(message)
    if match:
        result.extracted["nominal_pipe_size"] = fact_from_user_submission(
            key="nominal_pipe_size",
            value=match.group(1).strip(),
            unit="NPS",
            task_id=task_id,
            original_value=match.group(1).strip(),
            original_unit="NPS",
        )
        if "d_input_mode" not in result.extracted:
            result.extracted["d_input_mode"] = fact_from_user_submission(
                key="d_input_mode", value="nps_lookup", unit="dimensionless", task_id=task_id, original_value="nps_lookup"
            )
        return

    bare = _NPS_BARE.search(message)
    if bare:
        result.extracted["nominal_pipe_size"] = fact_from_user_submission(
            key="nominal_pipe_size",
            value=bare.group(1),
            unit="NPS",
            task_id=task_id,
            original_value=bare.group(1),
            original_unit="NPS",
        )
        if "d_input_mode" not in result.extracted:
            result.extracted["d_input_mode"] = fact_from_user_submission(key="d_input_mode", value="nps_lookup", unit="dimensionless", task_id=task_id, original_value="nps_lookup")


def _extract_diameter(
    message: str,
    result: ExtractionResult,
    *,
    task_id: str = "",
    allowed_fields: frozenset[str] | None = None,
) -> None:
    if "outside_diameter" in result.extracted:
        return
    if not _field_allowed("outside_diameter", allowed_fields):
        return
    if _symbol_labeled_present(message, "D"):
        return
    match = _DIAMETER.search(message)
    if match:
        value = float(match.group(1))
        unit = _normalize_length_unit(match.group(2))
        result.extracted["outside_diameter"] = fact_from_user_submission(key="outside_diameter", value=value, unit=unit, task_id=task_id, original_value=value, original_unit=unit)
        if "d_input_mode" not in result.extracted:
            result.extracted["d_input_mode"] = fact_from_user_submission(key="d_input_mode", value="direct_od", unit="dimensionless", task_id=task_id, original_value="direct_od")
        return

    # Bare "4 inch" only when not already rejected as mislabeled pressure
    pressure_span = _PRESSURE_LABELED.search(message)
    for bare in _DIAMETER_BARE.finditer(message):
        if pressure_span and bare.start() >= pressure_span.start() and bare.end() <= pressure_span.end():
            continue
        value = float(bare.group(1))
        unit = _normalize_length_unit(bare.group(0).split()[-1])
        result.extracted["outside_diameter"] = fact_from_user_submission(key="outside_diameter", value=value, unit=unit, task_id=task_id, original_value=value, original_unit=unit)
        if "d_input_mode" not in result.extracted:
            result.extracted["d_input_mode"] = fact_from_user_submission(key="d_input_mode", value="direct_od", unit="dimensionless", task_id=task_id, original_value="direct_od")
        return


def _normalize_length_unit(unit: str) -> str:
    u = normalize_unit(unit.rstrip('"'))
    if u in ("in", "inch", "inches"):
        return "in"
    if u == "mm":
        return "mm"
    return u


def _symbol_labeled_present(message: str, symbol: str) -> bool:
    return bool(
        re.search(
            rf"\b{re.escape(symbol)}\s*[:=]",
            message,
            re.IGNORECASE,
        )
    )
