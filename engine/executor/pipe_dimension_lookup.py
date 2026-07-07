"""ASME B36.10M and other registered pipe dimension table lookup."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.reference.pack_pipe_dimensions_db import resolve_pack_pipe_dimensions_db
from engine.reference.pipe_dimensions_db import INCH_TO_MM, PipeDimensionsDatabase, PipeScheduleEntry, _nps_sort_key
from engine.reference.pipe_dimensions_registry import (
    load_pipe_dimensions_registry,
    resolve_pipe_dimension_source,
)
from engine.reference.standards_paths import resolve_standard_pack

B36_10_SLUG = "asme_b36.10"
DEFAULT_TABLE = "table-2-1"
DEFAULT_TABLE_YAML = "tables/B3610-table-2-1.yaml"


@dataclass(frozen=True)
class PipeDimensionResult:
    """Resolved pipe dimensions from a registered pipe dimension table."""

    nps: str
    schedule: str | None
    outside_diameter_in: float
    outside_diameter_mm: float
    wall_thickness_in: float | None = None
    wall_thickness_mm: float | None = None
    inner_diameter_in: float | None = None
    inner_diameter_mm: float | None = None
    weight_lb_per_ft: float | None = None
    table_id: str = ""
    standard_slug: str = ""
    interpolated: bool = False


class PipeDimensionLookup:
    """Lookup nominal pipe size and schedule dimensions from registered standards."""

    def __init__(
        self,
        standards_root: Path,
        *,
        standard: str = B36_10_SLUG,
        table_id: str | None = None,
        table_rel: str = DEFAULT_TABLE_YAML,
    ) -> None:
        self._standards_root = standards_root.resolve()
        self._standard = standard
        self._pack_root = resolve_standard_pack(self._standards_root, standard)
        self._table_rel = table_rel
        self._db_path = resolve_pack_pipe_dimensions_db(self._pack_root)

        _, registry_sources = load_pipe_dimensions_registry(self._standards_root)
        if registry_sources:
            source = resolve_pipe_dimension_source(self._standards_root, standard)
            self._table_id = table_id or source.table_id
            self._standard = source.standard
        else:
            self._table_id = table_id or DEFAULT_TABLE

        self._database: PipeDimensionsDatabase | None = None
        self._yaml_table: dict[str, Any] | None = None

        if self._db_path.is_file():
            self._database = PipeDimensionsDatabase(self._db_path)
        else:
            table_path = self._pack_root / table_rel
            if not table_path.exists():
                raise FileNotFoundError(f"Pipe dimension table not found: {table_path}")
            self._yaml_table = yaml.safe_load(table_path.read_text(encoding="utf-8")) or {}
            if table_id:
                self._table_id = table_id
            elif self._yaml_table.get("table_id"):
                self._table_id = str(self._yaml_table["table_id"])

    @property
    def table_id(self) -> str:
        return self._table_id

    @property
    def standard_slug(self) -> str:
        return self._standard

    def list_schedules_for_nps(self, nominal_pipe_size: str) -> list[PipeScheduleEntry]:
        if self._database is not None:
            return self._database.list_schedules_for_nps(self._table_id, nominal_pipe_size)
        return self._list_schedules_for_nps_yaml(nominal_pipe_size)

    def find_nps_by_outside_diameter_mm(
        self,
        outside_diameter_mm: float,
        *,
        tolerance_mm: float = 0.05,
    ) -> str | None:
        if self._database is not None:
            return self._database.find_nps_by_outside_diameter_mm(
                self._table_id,
                outside_diameter_mm,
                tolerance_mm=tolerance_mm,
            )
        return self._find_nps_by_outside_diameter_mm_yaml(
            outside_diameter_mm,
            tolerance_mm=tolerance_mm,
        )

    def lookup(
        self,
        nominal_pipe_size: str,
        *,
        schedule: str | None = None,
    ) -> PipeDimensionResult:
        if self._database is not None:
            row = self._database.lookup(
                self._table_id,
                nominal_pipe_size,
                schedule=schedule,
            )
            return PipeDimensionResult(
                nps=row.nps,
                schedule=row.schedule,
                outside_diameter_in=row.outside_diameter_in,
                outside_diameter_mm=row.outside_diameter_mm,
                wall_thickness_in=row.wall_thickness_in,
                wall_thickness_mm=row.wall_thickness_mm,
                inner_diameter_in=row.inner_diameter_in,
                inner_diameter_mm=row.inner_diameter_mm,
                weight_lb_per_ft=row.weight_lb_per_ft,
                table_id=row.table_id,
                standard_slug=row.standard_slug,
            )

        return self._lookup_yaml(nominal_pipe_size, schedule=schedule)

    def list_nps_sizes(self) -> list[str]:
        if self._database is not None:
            return self._database.list_nps_sizes(self._table_id)
        return self._list_nps_sizes_yaml()

    def _list_schedules_for_nps_yaml(self, nominal_pipe_size: str) -> list[PipeScheduleEntry]:
        table = self._yaml_table or {}
        nps_key = self._resolve_nps_yaml(table, nominal_pipe_size)
        pipes = table.get("pipes", {}) or {}
        pipe_row = pipes[nps_key]
        schedules = pipe_row.get("schedules", {}) or {}
        entries: list[PipeScheduleEntry] = []
        for schedule_key, schedule_row in schedules.items():
            if not isinstance(schedule_row, dict):
                continue
            wall_in = float(schedule_row["wall_thickness_in"])
            wall_mm = float(schedule_row.get("wall_thickness_mm", wall_in * INCH_TO_MM))
            entries.append(
                PipeScheduleEntry(
                    schedule=str(schedule_key),
                    wall_thickness_in=wall_in,
                    wall_thickness_mm=wall_mm,
                )
            )
        return sorted(entries, key=lambda entry: entry.wall_thickness_in)

    def _find_nps_by_outside_diameter_mm_yaml(
        self,
        outside_diameter_mm: float,
        *,
        tolerance_mm: float = 0.05,
    ) -> str | None:
        pipes = (self._yaml_table or {}).get("pipes", {}) or {}
        target = float(outside_diameter_mm)
        for nps_key, pipe_row in pipes.items():
            if not isinstance(pipe_row, dict):
                continue
            od_in = float(pipe_row["outside_diameter_in"])
            od_mm = float(pipe_row.get("outside_diameter_mm", od_in * INCH_TO_MM))
            if abs(od_mm - target) <= tolerance_mm:
                return str(nps_key)
        return None

    def _lookup_yaml(
        self,
        nominal_pipe_size: str,
        *,
        schedule: str | None = None,
    ) -> PipeDimensionResult:
        table = self._yaml_table or {}
        nps_key = self._resolve_nps_yaml(table, nominal_pipe_size)
        pipes = table.get("pipes", {}) or {}
        pipe_row = pipes[nps_key]
        od_in = float(pipe_row["outside_diameter_in"])
        od_mm = float(pipe_row.get("outside_diameter_mm", od_in * INCH_TO_MM))

        schedule_key: str | None = None
        wall_in: float | None = None
        wall_mm: float | None = None
        id_in: float | None = None
        id_mm: float | None = None
        weight: float | None = None

        if schedule is not None:
            schedule_key = self._resolve_schedule_yaml(table, schedule)
            sched_row = self._schedule_row_yaml(pipe_row, schedule_key)
            if sched_row is None:
                raise ValueError(
                    f"Schedule {schedule} not defined for NPS {nps_key} in pipe dimension table"
                )
            wall_in = float(sched_row["wall_thickness_in"])
            wall_mm = float(sched_row.get("wall_thickness_mm", wall_in * INCH_TO_MM))
            if "inner_diameter_in" in sched_row:
                id_in = float(sched_row["inner_diameter_in"])
                id_mm = float(sched_row.get("inner_diameter_mm", id_in * INCH_TO_MM))
            else:
                id_in = od_in - 2.0 * wall_in
                id_mm = id_in * INCH_TO_MM
            if sched_row.get("weight_lb_per_ft") is not None:
                weight = float(sched_row["weight_lb_per_ft"])

        return PipeDimensionResult(
            nps=nps_key,
            schedule=schedule_key,
            outside_diameter_in=od_in,
            outside_diameter_mm=od_mm,
            wall_thickness_in=wall_in,
            wall_thickness_mm=wall_mm,
            inner_diameter_in=id_in,
            inner_diameter_mm=id_mm,
            weight_lb_per_ft=weight,
            table_id=self._table_id,
            standard_slug=self._standard,
        )

    def _list_nps_sizes_yaml(self) -> list[str]:
        pipes = (self._yaml_table or {}).get("pipes", {}) or {}
        return sorted(pipes.keys(), key=_nps_sort_key)

    def _resolve_nps_yaml(self, table: dict[str, Any], nps: str) -> str:
        text = str(nps).strip().strip('"').strip("'")
        aliases = table.get("aliases", {}).get("nps", {}) or {}
        for alias, target in aliases.items():
            if text.lower() == str(alias).lower():
                return str(target)

        normalized = re.sub(r"^\s*nps\s*", "", text, flags=re.IGNORECASE).strip()
        normalized = normalized.replace(" inch", "").replace(" inches", "").replace(" in", "").strip()
        if normalized.endswith('"'):
            normalized = normalized[:-1].strip()

        pipes = table.get("pipes", {}) or {}
        if normalized in pipes:
            return normalized

        for key in pipes:
            if key.lower() == normalized.lower():
                return key

        raise ValueError(f"Nominal pipe size not found in pipe dimension table: {nps}")

    def _resolve_schedule_yaml(self, table: dict[str, Any], schedule: str) -> str:
        text = str(schedule).strip().upper()
        text = re.sub(r"^SCH(?:EDULE)?\s*", "", text).strip()
        aliases = table.get("aliases", {}).get("schedule", {}) or {}
        for alias, target in aliases.items():
            if text == str(alias).upper():
                return str(target)
        return text

    @staticmethod
    def _schedule_row_yaml(pipe_row: dict[str, Any], schedule_key: str) -> dict[str, Any] | None:
        schedules = pipe_row.get("schedules", {}) or {}
        if schedule_key in schedules:
            row = schedules[schedule_key]
            return row if isinstance(row, dict) else None
        upper = schedule_key.upper()
        for key, row in schedules.items():
            if str(key).upper() == upper and isinstance(row, dict):
                return row
        return None
