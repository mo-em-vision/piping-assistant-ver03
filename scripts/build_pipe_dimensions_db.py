#!/usr/bin/env python3
"""Build pipe dimension SQLite databases from registered YAML sources."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.pipe_dimensions_db import import_pipe_dimensions_yaml
from engine.reference.pipe_dimensions_registry import load_pipe_dimensions_registry
from engine.reference.standards_paths import resolve_standard_pack


def build_all(*, standards_root: Path | None = None) -> list[Path]:
    root = (standards_root or (_ROOT / "standards")).resolve()
    _, sources = load_pipe_dimensions_registry(root)
    if not sources:
        raise FileNotFoundError(f"No pipe dimension sources in {root / 'pipe_dimensions' / 'registry.yaml'}")

    built: list[Path] = []
    for source in sources:
        pack_root = resolve_standard_pack(root, source.standard)
        yaml_path = pack_root / source.yaml_source
        if not yaml_path.is_file():
            raise FileNotFoundError(f"Pipe dimension YAML not found: {yaml_path}")

        db_path = pack_root / source.db_file
        if db_path.exists():
            db_path.unlink()

        table_id = import_pipe_dimensions_yaml(
            db_path,
            yaml_path,
            standard_slug=source.standard,
            yaml_source=source.yaml_source,
        )
        print(f"Built {db_path} ({source.standard}, table {table_id})")
        built.append(db_path)

    return built


def build_pack(standard: str, *, standards_root: Path | None = None) -> Path:
    root = (standards_root or (_ROOT / "standards")).resolve()
    _, sources = load_pipe_dimensions_registry(root)
    for source in sources:
        if source.standard != standard:
            continue
        pack_root = resolve_standard_pack(root, source.standard)
        yaml_path = pack_root / source.yaml_source
        db_path = pack_root / source.db_file
        if db_path.exists():
            db_path.unlink()
        import_pipe_dimensions_yaml(
            db_path,
            yaml_path,
            standard_slug=source.standard,
            yaml_source=source.yaml_source,
        )
        print(f"Built {db_path}")
        return db_path
    raise FileNotFoundError(f"Pipe dimension source not registered: {standard}")


if __name__ == "__main__":
    build_all()
