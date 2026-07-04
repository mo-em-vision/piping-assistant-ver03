"""Repair equation/valrule ids corrupted by substring replacement during migration."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.reference.asme_b313_node_ids import canonical_pack_node_id

PACK = ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3" / "nodes"
KNOWLEDGE = ROOT / "knowledge"


def fix_broken_id(node_id: str) -> str:
    text = str(node_id or "").strip()
    if text.startswith("asme-b313-"):
        return text
    if text.startswith("asme_b313_"):
        return canonical_pack_node_id(text)

    match = re.match(r"^(\d+(?:\.\d+)*)\.eq\.(.+)$", text)
    if match:
        section = match.group(1).replace(".", "-")
        suffix = match.group(2)
        return f"asme-b313-{section}-eq-{suffix}"

    match = re.match(r"^(\d+(?:\.\d+)*)\.valrule[.-](.+)$", text)
    if match:
        section = match.group(1).replace(".", "-")
        suffix = match.group(2)
        return f"asme-b313-{section}-valrule-{suffix}"

    if "." in text and not text[0].isdigit():
        return f"asme-b313-{text.replace('.', '-')}"

    return text


def build_repair_map() -> dict[str, str]:
    repair: dict[str, str] = {}
    for path in PACK.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"^id:\s*(\S+)", text, re.MULTILINE):
            old_id = match.group(1).strip("'\"")
            new_id = fix_broken_id(old_id)
            if new_id != old_id:
                repair[old_id] = new_id
        if path.name.startswith("asme_b313_"):
            stem = path.stem
            repair.setdefault(stem, canonical_pack_node_id(stem))
    return repair


def apply_repair_map(text: str, repair: dict[str, str]) -> str:
    out = text
    for old, new in sorted(repair.items(), key=lambda item: len(item[0]), reverse=True):
        out = re.sub(rf"\b{re.escape(old)}\b", new, out)
    return out


def rename_equation_files(repair: dict[str, str]) -> None:
    for folder in (PACK / "equation", PACK / "validation_rule"):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.yaml"), reverse=True):
            text = path.read_text(encoding="utf-8")
            match = re.search(r"^id:\s*(\S+)", text, re.MULTILINE)
            if not match:
                continue
            node_id = match.group(1).strip("'\"")
            new_path = folder / f"{node_id}.yaml"
            updated = apply_repair_map(text, repair)
            new_path.write_text(updated, encoding="utf-8")
            if new_path != path:
                path.unlink()
            sidecar = path.with_suffix("").parent / path.stem
            if sidecar.is_dir() and sidecar.name != node_id:
                new_sidecar = folder / node_id
                if new_sidecar.exists():
                    continue
                sidecar.rename(new_sidecar)


def main() -> None:
    repair = build_repair_map()
    for path in KNOWLEDGE.rglob("*"):
        if not path.is_file() or path.suffix not in {".yaml", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        updated = apply_repair_map(text, repair)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
    rename_equation_files(repair)
    print("repaired", len(repair), "ids")


if __name__ == "__main__":
    main()
