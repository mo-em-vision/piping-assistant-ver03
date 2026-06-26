"""Tests for standards pack path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_paths import (
    list_standard_packs,
    resolve_global_tasks_db,
    resolve_pack_tasks_dir,
    resolve_standard_pack,
    resolve_standard_tasks_dir,
    resolve_standards_tasks_dir,
)
from engine.reference.pack_tables_db import resolve_pack_tables_db


def test_resolve_grouped_asme_b31_3() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    pack = resolve_standard_pack(root, "asme_b31.3")
    assert pack.name == "asme_b31.3"
    assert pack.parent.name == "asme"
    assert (pack / "nodes" / "304" / "304.1.1" / "node.md").exists()
    assert (pack / "nodes" / "304" / "304.1.2" / "node.md").exists()
    tables_db = resolve_pack_tables_db(pack)
    assert tables_db.name in {"standards_tables.db", "asme_b313_tables.db"}
    assert tables_db.is_file()


def test_resolve_standard_tasks_dir_for_asme_b31_3(project_root: Path) -> None:
    standards_root = project_root / "standards"
    tasks_dir = resolve_standard_tasks_dir(standards_root, "asme_b31.3")
    assert tasks_dir == resolve_standards_tasks_dir(standards_root) / "asme_b31.3"
    assert (tasks_dir / "pipe_wall_thickness_design" / "root.md").is_file()
    assert resolve_global_tasks_db(standards_root).name == "tasks.db"


def test_resolve_pack_tasks_dir_legacy_roots(project_root: Path) -> None:
    pack = project_root / "standards" / "api" / "api_570"
    tasks_dir = resolve_pack_tasks_dir(pack)
    assert tasks_dir.name == "roots"


def test_resolve_grouped_asme_b36_10() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    pack = resolve_standard_pack(root, "asme_b36.10")
    assert pack.name == "asme_b36.10"
    assert (pack / "tables" / "welded_seamless_pipe_dimensions.yaml").exists()


def test_resolve_explicit_group_path() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    pack = resolve_standard_pack(root, "asme/asme_b31.3")
    assert pack.name == "asme_b31.3"


def test_resolve_unknown_raises() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    with pytest.raises(FileNotFoundError):
        resolve_standard_pack(root, "nonexistent_standard")


def test_list_standard_packs_includes_asme_samples() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    slugs = {slug for slug, _ in list_standard_packs(root)}
    assert "asme_b31.3" in slugs
    assert "asme_b36.10" in slugs
    assert "astm_a106" in slugs
    assert "astm_a312" in slugs


def test_resolve_grouped_astm_a106() -> None:
    root = Path(__file__).resolve().parents[2] / "standards"
    pack = resolve_standard_pack(root, "astm_a106")
    assert pack.parent.name == "astm"
    assert resolve_pack_tables_db(pack).name == "astm_a106.db"
