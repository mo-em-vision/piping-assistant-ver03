"""Deterministic table lookup execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.executor.unit_manager import convert_to_si
from engine.reference.material_catalog_db import standards_root_from_pack_root
from engine.reference.material_resolver import canonical_material_id, resolve_material_table_key
from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.reference.standards_tables import StandardsTablesDatabase
from models.calculation import CalculationResult, CalculationStatus, CalculationStep, QuantityResult


@dataclass
class LookupTrace:
    table_id: str
    material: str
    design_temperature_f: float
    allowable_stress_pa: float
    interpolated: bool = False
    matched_row: dict[str, Any] | None = None


@dataclass
class LookupResult:
    calculation: CalculationResult
    trace: LookupTrace


class LookupEngine:
    """Execute table lookups defined in standards node metadata."""

    def __init__(self, standards_pack_root: Path) -> None:
        self._pack_root = standards_pack_root
        self._tables_db = StandardsTablesDatabase(resolve_pack_tables_db(standards_pack_root))

    def execute_lookup(
        self,
        *,
        node_id: str,
        lookup_config: dict[str, Any],
        inputs: dict[str, Any],
    ) -> LookupResult:
        table_ref = str(
            lookup_config.get("table_id")
            or lookup_config.get("table")
            or ""
        ).strip()
        table_data = self._tables_db.get_table(table_ref)
        if table_data is None:
            raise FileNotFoundError(f"Lookup table not found: {table_ref}")
        material = str(inputs.get("material", "")).strip()
        if not material:
            raise ValueError("material is required for stress lookup")

        standards_root = standards_root_from_pack_root(self._pack_root)
        material_id = canonical_material_id(material, standards_root=standards_root) or material

        temp_value = float(inputs["design_temperature"])
        temp_unit = str(inputs.get("design_temperature_unit", "F"))
        temp_f, _ = convert_to_si(temp_value, temp_unit, target_unit="f")

        interpolation = bool(lookup_config.get("interpolation", table_data.get("interpolation", False)))
        stress_pa, row, interpolated = self._lookup_stress(
            table_data,
            material=material_id,
            temperature_f=temp_f,
            interpolate=interpolation,
            standards_root=standards_root,
        )

        trace = LookupTrace(
            table_id=str(table_data.get("table_id", table_ref)),
            material=material_id,
            design_temperature_f=temp_f,
            allowable_stress_pa=stress_pa,
            interpolated=interpolated,
            matched_row=row,
        )

        calculation = CalculationResult(
            calculation_id=f"{node_id}:lookup",
            inputs={
                "material": material_id,
                "design_temperature": temp_f,
                "design_temperature_unit": "F",
            },
            steps=[
                CalculationStep(
                    name="table_lookup",
                    inputs={"material": material_id, "design_temperature_F": temp_f},
                    result=stress_pa,
                )
            ],
            final_result=QuantityResult(symbol="S", value=stress_pa, unit="Pa"),
            status=CalculationStatus.PASS,
        )

        return LookupResult(calculation=calculation, trace=trace)

    def _lookup_stress(
        self,
        table_data: dict[str, Any],
        *,
        material: str,
        temperature_f: float,
        interpolate: bool,
        standards_root: Path | None = None,
    ) -> tuple[float, dict[str, Any] | None, bool]:
        materials = table_data.get("materials", {}) or {}
        material_key = resolve_material_table_key(
            materials,
            material,
            standards_root=standards_root,
        )
        if material_key is None:
            raise ValueError(f"Material not found in lookup table: {material}")

        rows = materials[material_key].get("rows", [])
        if not rows:
            raise ValueError(f"No rows for material: {material_key}")

        sorted_rows = sorted(rows, key=lambda r: float(r["design_temperature"]))

        for row in sorted_rows:
            if float(row["design_temperature"]) == temperature_f:
                return float(row["allowable_stress"]), row, False

        if not interpolate:
            closest = min(sorted_rows, key=lambda r: abs(float(r["design_temperature"]) - temperature_f))
            return float(closest["allowable_stress"]), closest, False

        below = None
        above = None
        for row in sorted_rows:
            temp = float(row["design_temperature"])
            if temp <= temperature_f:
                below = row
            if temp >= temperature_f and above is None:
                above = row

        if below is None and above is not None:
            return float(above["allowable_stress"]), above, False
        if above is None and below is not None:
            return float(below["allowable_stress"]), below, False
        if below is None or above is None:
            closest = min(sorted_rows, key=lambda r: abs(float(r["design_temperature"]) - temperature_f))
            return float(closest["allowable_stress"]), closest, False

        t0 = float(below["design_temperature"])
        t1 = float(above["design_temperature"])
        if t0 == t1:
            return float(below["allowable_stress"]), below, False

        s0 = float(below["allowable_stress"])
        s1 = float(above["allowable_stress"])
        fraction = (temperature_f - t0) / (t1 - t0)
        stress = s0 + fraction * (s1 - s0)
        return stress, {"design_temperature": temperature_f, "allowable_stress": stress}, True
