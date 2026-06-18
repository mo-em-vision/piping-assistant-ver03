"""Deterministic extraction of pipe wall thickness inputs from chat messages."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from engine.executor.unit_manager import normalize_unit
from models.input import EngineeringInput, InputSource

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
    r"(?:outside\s+)?(?:diameter|od|nps)\s*[:=]?\s*"
    r"(\d+(?:\.\d+)?)\s*"
    r'(in(?:ch(?:es)?)?|mm|")',
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
    extracted: dict[str, EngineeringInput] = field(default_factory=dict)
    rejected: list[InputRejection] = field(default_factory=list)


def extract_pipe_wall_thickness_inputs(message: str) -> ExtractionResult:
    """Parse labeled and bare engineering values from a user message."""
    result = ExtractionResult()
    if not message.strip():
        return result

    _extract_material(message, result)
    _extract_temperature(message, result)
    _extract_pressure(message, result)
    _extract_diameter(message, result)
    return result


def _extract_material(message: str, result: ExtractionResult) -> None:
    if "material" in result.extracted:
        return
    match = _MATERIAL_LABEL.search(message) or _MATERIAL_BARE.search(message)
    if not match:
        return
    raw = match.group(1).strip()
    normalized = _normalize_material(raw)
    result.extracted["material"] = EngineeringInput(
        input_id="material",
        value=normalized,
        unit="dimensionless",
        source=InputSource.USER,
        original_value=raw,
    )


def _normalize_material(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw.strip())
    upper = text.upper().replace(" ", "")
    if upper in {"ASTMA106", "A106"}:
        return "SA-106B"
    if re.fullmatch(r"ASTM\s*A106", text, re.IGNORECASE):
        return "SA-106B"
    return text


def _extract_temperature(message: str, result: ExtractionResult) -> None:
    if "design_temperature" in result.extracted:
        return
    match = _TEMPERATURE.search(message)
    if not match:
        return
    value = float(match.group(1))
    unit = _normalize_temp_unit(match.group(2))
    result.extracted["design_temperature"] = EngineeringInput(
        input_id="design_temperature",
        value=value,
        unit=unit,
        source=InputSource.USER,
        original_value=value,
        original_unit=unit,
    )


def _normalize_temp_unit(unit: str) -> str:
    u = normalize_unit(unit)
    if u in ("c", "celsius", "celcius", "degc", "°c"):
        return "C"
    if u in ("f", "fahrenheit", "degf", "°f"):
        return "F"
    return unit.upper()


def _extract_pressure(message: str, result: ExtractionResult) -> None:
    if "design_pressure" in result.extracted:
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

    result.extracted["design_pressure"] = EngineeringInput(
        input_id="design_pressure",
        value=value,
        unit=unit if unit != "barg" else "bar",
        source=InputSource.USER,
        original_value=value,
        original_unit=unit,
    )


def _extract_diameter(message: str, result: ExtractionResult) -> None:
    if "outside_diameter" in result.extracted:
        return
    match = _DIAMETER.search(message)
    if match:
        value = float(match.group(1))
        unit = _normalize_length_unit(match.group(2))
        result.extracted["outside_diameter"] = EngineeringInput(
            input_id="outside_diameter",
            value=value,
            unit=unit,
            source=InputSource.USER,
            original_value=value,
            original_unit=unit,
        )
        return

    # Bare "4 inch" only when not already rejected as mislabeled pressure
    pressure_span = _PRESSURE_LABELED.search(message)
    for bare in _DIAMETER_BARE.finditer(message):
        if pressure_span and bare.start() >= pressure_span.start() and bare.end() <= pressure_span.end():
            continue
        value = float(bare.group(1))
        unit = _normalize_length_unit(bare.group(0).split()[-1])
        result.extracted["outside_diameter"] = EngineeringInput(
            input_id="outside_diameter",
            value=value,
            unit=unit,
            source=InputSource.USER,
            original_value=value,
            original_unit=unit,
        )
        return


def _normalize_length_unit(unit: str) -> str:
    u = normalize_unit(unit.rstrip('"'))
    if u in ("in", "inch", "inches"):
        return "in"
    if u == "mm":
        return "mm"
    return u
