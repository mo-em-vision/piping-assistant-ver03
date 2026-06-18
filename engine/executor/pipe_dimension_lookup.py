"""ASME B36.10M pipe dimension table lookup."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_paths import resolve_standard_pack

B36_10_SLUG = "asme_b36.10"
DEFAULT_TABLE = "tables/welded_seamless_pipe_dimensions.yaml"
INCH_TO_MM = 25.4


@dataclass(frozen=True)
class PipeDimensionResult:
    """Resolved pipe dimensions from ASME B36.10M sample table."""

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
    interpolated: bool = False


class PipeDimensionLookup:
    """Lookup nominal pipe size and schedule dimensions from ASME B36.10 tables."""

    def __init__(
        self,
        standards_root: Path,
        *,
        standard: str = B36_10_SLUG,
        table_rel: str = DEFAULT_TABLE,
    ) -> None:
        self._pack_root = resolve_standard_pack(standards_root, standard)
        self._table_path = self._pack_root / table_rel
        if not self._table_path.exists():
            raise FileNotFoundError(f"Pipe dimension table not found: {self._table_path}")
        self._table = yaml.safe_load(self._table_path.read_text(encoding="utf-8")) or {}

    @property
    def table_id(self) -> str:
        return str(self._table.get("table_id", "welded_seamless_pipe_dimensions"))

    def lookup(
        self,
        nominal_pipe_size: str,
        *,
        schedule: str | None = None,
    ) -> PipeDimensionResult:
        nps_key = self._resolve_nps(nominal_pipe_size)
        pipes = self._table.get("pipes", {}) or {}
        if nps_key not in pipes:
            raise ValueError(f"Nominal pipe size not found in B36.10 table: {nominal_pipe_size}")

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
            schedule_key = self._resolve_schedule(schedule)
            sched_row = self._schedule_row(pipe_row, schedule_key)
            if sched_row is None:
                raise ValueError(
                    f"Schedule {schedule} not defined for NPS {nps_key} in B36.10 table"
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
            table_id=self.table_id,
        )

    def list_nps_sizes(self) -> list[str]:
        pipes = self._table.get("pipes", {}) or {}
        return sorted(pipes.keys(), key=self._nps_sort_key)

    def _resolve_nps(self, nps: str) -> str:
        text = str(nps).strip().strip('"').strip("'")
        aliases = self._table.get("aliases", {}).get("nps", {}) or {}
        for alias, target in aliases.items():
            if text.lower() == str(alias).lower():
                return str(target)

        normalized = re.sub(r"^\s*nps\s*", "", text, flags=re.IGNORECASE).strip()
        normalized = normalized.replace(" inch", "").replace(" inches", "").replace(" in", "").strip()
        if normalized.endswith('"'):
            normalized = normalized[:-1].strip()

        pipes = self._table.get("pipes", {}) or {}
        if normalized in pipes:
            return normalized

        for key in pipes:
            if key.lower() == normalized.lower():
                return key

        raise ValueError(f"Nominal pipe size not found in B36.10 table: {nps}")

    def _resolve_schedule(self, schedule: str) -> str:
        text = str(schedule).strip().upper()
        text = re.sub(r"^SCH(?:EDULE)?\s*", "", text).strip()
        aliases = self._table.get("aliases", {}).get("schedule", {}) or {}
        for alias, target in aliases.items():
            if text == str(alias).upper():
                return str(target)
        return text

    @staticmethod
    def _schedule_row(pipe_row: dict[str, Any], schedule_key: str) -> dict[str, Any] | None:
        schedules = pipe_row.get("schedules", {}) or {}
        if schedule_key in schedules:
            row = schedules[schedule_key]
            return row if isinstance(row, dict) else None
        upper = schedule_key.upper()
        for key, row in schedules.items():
            if str(key).upper() == upper and isinstance(row, dict):
                return row
        return None

    @staticmethod
    def _nps_sort_key(nps: str) -> tuple[int, float]:
        if "/" in nps:
            parts = nps.split("-")
            total = 0.0
            for part in parts:
                if "/" in part:
                    num, den = part.split("/", 1)
                    total += float(num) / float(den)
                else:
                    total += float(part)
            return (0, total)
        try:
            return (1, float(nps))
        except ValueError:
            return (2, 0.0)
