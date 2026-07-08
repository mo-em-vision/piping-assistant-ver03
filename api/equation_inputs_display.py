"""Build equation input tables and variable substitution for display blocks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from engine.messaging.formula_parameter_prompt import classify_formula_parameters
from engine.reference.parameter_keys import (
    MATERIAL_GRADE_KEY,
    active_fact_for_key,
    active_material_grade_fact,
    is_material_grade_parameter,
    parameter_node_description,
)
from engine.reference.parameter_value_source import resolve_input_value_reference
from engine.reference.material_catalog_db import material_display_name
from engine.reference.material_resolver import canonical_material_id
from engine.reference.standards_reader import StandardsReader
from engine.reference.table_metadata import format_table_citation, table_citation_labels
from engine.state.task_facts import active_facts
from models.fact import Fact, FactClass, SourceType, ValidationStatus, fact_scalar_value, fact_unit
from models.task import Task

_HIDDEN_UNITS = frozenset({"dimensionless", ""})
_DEFAULT_STANDARDS_ROOT = Path(__file__).resolve().parent.parent / "knowledge" / "standards"

FORMULA_INPUT_DISPLAY_ROWS: tuple[tuple[str, str], ...] = (
    (MATERIAL_GRADE_KEY, ""),
    ("internal_design_gage_pressure", "P"),
    ("design_temperature", "T"),
    ("nominal_pipe_size", "NPS"),
    ("outside_diameter", "D"),
    ("allowable_stress", "S"),
    ("weld_joint_efficiency", "E"),
    ("weld_joint_strength_reduction_factor_W", "W"),
    ("temperature_coefficient_Y", "Y"),
)

FORMULA_INPUT_STEP_IDS = frozenset(row[0] for row in FORMULA_INPUT_DISPLAY_ROWS)

MAWP_PRESSURE_DESIGN_ROWS: tuple[tuple[str, str], ...] = (
    ("wall_thickness_basis", "basis"),
    ("actual_wall_thickness", "t_actual"),
    ("corrosion_allowance", "c"),
    ("required_wall_thickness", "t"),
)

MAWP_FORMULA_INPUT_DISPLAY_ROWS: tuple[tuple[str, str], ...] = (
    ("actual_wall_thickness", "t_actual"),
    ("corrosion_allowance", "c"),
    ("outside_diameter", "D"),
    ("allowable_stress", "S"),
    ("weld_joint_efficiency", "E"),
    ("weld_joint_strength_reduction_factor_W", "W"),
    ("temperature_coefficient_Y", "Y"),
)

_SYMBOL_TO_INPUT_ID: dict[str, str] = {
    "P": "internal_design_gage_pressure",
    "D": "outside_diameter",
    "NPS": "nominal_pipe_size",
    "S": "allowable_stress",
    "E": "weld_joint_efficiency",
    "W": "weld_joint_strength_reduction_factor_W",
    "Y": "temperature_coefficient_Y",
    "T": "design_temperature",
    "c": "corrosion_allowance",
}

AWAITING_USER_INPUT = "Awaiting user input"

PRIMARY_FORMULA_INPUT_IDS = frozenset(
    {MATERIAL_GRADE_KEY, "internal_design_gage_pressure", "design_temperature"},
)

_ASME_B31_3 = "ASME B31.3"
_ASME_B36_10 = "ASME B36.10"

_STANDARD_LABELS: dict[str, str] = {
    "asme_b31.3": _ASME_B31_3,
    "asme_b36.10": _ASME_B36_10,
}


def _standards_reader(*, standards_root: Path | None = None) -> StandardsReader:
    root = standards_root or _DEFAULT_STANDARDS_ROOT
    return StandardsReader(root, standard="asme_b31.3")


def _table_citation_label(
    table_ref: str,
    *,
    standards_root: Path | None = None,
) -> str:
    reader = _standards_reader(standards_root=standards_root)
    table_number, paragraph_number = table_citation_labels(reader, table_ref)
    return format_table_citation(
        standard_label=_ASME_B31_3,
        table_number=table_number,
        paragraph_number=paragraph_number,
    )


def _format_scalar(value: object) -> str:
    return str(value)


def format_value_with_unit_for_display(value: Any, unit: str | None) -> str | None:
    if value is None:
        return None
    if unit and unit not in _HIDDEN_UNITS:
        normalized = unit.strip()
        if normalized == "Pa" and isinstance(value, (int, float)):
            return f"{float(value) / 1_000_000:g} MPa"
        return f"{_format_scalar(value)} {_format_unit_for_display(normalized)}"
    return _format_scalar(value)


def _format_unit_for_display(unit: str) -> str:
    normalized = unit.strip().lower()
    if normalized == "c":
        return "\u00b0C"
    if normalized == "f":
        return "\u00b0F"
    if normalized == "k":
        return "K"
    return unit


def _fact_has_displayable_value(fact: Fact | None) -> bool:
    if fact is None:
        return False
    if fact_scalar_value(fact) is None:
        return False
    if fact.fact_class == FactClass.DEFAULT_CONFIRMED and fact.validation.status == ValidationStatus.PENDING:
        return False
    return True


def _input_has_displayable_value(fact: Fact | None) -> bool:
    """Legacy alias."""
    return _fact_has_displayable_value(fact)


def _standard_display_label(standard_slug: object) -> str | None:
    if not standard_slug:
        return None
    slug = str(standard_slug).strip().lower()
    return _STANDARD_LABELS.get(slug)


def _input_display_value_from_input(task: Task, input_id: str) -> str | None:
    fact = active_fact_for_key(task, input_id)
    if fact is not None and _fact_has_displayable_value(fact):
        value = fact_scalar_value(fact)
        unit = fact_unit(fact)
        if unit and unit not in _HIDDEN_UNITS:
            return format_value_with_unit_for_display(value, unit)
        return _format_scalar(value)

    return None


def _joint_category_label(task: Task) -> str | None:
    fact = active_fact_for_key(task, "pipe_construction_type")
    if not _fact_has_displayable_value(fact):
        return None
    raw = str(fact_scalar_value(fact)).strip()
    if not raw:
        return None
    return raw.replace("_", " ").replace("-", " ")


def _resolve_material_display(raw: str, *, standards_root: Path | None = None) -> str:
    cleaned = raw.strip()
    if not cleaned:
        return cleaned
    root = standards_root or _DEFAULT_STANDARDS_ROOT
    material_id = canonical_material_id(cleaned, standards_root=root) or cleaned
    label = material_display_name(root, material_id)
    return label or cleaned


def _material_label(task: Task, *, standards_root: Path | None = None) -> str | None:
    fact = active_material_grade_fact(task)
    if not _fact_has_displayable_value(fact):
        return None
    raw = str(fact_scalar_value(fact)).strip()
    if not raw:
        return None
    return _resolve_material_display(raw, standards_root=standards_root)


def _design_temperature_display(task: Task) -> str | None:
    fact = task.fact_store.active_fact("design_temperature")
    if not _fact_has_displayable_value(fact):
        return None
    unit = _format_unit_for_display(str(fact_unit(fact) or "F"))
    return f"{_format_scalar(fact_scalar_value(fact))}{unit}"


def _d_input_mode(task: Task) -> str:
    mode_input = task.fact_store.active_fact("d_input_mode")
    if mode_input is not None and _fact_has_displayable_value(mode_input):
        return str(fact_scalar_value(mode_input))
    return "nps_lookup"


def _uses_nps_for_outside_diameter(task: Task) -> bool:
    if _d_input_mode(task) == "direct_od":
        return False
    if isinstance(task.outputs.get("outside_diameter_lookup"), dict):
        return True
    return _d_input_mode(task) == "nps_lookup"


def _nps_display_label(task: Task) -> str | None:
    nps_input = task.fact_store.active_fact("nominal_pipe_size")
    if nps_input is not None and _fact_has_displayable_value(nps_input):
        original = nps_input.original_value
        if original is not None and str(original).strip():
            return str(original).strip()
        return str(fact_scalar_value(nps_input)).strip()

    lookup = task.outputs.get("outside_diameter_lookup")
    if isinstance(lookup, dict) and lookup.get("nps"):
        return str(lookup["nps"]).strip()

    return None


def _is_table_sourced(task: Task, input_id: str) -> bool:
    fact = active_fact_for_key(task, input_id)
    return (
        fact is not None
        and fact.source.source_type == SourceType.TABLE_LOOKUP
        and _fact_has_displayable_value(fact)
    )


def _skip_formula_input_row(task: Task, input_id: str) -> bool:
    """NPS is collected in the workflow composer and folded into the D row when used."""
    return input_id == "nominal_pipe_size"


def _outside_diameter_display_value(task: Task) -> str | None:
    if _uses_nps_for_outside_diameter(task):
        nps_input = task.fact_store.active_fact("nominal_pipe_size")
        od_input = task.fact_store.active_fact("outside_diameter")
        if not (
            _fact_has_displayable_value(nps_input)
            and _fact_has_displayable_value(od_input)
        ):
            return None
        display = _input_display_value_from_input(task, "outside_diameter")
        if not display:
            return None
        nps_label = _nps_display_label(task)
        lookup = task.outputs.get("outside_diameter_lookup")
        standard_label = None
        if isinstance(lookup, dict):
            standard_label = _standard_display_label(lookup.get("standard"))
        if nps_label and standard_label:
            return f"{display} (NPS: {nps_label}, {standard_label})"
        return display
    return _input_display_value_from_input(task, "outside_diameter")


def _allowable_stress_display_value(task: Task, *, standards_root: Path | None = None) -> str | None:
    stress = task.outputs.get("allowable_stress") or task.outputs.get("S")
    if stress is None:
        return None
    unit = str(task.outputs.get("allowable_stress_unit") or task.outputs.get("S_unit") or "Pa")
    if unit == "Pa":
        display = format_value_with_unit_for_display(stress, "Pa")
    elif unit not in _HIDDEN_UNITS:
        display = f"{_format_scalar(stress)} {unit}"
    else:
        display = _format_scalar(stress)

    lookup = task.outputs.get("allowable_stress_lookup")
    if not isinstance(lookup, dict) or not lookup.get("table_id"):
        return display

    material_input = active_material_grade_fact(task)
    temp_input = task.fact_store.active_fact("design_temperature")
    if not (
        _fact_has_displayable_value(material_input)
        and _fact_has_displayable_value(temp_input)
    ):
        return None

    mat = lookup.get("material")
    temp_f = lookup.get("design_temperature_f")
    if mat is not None and temp_f is not None:
        mat_label = _resolve_material_display(str(mat))
        interp = " (interpolated)" if lookup.get("interpolated") else ""
        display += f" ({_table_citation_label('A-1', standards_root=standards_root)}, {mat_label} @ {temp_f:g} \u00b0F{interp})"
    return display


def _weld_joint_efficiency_display_value(task: Task, *, standards_root: Path | None = None) -> str | None:
    display = _input_display_value_from_input(task, "weld_joint_efficiency")
    if not display:
        return None
    if not _is_table_sourced(task, "weld_joint_efficiency"):
        return display
    if not _fact_has_displayable_value(active_fact_for_key(task, "pipe_construction_type")):
        return None
    joint_category = _joint_category_label(task)
    if not joint_category:
        return None
    return f"{display} ({_table_citation_label('A-2', standards_root=standards_root)} / {_table_citation_label('A-3', standards_root=standards_root)}, {joint_category})"


def _weld_joint_strength_reduction_factor_W_display_value(
    task: Task,
    *,
    standards_root: Path | None = None,
) -> str | None:
    display = _input_display_value_from_input(task, "weld_joint_strength_reduction_factor_W")
    if not display:
        return None
    if not _is_table_sourced(task, "weld_joint_strength_reduction_factor_W"):
        return display
    material = _material_label(task)
    if not material:
        return None
    return f"{display} ({_table_citation_label('302.3.5-1', standards_root=standards_root)}, {material})"


def _temperature_coefficient_Y_display_value(
    task: Task,
    *,
    standards_root: Path | None = None,
) -> str | None:
    display = _input_display_value_from_input(task, "temperature_coefficient_Y")
    if not display:
        return None
    if not _is_table_sourced(task, "temperature_coefficient_Y"):
        return display
    material = _material_label(task, standards_root=standards_root)
    temp_display = _design_temperature_display(task)
    if not material or not temp_display:
        return None
    return f"{display} ({_table_citation_label('table_304_1_1', standards_root=standards_root)}, {material} @ {temp_display})"


def _input_display_value(task: Task, input_id: str, *, standards_root: Path | None = None) -> str | None:
    if is_material_grade_parameter(input_id):
        return _material_label(task, standards_root=standards_root)
    if input_id == "outside_diameter":
        return _outside_diameter_display_value(task)
    if input_id == "allowable_stress":
        return _allowable_stress_display_value(task, standards_root=standards_root)
    if input_id == "weld_joint_efficiency":
        return _weld_joint_efficiency_display_value(task, standards_root=standards_root)
    if input_id == "weld_joint_strength_reduction_factor_W":
        return _weld_joint_strength_reduction_factor_W_display_value(task, standards_root=standards_root)
    if input_id == "temperature_coefficient_Y":
        return _temperature_coefficient_Y_display_value(task, standards_root=standards_root)
    if input_id == "actual_wall_thickness":
        return _actual_wall_thickness_display_value(task)
    if input_id == "pressure_design_thickness":
        value = task.outputs.get("pressure_design_thickness") or task.outputs.get("t")
        if value is None:
            return None
        return format_thickness_result_display(float(value), "mm")
    if input_id == "mawp":
        value = task.outputs.get("mawp") or task.outputs.get("MAWP")
        if value is None:
            return None
        return format_value_with_unit_for_display(float(value) / 1_000_000, "MPa")
    return _input_display_value_from_input(task, input_id)


def _actual_wall_thickness_display_value(task: Task) -> str | None:
    display = _input_display_value_from_input(task, "actual_wall_thickness")
    if not display:
        return None
    lookup = task.outputs.get("outside_diameter_lookup")
    if isinstance(lookup, dict) and lookup.get("wall_thickness_mm") is not None:
        schedule = lookup.get("schedule")
        nps = lookup.get("nps")
        if schedule and nps:
            return f"{display} ({_ASME_B36_10}, NPS {nps} Sch {schedule})"
    return display


def _build_formula_table_rows(
    task: Task,
    rows_spec: tuple[tuple[str, str], ...],
    *,
    reader: StandardsReader | None = None,
) -> list[dict[str, str]]:
    rows: list[dict[str, Any]] = []
    for input_id, symbol in rows_spec:
        if _skip_formula_input_row(task, input_id):
            continue
        display = _input_display_value(task, input_id)
        row: dict[str, str] = {
            "symbol": symbol,
            "definition": parameter_node_description(reader=reader, input_id=input_id),
            "value": display or "",
        }
        if not display and reader is not None:
            value_reference = resolve_input_value_reference(reader, input_id, task)
            if value_reference is not None:
                row["value_reference"] = value_reference
            else:
                row["value"] = AWAITING_USER_INPUT
        elif not display:
            row["value"] = AWAITING_USER_INPUT
        rows.append(row)
    return rows


def build_mawp_pressure_design_input_table(
    task: Task,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    return {
        "columns": [
            {"key": "symbol", "label": "Symbol", "sortable": False},
            {"key": "definition", "label": "Definition", "sortable": False},
            {"key": "value", "label": "Value", "sortable": False},
        ],
        "rows": _build_formula_table_rows(
            task,
            MAWP_PRESSURE_DESIGN_ROWS,
            reader=reader,
        ),
    }


def build_mawp_formula_inputs_input_table(
    task: Task,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    return {
        "columns": [
            {"key": "symbol", "label": "Symbol", "sortable": False},
            {"key": "definition", "label": "Definition", "sortable": False},
            {"key": "value", "label": "Value", "sortable": False},
        ],
        "rows": _build_formula_table_rows(
            task,
            MAWP_FORMULA_INPUT_DISPLAY_ROWS,
            reader=reader,
        ),
    }


def build_formula_inputs_table_rows(
    task: Task,
    *,
    reader: StandardsReader | None = None,
) -> list[dict[str, str]]:
    return _build_formula_table_rows(task, FORMULA_INPUT_DISPLAY_ROWS, reader=reader)


def build_formula_inputs_input_table(
    task: Task,
    *,
    reader: StandardsReader | None = None,
) -> dict[str, Any]:
    return {
        "columns": [
            {"key": "symbol", "label": "Symbol", "sortable": False},
            {"key": "definition", "label": "Definition", "sortable": False},
            {"key": "value", "label": "Value", "sortable": False},
        ],
        "rows": build_formula_inputs_table_rows(
            task,
            reader=reader,
        ),
    }


def primary_formula_inputs_complete(task: Task, planning: dict[str, Any]) -> bool:
    missing = set(planning.get("missing_inputs") or [])
    missing.update(planning.get("missing_assumptions") or [])
    return all(
        active_fact_for_key(task, input_id) is not None
        and _fact_has_displayable_value(active_fact_for_key(task, input_id))
        and input_id not in missing
        for input_id in PRIMARY_FORMULA_INPUT_IDS
    )


def _format_substitution_value(value: float) -> str:
    """Decimal literal safe for LaTeX math (no scientific notation with +)."""
    if value == 0:
        return "0"
    rounded = float(f"{value:.8g}")
    if abs(rounded - round(rounded)) < 1e-9 and abs(rounded) < 1e15:
        return str(int(round(rounded)))
    text = f"{rounded:.8f}".rstrip("0").rstrip(".")
    return text or "0"


def _format_result_thickness(value: float) -> str:
    return f"{round(float(value), 3):.3f}"


def format_thickness_result_display(value: float, unit: str = "mm") -> str:
    return f"{_format_result_thickness(value)} {unit.strip() or 'mm'}"


def build_mawp_substituted_equation(
    *,
    result_value_pa: float,
    variables_si: dict[str, float],
) -> tuple[str, str]:
    s = float(variables_si["S"])
    e = float(variables_si["E"])
    w = float(variables_si["W"])
    t = float(variables_si["t"])
    d = float(variables_si["D"])
    y = float(variables_si["Y"])
    fmt = _format_substitution_value
    numerator = f"2({fmt(s)})({fmt(e)})({fmt(w)})({fmt(t)})"
    denominator = f"({fmt(d)} - 2({fmt(y)})({fmt(t)}))"
    result_mpa = float(result_value_pa) / 1_000_000
    result_text = f"{result_mpa:.4g}"
    display = f"MAWP = {numerator} / {denominator} = {result_text} MPa"
    latex = (
        f"\\mathrm{{MAWP}} = \\frac{{{numerator}}}{{{denominator}}}"
        f" = {result_text}\\ \\mathrm{{MPa}}"
    )
    return display, latex


def build_wall_thickness_substituted_rhs(
    *,
    variables_si: dict[str, float],
) -> str:
    """Return the PD / 2((S)(E)(W) + (P)(Y)) RHS with numeric values substituted."""
    p = float(variables_si["P"])
    d = float(variables_si["D"])
    s = float(variables_si["S"])
    e = float(variables_si["E"])
    w = float(variables_si["W"])
    y = float(variables_si["Y"])
    fmt = _format_substitution_value
    return (
        f"({fmt(p)})({fmt(d)})"
        f" / 2(({fmt(s)})({fmt(e)})({fmt(w)}) + ({fmt(p)})({fmt(y)}))"
    )


def build_wall_thickness_substituted_equation(
    *,
    result_value: float,
    result_unit: str,
    variables_si: dict[str, float],
) -> tuple[str, str]:
    """Return plain display and LaTeX for evaluated t = PD / 2(...) = result."""
    rhs = build_wall_thickness_substituted_rhs(variables_si=variables_si)
    result_text = _format_result_thickness(result_value)
    unit = result_unit.strip() or "mm"
    numerator, denominator = rhs.split(" / ", 1)
    display = f"t = {rhs} = {result_text} {unit}"
    latex = (
        f"t = \\frac{{{numerator.strip()}}}{{{denominator.strip()}}}"
        f" = {result_text}\\ \\mathrm{{{unit}}}"
    )
    return display, latex


def build_minimum_thickness_equation(
    *,
    t_value: float,
    c_value: float | None = None,
    t_m_value: float | None = None,
    unit: str = "mm",
) -> tuple[str, str]:
    """Return display and LaTeX for t_m = t + c, optionally with c and t_m evaluated."""
    t_text = _format_result_thickness(t_value)
    if c_value is None:
        text = f"t_m = {t_text} + c"
        return text, text
    c_text = _format_result_thickness(c_value)
    tm_value = t_m_value if t_m_value is not None else t_value + c_value
    tm_text = _format_result_thickness(tm_value)
    text = f"t_m = {t_text} + {c_text} = {tm_text} {unit.strip() or 'mm'}"
    latex = f"t_m = {t_text} + {c_text} = {tm_text}\\ \\mathrm{{{unit.strip() or 'mm'}}}"
    return text, latex


def _substitute_formula_rhs(rhs: str, values: dict[str, float]) -> str:
    text = rhs
    for symbol in sorted((key for key in values if len(key) > 1), key=len, reverse=True):
        text = text.replace(symbol, _format_substitution_value(values[symbol]))
    if "P" in values and "D" in values and "PD" in text:
        text = text.replace(
            "PD",
            f"({_format_substitution_value(values['P'])})({_format_substitution_value(values['D'])})",
        )
    for symbol in ("P", "D", "S", "E", "W", "Y", "t"):
        if symbol not in values:
            continue
        formatted = _format_substitution_value(values[symbol])
        text = re.sub(rf"(?<![A-Za-z]){re.escape(symbol)}(?![A-Za-z])", formatted, text)
    return text


def build_substituted_formula_display(
    formula_display: str,
    *,
    variables_si: dict[str, float],
    intermediates: dict[str, float],
) -> str:
    """Return the governing equation with numeric values substituted for symbols."""
    values = {**variables_si, **intermediates}
    text = formula_display.strip()
    if " = " not in text:
        return _substitute_formula_rhs(text, values)
    lhs, rhs = text.split(" = ", 1)
    return f"{lhs.strip()} = {_substitute_formula_rhs(rhs.strip(), values)}"


def enrich_equation_variables(
    reader: StandardsReader,
    node_id: str,
    task: Task,
    planning: dict[str, Any],
    variables: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not variables:
        return variables

    missing = list(planning.get("missing_inputs") or [])
    known, _missing = classify_formula_parameters(
        reader,
        node_id,
        task_inputs=active_facts(task),
        missing_input_ids=missing,
    )
    if not known:
        return variables

    known_by_symbol = {item.symbol: item.display_value for item in known}
    enriched: list[dict[str, Any]] = []
    for variable in variables:
        row = dict(variable)
        symbol = str(row.get("symbol", ""))
        if symbol in known_by_symbol:
            row["value"] = known_by_symbol[symbol]
        enriched.append(row)
    return enriched
