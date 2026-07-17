#!/usr/bin/env python3
"""Reorganize ASME B31.3 nodes into workflows/, paragraph/, and tables/ layout."""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.b313_legacy_aliases import rewrite_b313_references
from engine.reference.standards_markdown import compose_frontmatter, split_frontmatter

PACK = _ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3"
NODES = PACK / "nodes"

PARAGRAPH_SOURCES: dict[str, str] = {
    "302.3.3": "302.3.3-a",
    "302.3.5": "302.3.5-e",
    "304.1.1": "B313-304.1.1",
    "304.1.2": "304.1.2-a",
    "304.1.3": "B313-304.1.3",
    "304.3.1": "B313-304.3.1",
    "304.3.2": "304.3.2-a",
    "304.3.3": "304.3.3-a",
}

TABLE_SOURCES: dict[str, str] = {
    "table-A-1": "B313-table-A-1",
    "table-A-1A": "B313-table-A-1A",
    "table-A-1B": "B313-table-A-1B",
    "table-302-3-3C": "B313-table-302-3-3C",
    "table-302-3-5": "B313-table-302-3-5",
    "table-304-1-1": "B313-table-304-1-1",
    "table-302-3-3C-note1": "B313-note-302-3-3C-1",
    "table-302-3-3C-note2a": "B313-note-302-3-3C-2a",
    "table-302-3-3C-note2b": "B313-note-302-3-3C-2b",
    "table-302-3-3C-note3a": "B313-note-302-3-3C-3a",
    "table-302-3-3C-note3b": "B313-note-302-3-3C-3b",
}

_KIND_BY_OLD_TYPE: dict[str, str] = {
    "definition": "definition",
    "calculation": "calculation",
    "text": "section",
    "requirement": "requirement",
}

DELETE_FOLDERS = [
    "B313-param-c",
    "B313-param-D",
    "B313-param-design_temperature",
    "B313-param-E",
    "B313-param-joint_category",
    "B313-param-material",
    "B313-param-mawp",
    "B313-param-nps",
    "B313-param-P",
    "B313-param-S",
    "B313-param-t",
    "B313-param-t_m",
    "B313-param-W",
    "B313-param-Y",
    "B313-designation-joint-category",
    "B313-designation-material",
    "B313-designation-nps",
    "B313-quantity-diameter",
    "B313-quantity-pressure",
    "B313-quantity-stress",
    "B313-quantity-temperature",
    "B313-quantity-thickness",
    "B313-eq-2-intro",
    "B313-eq-2-result",
    "B313-lookup-allowable-stress",
    "B313-interaction-pressure-loading",
    "B313-MAWP-SECTION",
    "B313-MAWP-CALCULATION",
    "B313-MAWP-PRESSURE-DESIGN",
    "B313-table-A-1-REF",
    "B313-WF-PIPE-WALL-THICKNESS",
    "B313-WF-MAWP",
] + list(PARAGRAPH_SOURCES.values()) + list(TABLE_SOURCES.values())


def _load_node(folder: str) -> tuple[dict[str, Any], str]:
    path = NODES / folder / "node.yaml"
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    metadata, body = split_frontmatter(text)
    return metadata, body


def _dump_yaml(metadata: dict[str, Any], body: str) -> str:
    return compose_frontmatter(metadata, body)


def _rewrite_obj(value: Any) -> Any:
    if isinstance(value, str):
        return rewrite_b313_references(value)
    if isinstance(value, list):
        return [_rewrite_obj(item) for item in value]
    if isinstance(value, dict):
        return {key: _rewrite_obj(item) for key, item in value.items()}
    return value


def _strip_param_defines(meta: dict[str, Any]) -> None:
    defines = meta.get("defines")
    if not isinstance(defines, list):
        return
    meta["defines"] = [item for item in defines if not str(item).startswith("param-") and "param-" not in str(item)]


def _convert_requires(meta: dict[str, Any]) -> None:
    requires = meta.get("requires")
    if not isinstance(requires, list):
        return
    converted: list[Any] = []
    for item in requires:
        if isinstance(item, str) and item.startswith("param-"):
            continue
        if isinstance(item, str) and re.match(r"^param-", rewrite_b313_references(item)):
            converted.append(rewrite_b313_references(item))
        else:
            converted.append(_rewrite_obj(item))
    meta["requires"] = converted


def _paragraph_kind(old_type: str, meta: dict[str, Any]) -> str:
    if meta.get("kind"):
        return str(meta["kind"])
    return _KIND_BY_OLD_TYPE.get(old_type, "section")


