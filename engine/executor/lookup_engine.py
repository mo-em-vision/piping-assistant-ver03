"""Deterministic table lookup execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.executor.table_registry import resolve_graph_node_table_id
from engine.reference.asme_b31_3_table_ids import TABLE_304_1_1, TABLE_304_1_1_1, TABLE_A_1
from engine.reference.material_catalog_db import standards_root_from_pack_root
from engine.reference.material_resolver import canonical_material_id
from engine.reference.parameter_keys import MATERIAL_GRADE_KEY, read_parameter_value
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


@dataclass(frozen=True)
class TableLookupValue:
    value: float


def _lookup_inputs_with_units(inputs: dict[str, Any]) -> dict[str, Any]:
    from engine.executor.unit_manager import prepare_fact
    from models.fact import Fact, fact_scalar_value, fact_unit

    normalized: dict[str, Any] = {}
    for key, raw in inputs.items():
        if isinstance(raw, Fact):
            target = "f" if key == "design_temperature" else None
            prepared = prepare_fact(raw, target_unit=target)
            normalized[key] = fact_scalar_value(prepared)
            if key == "design_temperature":
                normalized["design_temperature_unit"] = fact_unit(prepared)
        else:
            normalized[key] = raw
    return normalized


_Y_TABLE_REFS = frozenset(
    {
        TABLE_304_1_1_1,
        TABLE_304_1_1,
        "asme_b31.3_table_304_1_1_1",
        "asme_b31.3_table_304_1_1",
        "asme-b313-table-304-1-1-1",
    }
)

class LookupEngine:
    """Execute table lookups defined in standards node metadata."""

    def __init__(self, standards_pack_root: Path) -> None:
        self._pack_root = standards_pack_root
        self._tables_db = StandardsTablesDatabase(resolve_pack_tables_db(standards_pack_root))

    def _resolve_table_ref(self, table_ref: str) -> str:
        """Map graph node ids and aliases to canonical pack table ids."""
        wanted = table_ref.strip()
        if not wanted:
            return wanted
        resolved = self._tables_db.resolve_table_id(wanted)
        if resolved:
            return resolved
        return resolve_graph_node_table_id(wanted)

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
            or "asme-b313-table-A-1"
        ).strip()
        from engine.executor.lookup_rule_schema import TABLE_REF_ALIASES

        table_ref = TABLE_REF_ALIASES.get(table_ref, table_ref)
        normalized = _lookup_inputs_with_units(inputs)
        rule_result = self.execute_rule_lookup(
            table_ref=table_ref,
            rule=str(lookup_config.get("rule") or "by_material_temperature"),
            inputs=normalized,
            returns=[{"parameter": "PARAM-allowable-stress", "symbol": "S"}],
        )
        stress_pa = rule_result.outputs.get("allowable_stress") or rule_result.outputs.get("S")
        if stress_pa is None:
            raise ValueError("allowable_stress was not resolved from table lookup")

        material = str(read_parameter_value(inputs, MATERIAL_GRADE_KEY) or "").strip()
        standards_root = standards_root_from_pack_root(self._pack_root)
        material_id = canonical_material_id(material, standards_root=standards_root) or material
        temp_f = float(rule_result.meta.get("design_temperature_f") or normalized.get("design_temperature", 0))

        trace = LookupTrace(
            table_id=str(rule_result.meta.get("table_id") or table_ref),
            material=material_id,
            design_temperature_f=temp_f,
            allowable_stress_pa=float(stress_pa),
            interpolated=bool(rule_result.meta.get("interpolated")),
            matched_row=rule_result.meta.get("matched_row"),
        )

        calculation = CalculationResult(
            calculation_id=f"{node_id}:lookup",
            inputs={
                MATERIAL_GRADE_KEY: material_id,
                "design_temperature": temp_f,
                "design_temperature_unit": "F",
            },
            steps=[
                CalculationStep(
                    name="table_lookup",
                    inputs={MATERIAL_GRADE_KEY: material_id, "design_temperature_F": temp_f},
                    result=float(stress_pa),
                )
            ],
            final_result=QuantityResult(symbol="S", value=float(stress_pa), unit="Pa"),
            status=CalculationStatus.PASS,
        )

        return LookupResult(calculation=calculation, trace=trace)

    def lookup(self, table_id: str, inputs: dict[str, Any]) -> TableLookupValue:
        """Resolve a scalar from a registered standards table."""
        normalized = _lookup_inputs_with_units(inputs)
        table_ref = self._resolve_table_ref(table_id)

        if table_ref in {TABLE_A_1, "asme_b31.3_A-1", "A-1", "asme-b313-table-A-1"}:
            rule_result = self.execute_rule_lookup(
                table_ref="asme-b313-table-A-1",
                rule="by_material_temperature",
                inputs=normalized,
            )
            value = rule_result.outputs.get("allowable_stress")
            if value is None:
                raise ValueError("allowable_stress was not resolved from Table A-1 lookup")
            return TableLookupValue(value=float(value))

        if table_ref in _Y_TABLE_REFS:
            rule_result = self.execute_rule_lookup(
                table_ref="asme-b313-table-304-1-1-1",
                rule="by_material_group_temperature",
                inputs=normalized,
            )
            value = rule_result.outputs.get("temperature_coefficient_y")
            if value is None:
                value = rule_result.outputs.get("temperature_coefficient_Y")
            if value is None:
                value = rule_result.outputs.get("Y")
            if value is None:
                raise ValueError("temperature_coefficient_Y was not resolved from Table 304.1.1-1 lookup")
            return TableLookupValue(value=float(value))

        if table_ref in {"asme_b36.10", "asme_b36.10m", "B3610-table-2-1", "table-2-1"}:
            rule_result = self.execute_rule_lookup(
                table_ref="B3610-table-2-1",
                rule="by_nps",
                inputs=normalized,
            )
            value = rule_result.outputs.get("outside_diameter")
            if value is None:
                raise ValueError("outside_diameter was not resolved from pipe dimension lookup")
            return TableLookupValue(value=float(value))

        raise ValueError(f"Unsupported lookup table: {table_ref}")

    def execute_rule_lookup(
        self,
        *,
        table_ref: str,
        rule: str,
        inputs: dict[str, Any],
        returns: list[dict[str, Any]] | None = None,
    ) -> "TableRuleLookupResult":
        """Resolve table row(s) by authored rule name; map output columns to parameter keys."""
        from engine.executor.lookup_input_normalizer import normalize_lookup_inputs
        from engine.executor.table_rule_lookup import TableRuleLookupResult, execute_table_rule_lookup

        canonical = normalize_lookup_inputs(inputs)
        normalized = _lookup_inputs_with_units(canonical)
        result = execute_table_rule_lookup(
            standards_pack_root=self._pack_root,
            table_ref=table_ref,
            rule=rule,
            inputs=normalized,
            returns=returns,
        )
        if returns:
            mapped: dict[str, float] = dict(result.outputs)
            for item in returns:
                if not isinstance(item, dict):
                    continue
                symbol = str(item.get("symbol") or "").strip()
                if not symbol:
                    continue
                param_id = str(item.get("parameter") or "").strip()
                from engine.reference.workflow_sidecar import _PARAM_TO_FIELD

                fact_key = _PARAM_TO_FIELD.get(param_id, "")
                if fact_key and fact_key in mapped and symbol not in mapped:
                    mapped[symbol] = mapped[fact_key]
            return TableRuleLookupResult(outputs=mapped, meta=result.meta)
        return result

    def lookup_pipe_dimensions_nps_schedule(self, inputs: dict[str, Any]) -> dict[str, float]:
        """Resolve outside diameter and wall thickness from NPS and schedule."""
        result = self.execute_rule_lookup(
            table_ref="B3610-table-2-1",
            rule="by_nps_schedule",
            inputs=inputs,
        )
        return dict(result.outputs)

