"""Merge equation execution sidecars into flat equation node YAML files."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from engine.reference.standards_markdown import split_frontmatter

_ROOT = Path(__file__).resolve().parents[1]
_EQ_DIR = _ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3" / "nodes" / "equation"

_INLINE_EXECUTION_KEYS = (
    "variables",
    "steps",
    "executor",
    "execution_function",
    "calculation_module",
    "outputs",
    "equation_id",
    "nomenclature_ref",
)


def _load_sidecar(path: Path) -> dict:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    meta, _body = split_frontmatter(text)
    if isinstance(meta, dict) and meta:
        return meta
    loaded = yaml.safe_load(text)
    return loaded if isinstance(loaded, dict) else {}


def _equation_number(node_id: str) -> str | None:
    match = re.search(r"-eq-(.+)$", node_id)
    if match:
        return match.group(1)
    return None


def _paragraph_number(meta: dict, sidecar: dict) -> str | None:
    explicit = str(meta.get("paragraph_number") or "").strip()
    if explicit:
        return explicit
    legacy = str(sidecar.get("paragraph") or "").strip()
    if legacy:
        return legacy.split(",", 1)[0].strip()
    authority = meta.get("authority") or {}
    if isinstance(authority, dict):
        authorized = authority.get("authorized_by") or []
        if authorized:
            first = str(authorized[0]).strip()
            if first:
                return first
    return None


def _dump_frontmatter(meta: dict) -> str:
    dumped = yaml.safe_dump(
        meta,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )
    return f"---\n{dumped}---\n"


def flatten_equation_nodes(*, remove_sidecars: bool = True) -> list[str]:
    updated: list[str] = []
    for path in sorted(_EQ_DIR.glob("asme-b313-*.yaml")):
        node_id = path.stem
        sidecar_dir = _EQ_DIR / node_id
        flat_sidecar = _EQ_DIR / f"{node_id}.execution.yaml"
        sidecar_path = sidecar_dir / "execution.yaml"
        if sidecar_path.is_file():
            sidecar = _load_sidecar(sidecar_path)
        elif flat_sidecar.is_file():
            sidecar = _load_sidecar(flat_sidecar)
        else:
            sidecar = {}

        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        if not isinstance(meta, dict):
            continue

        equation_number = str(meta.get("equation_number") or "").strip() or _equation_number(node_id)
        if equation_number:
            meta["equation_number"] = equation_number

        paragraph_number = _paragraph_number(meta, sidecar)
        if paragraph_number:
            meta["paragraph_number"] = paragraph_number

        for key in _INLINE_EXECUTION_KEYS:
            if key in sidecar and sidecar[key]:
                meta[key] = sidecar[key]

        path.write_text(_dump_frontmatter(meta) + (body or ""), encoding="utf-8")
        updated.append(path.name)

        if remove_sidecars:
            if sidecar_dir.is_dir():
                shutil.rmtree(sidecar_dir)
            if flat_sidecar.is_file():
                flat_sidecar.unlink()

    return updated


if __name__ == "__main__":
    names = flatten_equation_nodes()
    print(f"Updated {len(names)} equation nodes:")
    for name in names:
        print(f"  - {name}")
