"""Load equation node sidecar files (execution metadata)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from engine.reference.standards_markdown import split_frontmatter

_EXECUTION_KEYS = (
    "variables",
    "steps",
    "executor",
    "execution_function",
    "calculation_module",
    "outputs",
    "equation_id",
    "nomenclature_ref",
    "display",
    "applies_when",
    "paragraph",
)


def equation_sidecar_dir(record_path: Path, node_id: str) -> Path:
    """Directory for sidecars: equation/foo.yaml -> equation/foo/."""
    return record_path.parent / node_id


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    meta, _body = split_frontmatter(text)
    if isinstance(meta, dict) and meta:
        return meta
    loaded = yaml.safe_load(text)
    return loaded if isinstance(loaded, dict) else {}


def merge_equation_sidecar_metadata(
    metadata: dict[str, Any],
    *,
    record_path: Path | None = None,
    node_id: str | None = None,
) -> dict[str, Any]:
    """Merge execution metadata from sidecars or inline flat equation YAML."""
    merged = dict(metadata)
    if record_path is None or not node_id:
        return merged
    if str(merged.get("type", "")) not in {"equation", "validation_rule"}:
        return merged

    sidecar_dir = equation_sidecar_dir(record_path, node_id)
    flat_execution = record_path.parent / f"{node_id}.execution.yaml"

    for path in (sidecar_dir / "execution.yaml", flat_execution):
        if path.is_file():
            data = _load_yaml(path)
            for key in _EXECUTION_KEYS:
                if key in data and data[key]:
                    merged[key] = data[key]
            break

    if record_path.is_file():
        file_meta, _body = split_frontmatter(record_path.read_text(encoding="utf-8"))
        if isinstance(file_meta, dict):
            for key in (*_EXECUTION_KEYS, "equation_number", "paragraph_number"):
                if key in file_meta and file_meta[key]:
                    merged[key] = file_meta[key]

    return merged
