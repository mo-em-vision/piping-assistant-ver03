"""Registry of pipe dimension sources across standards packs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_paths import resolve_standard_pack


@dataclass(frozen=True)
class PipeDimensionSourceSpec:
    standard: str
    group: str
    table_id: str
    db_file: str
    yaml_source: str
    default: bool = False

    @property
    def db_relative_path(self) -> str:
        return f"{self.group}/{self.standard}/{self.db_file}"


def pipe_dimensions_registry_path(standards_root: Path) -> Path:
    from engine.reference.knowledge_paths import dimensions_registry_path

    return dimensions_registry_path(standards_root_override=standards_root)


def load_pipe_dimensions_registry(standards_root: Path) -> tuple[str | None, list[PipeDimensionSourceSpec]]:
    from engine.reference.standards_config_db import StandardsConfigDatabase, standards_config_db_path

    config_db = StandardsConfigDatabase(standards_config_db_path(standards_root))
    if config_db.exists:
        default_standard, sources = config_db.load_pipe_dimension_sources()
        if sources:
            if default_standard is None:
                for source in sources:
                    if source.default:
                        default_standard = source.standard
                        break
                if default_standard is None:
                    default_standard = sources[0].standard
            return default_standard, sources

    path = pipe_dimensions_registry_path(standards_root)
    if not path.is_file():
        return None, []

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    default_standard = str(data.get("default_standard", "")).strip() or None
    sources: list[PipeDimensionSourceSpec] = []

    for item in data.get("sources", []) or []:
        if not isinstance(item, dict):
            continue
        standard = str(item.get("standard", "")).strip()
        group = str(item.get("group", "")).strip()
        table_id = str(item.get("table_id", "")).strip()
        db_file = str(item.get("db_file", "pipe_dimensions.db")).strip()
        yaml_source = str(item.get("yaml_source", "")).strip()
        if not standard or not group or not table_id or not yaml_source:
            continue
        sources.append(
            PipeDimensionSourceSpec(
                standard=standard,
                group=group,
                table_id=table_id,
                db_file=db_file,
                yaml_source=yaml_source,
                default=bool(item.get("default", False)),
            )
        )

    if default_standard is None:
        for source in sources:
            if source.default:
                default_standard = source.standard
                break
        if default_standard is None and sources:
            default_standard = sources[0].standard

    return default_standard, sources


def resolve_pipe_dimension_source(
    standards_root: Path,
    standard: str | None = None,
) -> PipeDimensionSourceSpec:
    default_standard, sources = load_pipe_dimensions_registry(standards_root)
    if not sources:
        raise FileNotFoundError(
            f"No pipe dimension sources registered in {pipe_dimensions_registry_path(standards_root)}"
        )

    wanted = (standard or default_standard or "").strip()
    if not wanted:
        raise ValueError("No pipe dimension standard specified and no default is configured")

    for source in sources:
        if source.standard == wanted:
            return source

    raise FileNotFoundError(f"Pipe dimension source not registered: {wanted}")


def resolve_pipe_dimension_db_path(
    standards_root: Path,
    standard: str | None = None,
) -> Path:
    source = resolve_pipe_dimension_source(standards_root, standard)
    pack_root = resolve_standard_pack(standards_root, source.standard)
    return pack_root / source.db_file


def resolve_pipe_dimension_yaml_path(
    standards_root: Path,
    standard: str | None = None,
) -> Path:
    source = resolve_pipe_dimension_source(standards_root, standard)
    pack_root = resolve_standard_pack(standards_root, source.standard)
    return pack_root / source.yaml_source
