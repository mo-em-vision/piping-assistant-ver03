"""Resolve nomenclature coefficients from standards tables and formulas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.reference.standards_tables import StandardsTablesDatabase


def interpolate_by_temperature(
    rows: list[dict[str, Any]],
    *,
    temperature_f: float,
    value_key: str,
    interpolate: bool = True,
) -> tuple[float, dict[str, Any] | None, bool]:
    """Look up a scalar value by temperature with optional linear interpolation."""
    if not rows:
        raise ValueError("No rows available for temperature lookup")

    sorted_rows = sorted(rows, key=lambda r: float(r["design_temperature"]))

    for row in sorted_rows:
        if float(row["design_temperature"]) == temperature_f:
            return float(row[value_key]), row, False

    if not interpolate:
        closest = min(
            sorted_rows,
            key=lambda r: abs(float(r["design_temperature"]) - temperature_f),
        )
        return float(closest[value_key]), closest, False

    below = None
    above = None
    for row in sorted_rows:
        temp = float(row["design_temperature"])
        if temp <= temperature_f:
            below = row
        if temp >= temperature_f and above is None:
            above = row

    if below is None and above is not None:
        return float(above[value_key]), above, False
    if above is None and below is not None:
        return float(below[value_key]), below, False
    if below is None or above is None:
        closest = min(
            sorted_rows,
            key=lambda r: abs(float(r["design_temperature"]) - temperature_f),
        )
        return float(closest[value_key]), closest, False

    t0 = float(below["design_temperature"])
    t1 = float(above["design_temperature"])
    if t0 == t1:
        return float(below[value_key]), below, False

    v0 = float(below[value_key])
    v1 = float(above[value_key])
    fraction = (temperature_f - t0) / (t1 - t0)
    value = v0 + fraction * (v1 - v0)
    return value, {"design_temperature": temperature_f, value_key: value}, True


def _tables_db(pack_root: Path) -> StandardsTablesDatabase:
    return StandardsTablesDatabase(resolve_pack_tables_db(pack_root))


def _load_table(pack_root: Path, table_ref: str) -> dict[str, Any]:
    data = _tables_db(pack_root).get_table(table_ref)
    if data is None:
        raise FileNotFoundError(f"Lookup table not found: {table_ref}")
    return data


def _normalize_material(material: str) -> str:
    return material.strip().upper().replace(" ", "")


def _resolve_material_key(materials: dict[str, Any], material: str) -> str | None:
    normalized = _normalize_material(material)
    for key in materials:
        if key.upper().replace(" ", "") == normalized:
            return key
    aliases = {
        "A106B": "SA-106B",
        "SA106B": "SA-106B",
        "A106-B": "A106-B",
        "SA105": "SA-105",
    }
    alias = aliases.get(normalized)
    if alias and alias in materials:
        return alias
    return None


def temperature_to_fahrenheit(value: float, unit: str = "F") -> float:
    from engine.executor.unit_manager import convert_to_si

    temp_f, _ = convert_to_si(value, unit, target_unit="f")
    return temp_f


def lookup_y_coefficient(
    pack_root: Path,
    *,
    design_temperature: float,
    design_temperature_unit: str = "F",
) -> tuple[float, bool]:
    """Return Y from Table 304.1.1 at design temperature."""
    table_data = _load_table(pack_root, "table_304_1_1")
    temp_f = temperature_to_fahrenheit(design_temperature, design_temperature_unit)
    rows = table_data.get("rows", []) or []
    interpolate = bool(table_data.get("interpolation", True))
    value, _, interpolated = interpolate_by_temperature(
        rows,
        temperature_f=temp_f,
        value_key="coefficient_Y",
        interpolate=interpolate,
    )
    return value, interpolated


def compute_thick_wall_y(*, inside_diameter: float, outside_diameter: float, corrosion_allowance: float = 0.0) -> float:
    """Thick-wall Y per §304.1.1(b): Y = (d + 2c) / (D + d + 2c)."""
    d = inside_diameter
    d_val = d + 2.0 * corrosion_allowance
    denom = outside_diameter + d + 2.0 * corrosion_allowance
    if denom == 0:
        raise ValueError("Cannot compute thick-wall Y with zero denominator")
    return d_val / denom


def inside_diameter_from_od_and_thickness(outside_diameter: float, thickness: float) -> float:
    return outside_diameter - 2.0 * thickness


def lookup_quality_factor(
    pack_root: Path,
    *,
    material: str,
    joint_category: str,
) -> float | None:
    """Look up E from Tables A-1A and A-1B by material and joint category."""
    material_key = _normalize_material(material)
    category = joint_category.strip().lower().replace("-", "_")
    for table_ref in ("A-1A", "A-1B"):
        table_data = _load_table(pack_root, table_ref)
        for row in table_data.get("rows", []) or []:
            row_material = _normalize_material(str(row.get("material", "")))
            row_category = str(row.get("joint_category", "")).strip().lower().replace("-", "_")
            if row_material == material_key and row_category == category:
                return float(row["quality_factor_E"])
    return None


def lookup_w_factor(
    pack_root: Path,
    *,
    material: str,
    design_temperature: float,
    design_temperature_unit: str = "F",
    weld_joint_category: str = "seamless",
) -> float | None:
    """Look up W from Table 302.3.5 when rows are available; otherwise return 1.0."""
    try:
        table_data = _load_table(pack_root, "302.3.5")
    except FileNotFoundError:
        return None
    rows = table_data.get("rows", []) or []
    if not rows:
        return 1.0
    material_key = _resolve_material_key(
        {str(row.get("material", "")): row for row in rows},
        material,
    )
    if material_key is None:
        return 1.0
    temp_f = temperature_to_fahrenheit(design_temperature, design_temperature_unit)
    category = weld_joint_category.strip().lower().replace("-", "_")
    for row in rows:
        row_material = str(row.get("material", ""))
        row_category = str(row.get("weld_joint_category", "")).strip().lower().replace("-", "_")
        if row_material == material_key and row_category == category:
            return float(row.get("weld_strength_reduction_W", row.get("W", 1.0)))
    value_key = "weld_strength_reduction_W"
    if value_key not in rows[0]:
        value_key = "W"
    try:
        value, _, _ = interpolate_by_temperature(
            rows,
            temperature_f=temp_f,
            value_key=value_key,
            interpolate=bool(table_data.get("interpolation", True)),
        )
        return value
    except (ValueError, KeyError):
        return 1.0


def _thin_wall_assumed(existing_inputs: dict[str, Any]) -> bool:
    thin_wall = existing_inputs.get("thin_wall")
    if thin_wall is None:
        return True
    raw = thin_wall.value if hasattr(thin_wall, "value") else thin_wall
    return str(raw).strip().lower() in {"true", "1", "yes"}


def propose_coefficient_defaults(
    pack_root: Path,
    *,
    existing_inputs: dict[str, Any],
) -> dict[str, tuple[float, str]]:
    """Propose table-derived defaults for Y, E, and W when inputs are available."""
    proposed: dict[str, tuple[float, str]] = {}

    temp = existing_inputs.get("design_temperature")
    if temp is not None and _thin_wall_assumed(existing_inputs):
        temp_unit = "F"
        raw_temp = temp
        if hasattr(temp, "value"):
            raw_temp = temp.value
            temp_unit = getattr(temp, "unit", "F") or "F"
        try:
            y_value, _ = lookup_y_coefficient(
                pack_root,
                design_temperature=float(raw_temp),
                design_temperature_unit=str(temp_unit),
            )
            proposed["temperature_coefficient"] = (
                y_value,
                "Table 304.1.1 at design temperature (thin-wall, t < D/6)",
            )
        except (ValueError, FileNotFoundError):
            pass

    material = existing_inputs.get("material")
    joint_category = existing_inputs.get("joint_category")
    if material is not None and joint_category is not None:
        mat_value = material.value if hasattr(material, "value") else material
        cat_value = joint_category.value if hasattr(joint_category, "value") else joint_category
        try:
            e_value = lookup_quality_factor(
                pack_root,
                material=str(mat_value),
                joint_category=str(cat_value),
            )
        except (ValueError, FileNotFoundError):
            e_value = None
        if e_value is not None:
            proposed["weld_joint_efficiency"] = (
                e_value,
                f"Tables A-1A/A-1B for {mat_value} ({cat_value})",
            )

    if material is not None and temp is not None:
        mat_value = material.value if hasattr(material, "value") else material
        raw_temp = temp.value if hasattr(temp, "value") else temp
        temp_unit = getattr(temp, "unit", "F") if hasattr(temp, "unit") else "F"
        cat_value = "seamless"
        if joint_category is not None:
            cat_value = (
                joint_category.value if hasattr(joint_category, "value") else joint_category
            )
        try:
            w_value = lookup_w_factor(
                pack_root,
                material=str(mat_value),
                design_temperature=float(raw_temp),
                design_temperature_unit=str(temp_unit or "F"),
                weld_joint_category=str(cat_value),
            )
        except (ValueError, FileNotFoundError):
            w_value = None
        if w_value is not None:
            proposed["weld_strength_reduction"] = (
                w_value,
                "Table 302.3.5 per §302.3.5(e)",
            )

    return proposed
