"""SQLite-backed pipe dimension tables for registered standards packs."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

INCH_TO_MM = 25.4

_SCHEMA = """
CREATE TABLE IF NOT EXISTS dimension_tables (
    table_id TEXT PRIMARY KEY,
    standard_slug TEXT NOT NULL,
    title TEXT,
    version TEXT,
    source TEXT,
    unit_system TEXT,
    yaml_source TEXT
);

CREATE TABLE IF NOT EXISTS nps_aliases (
    table_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    canonical_nps TEXT NOT NULL,
    PRIMARY KEY (table_id, alias),
    FOREIGN KEY (table_id) REFERENCES dimension_tables(table_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS schedule_aliases (
    table_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    canonical_schedule TEXT NOT NULL,
    PRIMARY KEY (table_id, alias),
    FOREIGN KEY (table_id) REFERENCES dimension_tables(table_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pipe_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id TEXT NOT NULL,
    nps TEXT NOT NULL,
    outside_diameter_in REAL NOT NULL,
    outside_diameter_mm REAL NOT NULL,
    UNIQUE (table_id, nps),
    FOREIGN KEY (table_id) REFERENCES dimension_tables(table_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS schedule_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipe_entry_id INTEGER NOT NULL,
    schedule TEXT NOT NULL,
    wall_thickness_in REAL NOT NULL,
    wall_thickness_mm REAL,
    inner_diameter_in REAL,
    inner_diameter_mm REAL,
    weight_lb_per_ft REAL,
    UNIQUE (pipe_entry_id, schedule),
    FOREIGN KEY (pipe_entry_id) REFERENCES pipe_entries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pipe_entries_table_nps
    ON pipe_entries(table_id, nps);
CREATE INDEX IF NOT EXISTS idx_schedule_entries_pipe
    ON schedule_entries(pipe_entry_id);
"""

_OPTION_QUERIES_COLUMN = "option_queries_json"


def _ensure_option_queries_column(connection: sqlite3.Connection) -> None:
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(dimension_tables)").fetchall()
    }
    if _OPTION_QUERIES_COLUMN not in columns:
        connection.execute(
            f"ALTER TABLE dimension_tables ADD COLUMN {_OPTION_QUERIES_COLUMN} TEXT"
        )


@dataclass(frozen=True)
class PipeScheduleEntry:
    """One schedule row for a nominal pipe size."""

    schedule: str
    wall_thickness_in: float
    wall_thickness_mm: float


@dataclass(frozen=True)
class PipeDimensionRow:
    """Resolved pipe dimensions from a registered dimension table."""

    standard_slug: str
    table_id: str
    nps: str
    schedule: str | None
    outside_diameter_in: float
    outside_diameter_mm: float
    wall_thickness_in: float | None = None
    wall_thickness_mm: float | None = None
    inner_diameter_in: float | None = None
    inner_diameter_mm: float | None = None
    weight_lb_per_ft: float | None = None


class PipeDimensionsDatabase:
    """Read and import pipe dimension tables for one standards pack."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path.resolve()

    @property
    def exists(self) -> bool:
        return self.db_path.is_file()

    def connect(self) -> sqlite3.Connection:
        if not self.exists:
            raise FileNotFoundError(f"Pipe dimensions database not found: {self.db_path}")
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(_SCHEMA)
            _ensure_option_queries_column(connection)

    def import_yaml(
        self,
        yaml_path: Path,
        *,
        standard_slug: str,
        yaml_source: str | None = None,
    ) -> str:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Invalid pipe dimension YAML: {yaml_path}")

        table_id = str(data.get("table_id", yaml_path.stem))
        option_queries = data.get("option_queries")
        option_queries_json = (
            json.dumps(option_queries) if isinstance(option_queries, dict) and option_queries else None
        )
        self.initialize_schema()

        with sqlite3.connect(self.db_path) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            _ensure_option_queries_column(connection)
            connection.execute("DELETE FROM dimension_tables WHERE table_id = ?", (table_id,))
            connection.execute(
                """
                INSERT INTO dimension_tables (
                    table_id, standard_slug, title, version, source, unit_system, yaml_source,
                    option_queries_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    table_id,
                    standard_slug,
                    str(data.get("title", table_id)),
                    str(data.get("version")) if data.get("version") is not None else None,
                    str(data.get("source")) if data.get("source") is not None else None,
                    str(data.get("unit_system")) if data.get("unit_system") is not None else None,
                    yaml_source or str(yaml_path.name),
                    option_queries_json,
                ),
            )

            aliases = data.get("aliases", {}) or {}
            for alias, target in (aliases.get("nps", {}) or {}).items():
                connection.execute(
                    """
                    INSERT INTO nps_aliases (table_id, alias, canonical_nps)
                    VALUES (?, ?, ?)
                    """,
                    (table_id, str(alias), str(target)),
                )
            for alias, target in (aliases.get("schedule", {}) or {}).items():
                connection.execute(
                    """
                    INSERT INTO schedule_aliases (table_id, alias, canonical_schedule)
                    VALUES (?, ?, ?)
                    """,
                    (table_id, str(alias).upper(), str(target)),
                )

            pipes = data.get("pipes", {}) or {}
            for nps_key, pipe_row in pipes.items():
                if not isinstance(pipe_row, dict):
                    continue
                od_in = float(pipe_row["outside_diameter_in"])
                od_mm = float(pipe_row.get("outside_diameter_mm", od_in * INCH_TO_MM))
                cursor = connection.execute(
                    """
                    INSERT INTO pipe_entries (table_id, nps, outside_diameter_in, outside_diameter_mm)
                    VALUES (?, ?, ?, ?)
                    """,
                    (table_id, str(nps_key), od_in, od_mm),
                )
                pipe_entry_id = int(cursor.lastrowid)

                schedules = pipe_row.get("schedules", {}) or {}
                for schedule_key, schedule_row in schedules.items():
                    if not isinstance(schedule_row, dict):
                        continue
                    wall_in = float(schedule_row["wall_thickness_in"])
                    wall_mm = schedule_row.get("wall_thickness_mm")
                    wall_mm_value = (
                        float(wall_mm) if wall_mm is not None else wall_in * INCH_TO_MM
                    )
                    if "inner_diameter_in" in schedule_row:
                        id_in = float(schedule_row["inner_diameter_in"])
                        id_mm = schedule_row.get("inner_diameter_mm")
                        id_mm_value = (
                            float(id_mm) if id_mm is not None else id_in * INCH_TO_MM
                        )
                    else:
                        id_in = od_in - 2.0 * wall_in
                        id_mm_value = id_in * INCH_TO_MM
                    weight = schedule_row.get("weight_lb_per_ft")
                    connection.execute(
                        """
                        INSERT INTO schedule_entries (
                            pipe_entry_id, schedule, wall_thickness_in, wall_thickness_mm,
                            inner_diameter_in, inner_diameter_mm, weight_lb_per_ft
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            pipe_entry_id,
                            str(schedule_key),
                            wall_in,
                            wall_mm_value,
                            id_in,
                            id_mm_value,
                            float(weight) if weight is not None else None,
                        ),
                    )

            connection.commit()

        return table_id

    def list_schedules_for_nps(
        self,
        table_id: str,
        nominal_pipe_size: str,
    ) -> list[PipeScheduleEntry]:
        nps_key = self._resolve_nps(table_id, nominal_pipe_size)
        with self.connect() as connection:
            pipe_row = connection.execute(
                """
                SELECT id
                FROM pipe_entries
                WHERE table_id = ? AND nps = ?
                """,
                (table_id, nps_key),
            ).fetchone()
            if pipe_row is None:
                raise ValueError(f"Nominal pipe size not found: {nominal_pipe_size}")

            rows = connection.execute(
                """
                SELECT schedule, wall_thickness_in, wall_thickness_mm
                FROM schedule_entries
                WHERE pipe_entry_id = ?
                ORDER BY wall_thickness_in
                """,
                (int(pipe_row["id"]),),
            ).fetchall()

        entries: list[PipeScheduleEntry] = []
        for row in rows:
            wall_in = float(row["wall_thickness_in"])
            wall_mm = (
                float(row["wall_thickness_mm"])
                if row["wall_thickness_mm"] is not None
                else wall_in * INCH_TO_MM
            )
            entries.append(
                PipeScheduleEntry(
                    schedule=str(row["schedule"]),
                    wall_thickness_in=wall_in,
                    wall_thickness_mm=wall_mm,
                )
            )
        return entries

    def find_nps_by_outside_diameter_mm(
        self,
        table_id: str,
        outside_diameter_mm: float,
        *,
        tolerance_mm: float = 0.05,
    ) -> str | None:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT nps, outside_diameter_mm
                FROM pipe_entries
                WHERE table_id = ?
                """,
                (table_id,),
            ).fetchall()
        target = float(outside_diameter_mm)
        for row in rows:
            od_mm = float(row["outside_diameter_mm"])
            if abs(od_mm - target) <= tolerance_mm:
                return str(row["nps"])
        return None

    def list_nps_sizes(self, table_id: str) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT nps
                FROM pipe_entries
                WHERE table_id = ?
                ORDER BY nps
                """,
                (table_id,),
            ).fetchall()
        sizes = [str(row["nps"]) for row in rows]
        return sorted(sizes, key=_nps_sort_key)

    def lookup(
        self,
        table_id: str,
        nominal_pipe_size: str,
        *,
        schedule: str | None = None,
    ) -> PipeDimensionRow:
        nps_key = self._resolve_nps(table_id, nominal_pipe_size)
        with self.connect() as connection:
            meta = connection.execute(
                "SELECT standard_slug FROM dimension_tables WHERE table_id = ?",
                (table_id,),
            ).fetchone()
            if meta is None:
                raise ValueError(f"Pipe dimension table not found: {table_id}")

            pipe_row = connection.execute(
                """
                SELECT id, nps, outside_diameter_in, outside_diameter_mm
                FROM pipe_entries
                WHERE table_id = ? AND nps = ?
                """,
                (table_id, nps_key),
            ).fetchone()
            if pipe_row is None:
                raise ValueError(f"Nominal pipe size not found: {nominal_pipe_size}")

            schedule_key: str | None = None
            wall_in: float | None = None
            wall_mm: float | None = None
            id_in: float | None = None
            id_mm: float | None = None
            weight: float | None = None

            if schedule is not None:
                schedule_key = self._resolve_schedule(table_id, schedule)
                sched_row = connection.execute(
                    """
                    SELECT schedule, wall_thickness_in, wall_thickness_mm,
                           inner_diameter_in, inner_diameter_mm, weight_lb_per_ft
                    FROM schedule_entries
                    WHERE pipe_entry_id = ?
                    """,
                    (int(pipe_row["id"]),),
                ).fetchall()
                matched = _match_schedule_row(sched_row, schedule_key)
                if matched is None:
                    raise ValueError(
                        f"Schedule {schedule} not defined for NPS {nps_key}"
                    )
                wall_in = float(matched["wall_thickness_in"])
                wall_mm = (
                    float(matched["wall_thickness_mm"])
                    if matched["wall_thickness_mm"] is not None
                    else wall_in * INCH_TO_MM
                )
                id_in = float(matched["inner_diameter_in"])
                id_mm = (
                    float(matched["inner_diameter_mm"])
                    if matched["inner_diameter_mm"] is not None
                    else id_in * INCH_TO_MM
                )
                if matched["weight_lb_per_ft"] is not None:
                    weight = float(matched["weight_lb_per_ft"])

        return PipeDimensionRow(
            standard_slug=str(meta["standard_slug"]),
            table_id=table_id,
            nps=nps_key,
            schedule=schedule_key,
            outside_diameter_in=float(pipe_row["outside_diameter_in"]),
            outside_diameter_mm=float(pipe_row["outside_diameter_mm"]),
            wall_thickness_in=wall_in,
            wall_thickness_mm=wall_mm,
            inner_diameter_in=id_in,
            inner_diameter_mm=id_mm,
            weight_lb_per_ft=weight,
        )

    def _resolve_nps(self, table_id: str, nps: str) -> str:
        text = str(nps).strip().strip('"').strip("'")
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT canonical_nps
                FROM nps_aliases
                WHERE table_id = ? AND lower(alias) = lower(?)
                """,
                (table_id, text),
            ).fetchone()
            if row is not None:
                return str(row["canonical_nps"])

        normalized = re.sub(r"^\s*nps\s*", "", text, flags=re.IGNORECASE).strip()
        normalized = (
            normalized.replace(" inch", "").replace(" inches", "").replace(" in", "").strip()
        )
        if normalized.endswith('"'):
            normalized = normalized[:-1].strip()

        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT nps
                FROM pipe_entries
                WHERE table_id = ? AND (nps = ? OR lower(nps) = lower(?))
                LIMIT 1
                """,
                (table_id, normalized, normalized),
            ).fetchone()
            if row is not None:
                return str(row["nps"])

        raise ValueError(f"Nominal pipe size not found: {nps}")

    def _resolve_schedule(self, table_id: str, schedule: str) -> str:
        text = str(schedule).strip().upper()
        text = re.sub(r"^SCH(?:EDULE)?\s*", "", text).strip()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT canonical_schedule
                FROM schedule_aliases
                WHERE table_id = ? AND alias = ?
                """,
                (table_id, text),
            ).fetchone()
            if row is not None:
                return str(row["canonical_schedule"])
        return text


def _match_schedule_row(
    rows: list[sqlite3.Row],
    schedule_key: str,
) -> sqlite3.Row | None:
    for row in rows:
        if str(row["schedule"]) == schedule_key:
            return row
    upper = schedule_key.upper()
    for row in rows:
        if str(row["schedule"]).upper() == upper:
            return row
    return None


def _nps_sort_key(nps: str) -> float:
    """Numeric NPS sort key (inches) for increasing pipe size order."""
    total = 0.0
    for part in str(nps).strip().split("-"):
        if "/" in part:
            num, den = part.split("/", 1)
            total += float(num) / float(den)
        else:
            total += float(part)
    return total


def import_pipe_dimensions_yaml(
    db_path: Path,
    yaml_path: Path,
    *,
    standard_slug: str,
    yaml_source: str | None = None,
) -> str:
    """Import one YAML pipe dimension table into a pack database."""
    database = PipeDimensionsDatabase(db_path)
    return database.import_yaml(
        yaml_path,
        standard_slug=standard_slug,
        yaml_source=yaml_source,
    )
