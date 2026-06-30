#!/usr/bin/env python3
"""Merge dual node.yaml + node.md sources into a single node.yaml per folder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engine.reference.standards_markdown import (
    compose_frontmatter,
    merge_dual_node_frontmatter,
    split_frontmatter,
)

PACK = _ROOT / "standards" / "asme" / "asme_b31.3"
NODES = PACK / "nodes"


def discover_dual_node_dirs(pack_nodes: Path) -> list[Path]:
    dual: list[Path] = []
    if not pack_nodes.is_dir():
        return dual
    for node_dir in sorted(pack_nodes.iterdir()):
        if not node_dir.is_dir():
            continue
        if (node_dir / "node.yaml").is_file() and (node_dir / "node.md").is_file():
            dual.append(node_dir)
    return dual


def merge_dual_node_dir(node_dir: Path) -> tuple[str, dict] | None:
    yaml_path = node_dir / "node.yaml"
    md_path = node_dir / "node.md"
    if not yaml_path.is_file() or not md_path.is_file():
        return None

    yaml_meta, yaml_body = split_frontmatter(yaml_path.read_text(encoding="utf-8"))
    merged_meta, merged_body = merge_dual_node_frontmatter(
        node_dir,
        yaml_meta,
        yaml_body,
        primary_path=yaml_path,
    )
    node_id = str(merged_meta.get("id") or node_dir.name).strip()
    return node_id, {
        "yaml_path": yaml_path,
        "md_path": md_path,
        "metadata": merged_meta,
        "body": merged_body,
    }


def run(*, dry_run: bool) -> int:
    merged_dirs = discover_dual_node_dirs(NODES)
    if not merged_dirs:
        print("No dual node.yaml + node.md folders found.")
        return 0

    for node_dir in merged_dirs:
        result = merge_dual_node_dir(node_dir)
        if result is None:
            continue
        node_id, payload = result
        output = compose_frontmatter(payload["metadata"], payload["body"])
        print(f"merge {node_id}: {node_dir.relative_to(PACK)}")
        if dry_run:
            continue
        payload["yaml_path"].write_text(output, encoding="utf-8")
        payload["md_path"].unlink()

    action = "would merge" if dry_run else "merged"
    print(f"\nSummary: {action} {len(merged_dirs)} dual-source node(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print merges without writing files or deleting node.md",
    )
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
