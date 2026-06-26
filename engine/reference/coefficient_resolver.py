"""Resolve nomenclature coefficients from standards tables and formulas."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from engine.reference.material_catalog_db import material_display_name, standards_root_from_pack_root
from engine.reference.material_resolver import canonical_material_id, resolve_material_table_key
from engine.reference.asme_b31_3_table_ids import (
    TABLE_302_3_5,
    TABLE_304_1_1,
    TABLE_A_1A,
    TABLE_A_1B,
)
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


def temperature_to_fahrenheit(value: float, unit: str = "F") -> float:
    from engine.executor.unit_manager import convert_to_si

    temp_f, _ = convert_to_si(value, unit, target_unit="f")
    return temp_f


def lookup_y_coefficient(
    pack_root: Path,
    *,
    design_temperature: float,
    design_temperature_unit: str = "F",
    material: str | None = None,
) -> tuple[float, bool]:
    """Return Y from Table 304.1.1 at design temperature."""
    from engine.reference.standards_tables import flatten_lookup_table_rows

    table_data = _load_table(pack_root, TABLE_304_1_1)
    temp_f = temperature_to_fahrenheit(design_temperature, design_temperature_unit)
    rows = flatten_lookup_table_rows(table_data)
    if material:
        rows = _filter_y_rows_for_material(rows, material)
    elif rows:
        rows = [row for row in rows if row.get("material_id") == "ferritic_steels"] or rows
    interpolate = bool(table_data.get("interpolation", True))
    value, _, interpolated = interpolate_by_temperature(
        rows,
        temperature_f=temp_f,
        value_key="coefficient_Y",
        interpolate=interpolate,
    )
    return value, interpolated


def _filter_y_rows_for_material(rows: list[dict[str, Any]], material: str) -> list[dict[str, Any]]:
    token = material.strip().lower()
    material_aliases: dict[str, tuple[str, ...]] = {
        "ferritic_steels": ("ferritic", "carbon steel", "carbon_steel", "a106", "sa-106", "sa106"),
        "austenitic_steels": ("austenitic", "stainless", "ss", "304", "316"),
        "nickel_alloys": ("nickel", "inconel", "incoloy", "n06617", "n08800", "n08810", "n08825"),
        "gray_iron": ("gray iron", "cast iron", "grey iron"),
        "other_ductile_metals": ("ductile", "other ductile"),
    }
    for material_id, aliases in material_aliases.items():
        if token == material_id.replace("_", " "):
            return [row for row in rows if row.get("material_id") == material_id]
        if any(alias in token for alias in aliases):
            return [row for row in rows if row.get("material_id") == material_id]
    return [row for row in rows if row.get("material_id") == "ferritic_steels"] or rows


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


def _row_material_token(row: dict[str, Any]) -> str:
    return str(row.get("material_id") or row.get("material", ""))


def lookup_quality_factor(
    pack_root: Path,
    *,
    material: str,
    joint_category: str,
) -> float | None:
    """Look up E from Tables A-1A and A-1B by material and joint category."""
    category = joint_category.strip().lower().replace("-", "_")
    standards_root = standards_root_from_pack_root(pack_root)
    for table_ref in (TABLE_A_1A, TABLE_A_1B):
        table_data = _load_table(pack_root, table_ref)
        rows = table_data.get("rows", []) or []
        material_keys = {_row_material_token(row): row for row in rows}
        material_key = resolve_material_table_key(
            material_keys,
            material,
            standards_root=standards_root,
        )
        if material_key is None:
            continue
        for row in rows:
            row_material = _row_material_token(row)
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
        table_data = _load_table(pack_root, TABLE_302_3_5)
    except FileNotFoundError:
        return None
    rows = table_data.get("rows", []) or []
    if not rows:
        return 1.0
    standards_root = standards_root_from_pack_root(pack_root)
    material_key = resolve_material_table_key(
        {_row_material_token(row): row for row in rows},
        material,
        standards_root=standards_root,
    )
    if material_key is None:
        return 1.0
    temp_f = temperature_to_fahrenheit(design_temperature, design_temperature_unit)
    category = weld_joint_category.strip().lower().replace("-", "_")
    for row in rows:
        row_material = _row_material_token(row)
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
            mat_label = str(mat_value)
            standards_root = standards_root_from_pack_root(pack_root)
            material_id = canonical_material_id(mat_label, standards_root=standards_root)
            if material_id is not None:
                display = material_display_name(standards_root, material_id)
                if display:
                    mat_label = display
            proposed["weld_joint_efficiency"] = (
                e_value,
                f"Tables A-1A/A-1B for {mat_label} ({cat_value})",
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
