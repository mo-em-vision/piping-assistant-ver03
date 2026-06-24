"""ASTM material property table lookup."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.reference.material_catalog_db import resolve_material_id, standards_root_from_pack_root
from engine.reference.material_ids import is_material_id
from engine.reference.pack_tables_db import resolve_pack_tables_db
from engine.reference.standards_paths import resolve_standard_pack
from engine.reference.standards_tables import StandardsTablesDatabase

A106_SLUG = "astm_a106"
A312_SLUG = "astm_a312"
DEFAULT_TABLE = "tables/material_properties.yaml"

_DEFAULT_TABLE_IDS = {
    A106_SLUG: "astm_a106_material_properties",
    A312_SLUG: "astm_a312_material_properties",
}


@dataclass(frozen=True)
class MechanicalProperties:
    test_temperature_f: float
    tensile_strength_min_pa: float
    yield_strength_min_pa: float
    elongation_min_percent: float | None = None
    tensile_strength_min_ksi: float | None = None
    yield_strength_min_ksi: float | None = None
    reduction_of_area_min_percent: float | None = None


@dataclass(frozen=True)
class MaterialPropertiesResult:
    grade: str
    display_name: str
    specification: str
    product_form: str
    mechanical: MechanicalProperties
    chemical_composition: dict[str, Any] = field(default_factory=dict)
    physical_properties: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    table_id: str = ""
    notes: list[str] = field(default_factory=list)


class MaterialPropertiesLookup:
    """Lookup ASTM material grade properties from standards/astm packs."""

    def __init__(
        self,
        standards_root: Path,
        *,
        standard: str = A106_SLUG,
        table_rel: str = DEFAULT_TABLE,
        table_id: str | None = None,
    ) -> None:
        self._standard = standard
        self._pack_root = resolve_standard_pack(standards_root, standard)
        self._tables_db_path = resolve_pack_tables_db(self._pack_root)
        self._tables_db = StandardsTablesDatabase(self._tables_db_path)
        table_ref = table_id or table_rel or _DEFAULT_TABLE_IDS.get(standard, "material_properties")
        table_data = self._tables_db.get_table(table_ref)
        if table_data is None:
            raise FileNotFoundError(
                f"Material properties table not found in {self._tables_db_path}: {table_ref}"
            )
        self._table = table_data

    @property
    def table_id(self) -> str:
        return str(self._table.get("table_id", "material_properties"))

    @property
    def specification(self) -> str:
        return str(self._table.get("standard", self._standard))

    def lookup(
        self,
        grade: str,
        *,
        test_temperature_f: float | None = None,
    ) -> MaterialPropertiesResult:
        grade_key = self._resolve_grade(grade)
        materials = self._table.get("materials", {}) or {}
        material_key = grade_key
        for key, payload in materials.items():
            if str(payload.get("grade_key", key)) == grade_key:
                material_key = key
                break
        row = materials[material_key]
        mech = self._select_mechanical(row, test_temperature_f=test_temperature_f)

        return MaterialPropertiesResult(
            grade=grade_key,
            display_name=str(row.get("display_name", grade_key)),
            specification=str(row.get("specification", self.specification)),
            product_form=str(row.get("product_form", "")),
            mechanical=mech,
            chemical_composition=dict(row.get("chemical_composition", {}) or {}),
            physical_properties=dict(row.get("physical_properties", {}) or {}),
            aliases=[str(item) for item in row.get("aliases", []) or []],
            table_id=self.table_id,
            notes=[str(item) for item in row.get("notes", []) or []],
        )

    def list_grades(self) -> list[str]:
        return sorted((self._table.get("materials", {}) or {}).keys())

    def _resolve_grade(self, grade: str) -> str:
        text = str(grade).strip()
        standards_root = standards_root_from_pack_root(self._pack_root)
        if is_material_id(text) and text in (self._table.get("materials", {}) or {}):
            payload = (self._table.get("materials", {}) or {})[text]
            return str(payload.get("grade_key", text))

        resolved_id = resolve_material_id(standards_root, text)
        materials = self._table.get("materials", {}) or {}
        if resolved_id is not None and resolved_id in materials:
            payload = materials[resolved_id]
            return str(payload.get("grade_key", resolved_id))

        aliases = self._table.get("aliases", {}).get("grade", {}) or {}
        for alias, target in aliases.items():
            if text.lower() == str(alias).lower():
                return str(target)

        normalized = re.sub(r"\s+", " ", text.upper())
        materials = self._table.get("materials", {}) or {}

        if text in materials:
            return text

        for key, row in materials.items():
            if key.upper() == normalized or key.upper().replace(" ", "") == normalized.replace(" ", ""):
                return key
            for alias in row.get("aliases", []) or []:
                if str(alias).upper() == normalized or str(alias).upper().replace(" ", "") == normalized.replace(" ", ""):
                    return key

        raise ValueError(f"Material grade not found in {self.specification}: {grade}")

    def _select_mechanical(
        self,
        row: dict[str, Any],
        *,
        test_temperature_f: float | None,
    ) -> MechanicalProperties:
        mech_block = row.get("mechanical_properties", {}) or {}
        room = mech_block.get("room_temperature")
        if not isinstance(room, dict):
            raise ValueError(f"Room-temperature mechanical properties missing for {row.get('display_name')}")

        if test_temperature_f is None:
            return self._parse_mechanical(room)

        temp_rows = mech_block.get("elevated_temperature", []) or []
        if isinstance(temp_rows, list):
            for entry in temp_rows:
                if not isinstance(entry, dict):
                    continue
                if float(entry.get("test_temperature_f", -1)) == float(test_temperature_f):
                    return self._parse_mechanical(entry)

            if temp_rows:
                closest = min(
                    (entry for entry in temp_rows if isinstance(entry, dict)),
                    key=lambda entry: abs(float(entry.get("test_temperature_f", 0)) - test_temperature_f),
                )
                return self._parse_mechanical(closest)

        return self._parse_mechanical(room)

    @staticmethod
    def _parse_mechanical(data: dict[str, Any]) -> MechanicalProperties:
        tensile = data.get("tensile_strength_min", {}) or {}
        yield_strength = data.get("yield_strength_min", {}) or {}
        return MechanicalProperties(
            test_temperature_f=float(data.get("test_temperature_f", 70)),
            tensile_strength_min_pa=float(tensile.get("pa", tensile.get("value", 0))),
            yield_strength_min_pa=float(yield_strength.get("pa", yield_strength.get("value", 0))),
            elongation_min_percent=(
                float(data["elongation_min_percent"]) if data.get("elongation_min_percent") is not None else None
            ),
            tensile_strength_min_ksi=(
                float(tensile["ksi"]) if tensile.get("ksi") is not None else None
            ),
            yield_strength_min_ksi=(
                float(yield_strength["ksi"]) if yield_strength.get("ksi") is not None else None
            ),
            reduction_of_area_min_percent=(
                float(data["reduction_of_area_min_percent"])
                if data.get("reduction_of_area_min_percent") is not None
                else None
            ),
        )