def _build_paragraph(new_id: str, folder: str) -> tuple[dict[str, Any], str]:
    meta, body = _load_node(folder)
    old_type = str(meta.get("type", ""))
    meta = _rewrite_obj(meta)
    meta["id"] = new_id
    meta["type"] = "paragraph"
    meta["kind"] = _paragraph_kind(old_type, meta)
    _strip_param_defines(meta)
    _convert_requires(meta)
    if "contains" in meta:
        contains = [c for c in meta.get("contains", []) if "init-text" not in str(c) and "assumption" not in str(c)]
        if contains:
            meta["contains"] = contains
        else:
            meta.pop("contains", None)
    if "calculates" in meta:
        meta["calculates"] = [_rewrite_obj(c) for c in meta.get("calculates", []) if str(c).startswith("param-")]
    body = rewrite_b313_references(body)
    return meta, body


def _build_table(new_id: str, folder: str, *, extra_meta: dict[str, Any] | None = None) -> tuple[dict[str, Any], str]:
    meta, body = _load_node(folder)
    meta = _rewrite_obj(meta)
    meta["id"] = new_id
    if str(meta.get("type")) == "requirement":
        meta["type"] = "text"
        meta["kind"] = "note"
    if extra_meta:
        meta.update(extra_meta)
    body = rewrite_b313_references(body)
    return meta, body


def _build_pipe_wall_workflow() -> tuple[dict[str, Any], str]:
    meta, body = _load_node("B313-WF-PIPE-WALL-THICKNESS")
    interaction_meta, _ = _load_node("B313-interaction-pressure-loading")
    section_meta, section_body = _load_node("B313-304.1.1")

    meta = _rewrite_obj(meta)
    meta["id"] = "WF-PIPE-WALL-THICKNESS"
    meta["anchors_to"] = "304.1.1"
    meta["goal_output"] = "minimum_required_thickness"
    meta.pop("contains", None)
    meta.setdefault("requires", [])

    assumptions = section_meta.get("assumptions") or []
    if assumptions:
        meta["assumptions"] = _rewrite_obj(copy.deepcopy(assumptions))

    interaction = {
        "variable": interaction_meta.get("input_id") or "pressure_loading",
        "mode": interaction_meta.get("mode", "decision"),
        "required": True,
        "required_for_expansion": True,
        "options": interaction_meta.get("options", []),
        "question": interaction_meta.get("question", ""),
    }
    edges = _rewrite_obj(interaction_meta.get("edges") or [])
    meta["interactions"] = [interaction]
    if edges:
        meta["edges"] = edges

    texts = [
        {
            "id": "pipe-wall-init-text",
            "type": "text",
            "kind": "section",
            "role": "initiation",
            "title": str(section_meta.get("display_heading", meta.get("title", ""))).strip(),
            "text": str(meta.get("purpose", "")).strip(),
        },
        {
            "id": "pipe-wall-result-text",
            "type": "text",
            "role": "result_explanation",
            "text": "Minimum required wall thickness t_m has been calculated per §304.1.1 eq. (2).",
        },
    ]
    meta["texts"] = texts
    meta["suggested_workflows"] = ["mawp_design"]

    body = rewrite_b313_references(body)
    return meta, body


