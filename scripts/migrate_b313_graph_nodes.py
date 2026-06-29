#!/usr/bin/env python3
"""One-time migration: graph/nodes → hierarchical nodes/ tree for ASME B31.3."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
PACK = _ROOT / "standards" / "asme" / "asme_b31.3"
GRAPH = PACK / "graph" / "nodes"
NODES = PACK / "nodes"

SECTION_ID_REPLACEMENTS = {
    "B313-304.1.1-SECTION": "B313-304.1.1",
    "B313-304.1.2-SECTION": "B313-304.1.2",
    "B313-304.1.3-SECTION": "B313-304.1.3",
}

MOVE_MAP: dict[str, str] = {
    "B313-WF-PIPE-WALL-THICKNESS": "workflows/B313-WF-PIPE-WALL-THICKNESS",
    "B313-WF-MAWP": "workflows/B313-WF-MAWP",
    "B313-304.1.1-SECTION": "304/304.1/304.1.1",
    "B313-304.1.2-SECTION": "304/304.1/304.1.2",
    "B313-304.1.3-SECTION": "304/304.1/304.1.3",
    "B313-MAWP-SECTION": "304/304.1/mawp_definition",
    "B313-304.1.1-init-text": "304/304.1/304.1.1/text/initiation",
    "B313-assumption-straight-pipe": "304/304.1/304.1.1/assumptions/straight-pipe",
    "B313-interaction-pressure-loading": "304/304.1/304.1.1/interactions/pressure-loading",
    "B313-eq-2": "304/304.1/304.1.1/equations/eq-2",
    "B313-eq-2-intro": "304/304.1/304.1.1/equations/eq-2-intro",
    "B313-eq-2-result": "304/304.1/304.1.1/equations/eq-2-result",
    "B313-eq-wall-thickness": "304/304.1/304.1.2/equations/wall-thickness",
    "B313-eq-wall-thickness-intro": "304/304.1/304.1.2/equations/wall-thickness-intro",
    "B313-eq-wall-thickness-result": "304/304.1/304.1.2/equations/wall-thickness-result",
    "B313-eq-mawp": "304/304.1/mawp_definition/equations/mawp",
    "B313-lookup-allowable-stress": "appendix_A/lookups/allowable-stress",
    "B313-table-A-1-REF": "appendix_A/tables/B313-table-A-1-ref",
}

PARAM_PREFIX = "B313-param-"

LEGACY_SUPERSEDE = [
    NODES / "304" / "304.1" / "304.1.1" / "node.md",
    NODES / "304" / "304.1" / "304.1.2" / "node.md",
    NODES / "304" / "304.1" / "304.1.3" / "node.md",
    NODES / "304" / "304.1" / "304.1.1" / "equations" / "eq_2_minimum_required_thickness.md",
]


def _replace_section_ids(text: str) -> str:
    for old, new in SECTION_ID_REPLACEMENTS.items():
        text = text.replace(old, new)
    return text


def _rewrite_section_node_id(text: str, folder_key: str) -> str:
    if folder_key not in SECTION_ID_REPLACEMENTS:
        return text
    new_id = SECTION_ID_REPLACEMENTS[folder_key]
    return re.sub(
        r"^id:\s*" + re.escape(folder_key) + r"\s*$",
        f"id: {new_id}",
        text,
        count=1,
        flags=re.MULTILINE,
    )


def _mark_superseded(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if "status: superseded" in text:
        return
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            front = text[: end + 4]
            body = text[end + 4 :]
            if re.search(r"^status:\s*", front, re.MULTILINE):
                front = re.sub(
                    r"^status:\s*.*$",
                    "status: superseded",
                    front,
                    count=1,
                    flags=re.MULTILINE,
                )
            else:
                front = front.rstrip() + "\nstatus: superseded\n---"
            path.write_text(front + body, encoding="utf-8")
            return
    path.write_text("---\nstatus: superseded\n---\n\n" + text, encoding="utf-8")


def migrate() -> None:
    if not GRAPH.is_dir():
        print("No graph/nodes directory — migration already done?")
        return

    for folder_name, rel_target in sorted(MOVE_MAP.items()):
        src = GRAPH / folder_name / "node.yaml"
        if not src.is_file():
            raise FileNotFoundError(src)
        dest_dir = NODES / rel_target
        dest_dir.mkdir(parents=True, exist_ok=True)
        content = src.read_text(encoding="utf-8")
        content = _rewrite_section_node_id(content, folder_name)
        content = _replace_section_ids(content)
        (dest_dir / "node.yaml").write_text(content, encoding="utf-8")
        print(f"  {folder_name} -> nodes/{rel_target}/node.yaml")

    for entry in sorted(GRAPH.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name in MOVE_MAP or not name.startswith(PARAM_PREFIX):
            continue
        rel_target = f"parameters/{name}"
        src = entry / "node.yaml"
        if not src.is_file():
            continue
        dest_dir = NODES / rel_target
        dest_dir.mkdir(parents=True, exist_ok=True)
        content = _replace_section_ids(src.read_text(encoding="utf-8"))
        (dest_dir / "node.yaml").write_text(content, encoding="utf-8")
        print(f"  {name} -> nodes/{rel_target}/node.yaml")

    for legacy in LEGACY_SUPERSEDE:
        _mark_superseded(legacy)
        if legacy.is_file():
            print(f"  superseded {legacy.relative_to(PACK)}")

    graph_root = PACK / "graph"
    if graph_root.is_dir():
        shutil.rmtree(graph_root)
        print(f"  removed {graph_root.relative_to(_ROOT)}")


if __name__ == "__main__":
    migrate()
