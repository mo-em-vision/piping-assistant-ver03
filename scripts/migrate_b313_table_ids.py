#!/usr/bin/env python3
"""One-time migration: B31.3 table node ids, source metadata, and B36.10 table rename."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
ROOT = _ROOT / "knowledge" / "standards"

B313_RENAMES = {
    "table-A-1.yaml": "B313-table-A-1.yaml",
    "table-A-1A.yaml": "B313-table-A-1A.yaml",
    "table-A-1B.yaml": "B313-table-A-1B.yaml",
    "table-302-3-3C.yaml": "B313-table-302-3-3C.yaml",
    "table-302-3-5.yaml": "B313-table-302-3-5.yaml",
    "table-304-1-1.yaml": "B313-table-304-1-1.yaml",
    "table-302-3-3C-note1.yaml": "B313-note-302-3-3C-1.yaml",
    "table-302-3-3C-note2a.yaml": "B313-note-302-3-3C-2a.yaml",
    "table-302-3-3C-note2b.yaml": "B313-note-302-3-3C-2b.yaml",
    "table-302-3-3C-note3a.yaml": "B313-note-302-3-3C-3a.yaml",
    "table-302-3-3C-note3b.yaml": "B313-note-302-3-3C-3b.yaml",
}

ID_MAP = {
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

TABLE_ID_BY_NODE = {
    "B313-table-A-1": "asme_b31.3_A-1",
    "B313-table-A-1A": "asme_b31.3_A-1A",
    "B313-table-A-1B": "asme_b31.3_A-1B",
    "B313-table-302-3-3C": "asme_b31.3_table_302_3_3C",
    "B313-table-302-3-5": "asme_b31.3_302.3.5",
    "B313-table-304-1-1": "asme_b31.3_table_304_1_1",
}


def migrate_b313_tables() -> None:
    tables_dir = ROOT / "asme" / "asme_b31.3" / "nodes" / "tables"
    for old, new in B313_RENAMES.items():
        src = tables_dir / old
        dst = tables_dir / new
        if src.exists():
            src.rename(dst)

    for path in sorted(tables_dir.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        body = parts[2]
        meta_lines = parts[1].strip().splitlines()
        old_id = next((line.split(":", 1)[1].strip() for line in meta_lines if line.startswith("id:")), path.stem)
        new_id = ID_MAP.get(old_id, old_id)

        out_lines: list[str] = []
        has_standard = False
        skip_source = False
        for line in meta_lines:
            if skip_source:
                if line.startswith("  "):
                    continue
                skip_source = False
            if line.startswith("id:"):
                out_lines.append(f"id: {new_id}")
            elif line.startswith("standard:"):
                out_lines.append("standard: asme_b31.3")
                has_standard = True
            elif line.startswith("source:"):
                skip_source = True
                continue
            else:
                out_lines.append(line)

        if not has_standard:
            out_lines.insert(1, "standard: asme_b31.3")

        block = [
            "source:",
            "  pack: asme_b31.3",
            f"  yaml: nodes/tables/{path.name}",
            "  tables_db: asme_b313_tables.db",
        ]
        if new_id in TABLE_ID_BY_NODE:
            block.append(f"  table_id: {TABLE_ID_BY_NODE[new_id]}")
        out_lines[2:2] = block

        path.write_text("---\n" + "\n".join(out_lines) + "\n---" + body, encoding="utf-8")


def migrate_b36_table() -> None:
    b36_tables = ROOT / "asme" / "asme_b36.10" / "tables"
    old_b36 = b36_tables / "table-2-1.yaml"
    new_b36 = b36_tables / "B3610-table-2-1.yaml"
    if not old_b36.exists():
        return
    text = old_b36.read_text(encoding="utf-8")
    if not text.startswith("standard:"):
        prefix = (
            "standard: asme_b36.10\n"
            "node_id: B3610-table-2-1\n"
            "registry:\n"
            "  pack: asme_b36.10\n"
            "  yaml: tables/B3610-table-2-1.yaml\n"
            "  db_file: pipe_dimensions.db\n"
            "  table_id: table-2-1\n"
        )
        text = prefix + text
    old_b36.write_text(text, encoding="utf-8")
    old_b36.rename(new_b36)


def patch_references() -> None:
    replacements = sorted(ID_MAP.items(), key=lambda item: len(item[0]), reverse=True)
    patch_roots = [_ROOT / "knowledge", _ROOT / "tests", _ROOT / "engine", _ROOT / "api", _ROOT / "docs"]
    for base in patch_roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in {".yaml", ".md", ".py"}:
                continue
            text = path.read_text(encoding="utf-8")
            orig = text
            for old, new in replacements:
                text = text.replace(f"node:{old}", f"node:{new}")
                text = text.replace(f"node_id: {old}", f"node_id: {new}")
                text = text.replace(f"`{old}`", f"`{new}`")
            for old_file, new_file in B313_RENAMES.items():
                text = text.replace(f"nodes/tables/{old_file}", f"nodes/tables/{new_file}")
                text = text.replace(f"tables/{old_file}", f"tables/{new_file}")
            text = text.replace("table:table-A-1", "table:asme_b31.3_A-1")
            text = text.replace("yaml_source: tables/table-2-1.yaml", "yaml_source: tables/B3610-table-2-1.yaml")
            if text != orig:
                path.write_text(text, encoding="utf-8")


def main() -> None:
    migrate_b313_tables()
    migrate_b36_table()
    patch_references()


if __name__ == "__main__":
    main()
