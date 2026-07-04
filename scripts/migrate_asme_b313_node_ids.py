"""Migrate knowledge YAML to asme-b313- node id prefix."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.reference.asme_b313_node_ids import (
    canonical_pack_node_id,
    is_bare_paragraph_id,
    qualify_cross_pack_ref,
)

PACK_NODES = ROOT / "knowledge" / "standards" / "asme" / "asme_b31.3" / "nodes"
GLOBAL = ROOT / "knowledge" / "global"


def collect_tokens() -> set[str]:
    tokens: set[str] = set()
    pattern = re.compile(r"\b(?:asme_b313_[A-Za-z0-9_]+|B313-[A-Za-z0-9.-]+)\b")
    for base in (PACK_NODES, GLOBAL):
        for path in base.rglob("*.yaml"):
            text = path.read_text(encoding="utf-8")
            tokens.update(pattern.findall(text))
            for match in re.finditer(r"^id:\s*(\S+)", text, re.MULTILINE):
                tokens.add(match.group(1).strip("'\""))
    return tokens


def build_mappings(tokens: set[str]) -> tuple[dict[str, str], dict[str, str]]:
    from engine.reference.asme_b313_node_ids import resolve_qualified_paragraph_ref

    pack_map: dict[str, str] = {}
    global_map: dict[str, str] = {}
    for old in sorted(tokens, key=len, reverse=True):
        if is_bare_paragraph_id(old):
            pack_map[old] = old
            continue
        if old.startswith("asme_b313_") and re.match(r"asme_b313_\d", old):
            qualified = qualify_cross_pack_ref(old)
            bare = resolve_qualified_paragraph_ref(old) or resolve_qualified_paragraph_ref(qualified)
            if bare:
                pack_map[old] = bare
                global_map[old] = qualified
            continue
        new = canonical_pack_node_id(old)
        pack_map[old] = new
        global_map[old] = new
    return pack_map, global_map


def apply_mapping(text: str, mapping: dict[str, str]) -> str:
    out = text
    for old, new in sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True):
        if old == new:
            continue
        out = re.sub(rf"\b{re.escape(old)}\b", new, out)
    return out


def rename_files(pack_map: dict[str, str]) -> None:
    for path in sorted(PACK_NODES.rglob("*.yaml"), reverse=True):
        new_name = path.name
        for old, new in sorted(pack_map.items(), key=lambda item: len(item[0]), reverse=True):
            if old in new_name and old != new:
                new_name = new_name.replace(old, new)
        if new_name == path.name:
            continue
        new_path = path.with_name(new_name)
        new_path.parent.mkdir(parents=True, exist_ok=True)
        path.rename(new_path)


def main() -> None:
    tokens = collect_tokens()
    pack_map, global_map = build_mappings(tokens)

    for path in PACK_NODES.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        updated = apply_mapping(text, pack_map)
        if updated != text:
            path.write_text(updated, encoding="utf-8")

    rename_files(pack_map)

    for path in GLOBAL.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        updated = apply_mapping(text, global_map)
        if updated != text:
            path.write_text(updated, encoding="utf-8")

    print(f"migrated {len(pack_map)} pack tokens, {len(global_map)} global tokens")


if __name__ == "__main__":
    main()