def _build_mawp_workflow() -> tuple[dict[str, Any], str]:
    wf_meta, wf_body = _load_node("B313-WF-MAWP")
    section_meta, section_body = _load_node("B313-MAWP-SECTION")
    calc_meta, calc_body = _load_node("B313-MAWP-CALCULATION")
    pressure_meta, pressure_body = _load_node("B313-MAWP-PRESSURE-DESIGN")

    meta = _rewrite_obj(wf_meta)
    meta["id"] = "WF-MAWP"
    meta["anchors_to"] = "304.1.2"
    meta["goal_output"] = "mawp"

    nomenclature = _rewrite_obj(section_meta.get("nomenclature") or [])
    for entry in nomenclature:
        if isinstance(entry, dict) and entry.get("introduced_here"):
            sym = str(entry.get("symbol", ""))
            if sym == "MAWP":
                entry["input_id"] = "mawp"
                entry["introduced_here"] = True

    meta["nomenclature"] = nomenclature
    meta["equations"] = []
    for source in (section_meta, calc_meta, pressure_meta):
        for eq in source.get("equations") or []:
            meta["equations"].append(_rewrite_obj(copy.deepcopy(eq)))
        for sub in source.get("subsections") or []:
            if isinstance(sub, dict):
                for eq in sub.get("equations") or []:
                    meta["equations"].append(_rewrite_obj(copy.deepcopy(eq)))

    meta["depends_on"] = _rewrite_obj(calc_meta.get("depends_on") or [])
    meta["inputs"] = _rewrite_obj(calc_meta.get("inputs") or [])
    meta["outputs"] = _rewrite_obj(calc_meta.get("outputs") or [])
    meta["conditions"] = _rewrite_obj(calc_meta.get("conditions") or [])
    meta["provisional_assumptions"] = _rewrite_obj(calc_meta.get("provisional_assumptions") or [])

    texts = [
        {
            "id": "mawp-init-text",
            "type": "text",
            "role": "initiation",
            "title": str(section_meta.get("display_heading", meta.get("title", ""))).strip(),
            "text": str(section_meta.get("purpose", "")).strip(),
        },
        {
            "id": "mawp-result-text",
            "type": "text",
            "role": "result_explanation",
            "text": "Maximum Allowable Working Pressure (MAWP) has been calculated per §304.1.2.",
        },
    ]
    meta["texts"] = texts
    meta["suggested_workflows"] = ["pipe_wall_thickness_design"]

    body_parts = [
        rewrite_b313_references(wf_body),
        rewrite_b313_references(section_body),
        rewrite_b313_references(calc_body),
        rewrite_b313_references(pressure_body),
    ]
    body = "\n\n".join(part.strip() for part in body_parts if part.strip())
    return meta, body


def _write(path: Path, metadata: dict[str, Any], body: str, *, dry_run: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = _dump_yaml(metadata, body)
    if dry_run:
        print(f"  write {path.relative_to(PACK)} ({len(content)} bytes)")
        return
    path.write_text(content, encoding="utf-8")


def reorganize(*, dry_run: bool) -> dict[str, Any]:
    report: dict[str, Any] = {"written": [], "deleted": []}
    out_nodes = NODES

    if not dry_run:
        for sub in ("workflows", "paragraph", "tables"):
            target = out_nodes / sub
            if target.is_dir():
                shutil.rmtree(target)

    for new_id, folder in PARAGRAPH_SOURCES.items():
        meta, body = _build_paragraph(new_id, folder)
        path = out_nodes / "paragraph" / f"{new_id}.yaml"
        _write(path, meta, body, dry_run=dry_run)
        report["written"].append(str(path.relative_to(PACK)))

    ref_meta, _ = _load_node("B313-table-A-1-REF")
    extra = {
        "table_id": ref_meta.get("table_id"),
        "lookup_keys": ref_meta.get("lookup_keys"),
    }
    meta, body = _build_table("table-A-1", "B313-table-A-1", extra_meta=_rewrite_obj(extra))
    _write(out_nodes / "tables" / "table-A-1.yaml", meta, body, dry_run=dry_run)
    report["written"].append("nodes/tables/table-A-1.yaml")

    for new_id, folder in TABLE_SOURCES.items():
        if new_id == "table-A-1":
            continue
        meta, body = _build_table(new_id, folder)
        path = out_nodes / "tables" / f"{new_id}.yaml"
        _write(path, meta, body, dry_run=dry_run)
        report["written"].append(str(path.relative_to(PACK)))

    pw_meta, pw_body = _build_pipe_wall_workflow()
    _write(out_nodes / "workflows" / "pipe-wall-thickness.yaml", pw_meta, pw_body, dry_run=dry_run)
    report["written"].append("nodes/workflows/pipe-wall-thickness.yaml")

    mawp_meta, mawp_body = _build_mawp_workflow()
    _write(out_nodes / "workflows" / "mawp.yaml", mawp_meta, mawp_body, dry_run=dry_run)
    report["written"].append("nodes/workflows/mawp.yaml")

    for folder in DELETE_FOLDERS:
        path = NODES / folder
        if path.is_dir():
            if dry_run:
                print(f"  delete {path.relative_to(PACK)}")
            else:
                shutil.rmtree(path)
            report["deleted"].append(folder)

    # Remove stray B313-* folders and .py modules under 302.3.5
    for path in sorted(NODES.glob("B313-*")):
        if path.is_dir():
            if dry_run:
                print(f"  delete {path.relative_to(PACK)}")
            else:
                shutil.rmtree(path)
            report["deleted"].append(path.name)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()
    report = reorganize(dry_run=args.dry_run)
    print(f"Written {len(report['written'])} files; deleted {len(report['deleted'])} folders")


if __name__ == "__main__":
    main()
