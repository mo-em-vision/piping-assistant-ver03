"""Tests for standards pack path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.reference.standards_paths import (
    list_standard_packs,
    resolve_global_tasks_db,
    resolve_pack_workflows_dir,
    resolve_pack_tasks_dir,
    resolve_standard_pack,
)
from engine.reference.pack_tables_db import resolve_pack_tables_db


def test_resolve_grouped_asme_b31_3() -> None:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    pack = resolve_standard_pack(root, "asme_b31.3")
    assert pack.name == "asme_b31.3"
    assert pack.parent.name == "asme"
    assert (pack / "nodes" / "paragraph" / "304.1.1-a.yaml").exists()
    assert (pack / "nodes" / "paragraph" / "304.1.1-b.yaml").exists()
    assert (pack / "nodes" / "paragraph" / "304.1.2-a.yaml").exists()
    tables_db = resolve_pack_tables_db(pack)
    assert tables_db.name in {"standards_tables.db", "tables.db"}
    assert tables_db.is_file()


def test_resolve_pack_workflows_dir_for_asme_b31_3(project_root: Path) -> None:
    standards_root = project_root / "knowledge" / "standards"
    pack = resolve_standard_pack(standards_root, "asme_b31.3")
    workflows_dir = resolve_pack_workflows_dir(pack)
    assert workflows_dir == pack / "nodes" / "workflows"
    workflow = workflows_dir / "pipe-wall-thickness.yaml"
    if not workflow.is_file():
        pytest.skip("workflow YAML not present in this workspace")
    assert workflow.is_file()
    assert resolve_global_tasks_db(standards_root).name == "workflows.db"


def test_resolve_pack_tasks_dir_legacy_roots(tmp_path: Path) -> None:
    pack = tmp_path / "stub_pack"
    (pack / "roots").mkdir(parents=True)
    tasks_dir = resolve_pack_tasks_dir(pack)
    assert tasks_dir.name == "roots"


def test_resolve_grouped_asme_b36_10() -> None:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    pack = resolve_standard_pack(root, "asme_b36.10")
    assert pack.name == "asme_b36.10"
    assert (pack / "tables" / "B3610-table-2-1.yaml").exists()


def test_resolve_explicit_group_path() -> None:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    pack = resolve_standard_pack(root, "asme/asme_b31.3")
    assert pack.name == "asme_b31.3"


def test_resolve_unknown_raises() -> None:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    with pytest.raises(FileNotFoundError):
        resolve_standard_pack(root, "nonexistent_standard")


def test_list_standard_packs_includes_asme_and_astm() -> None:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    slugs = {slug for slug, _ in list_standard_packs(root)}
    assert "asme_b31.3" in slugs
    assert "asme_b36.10" in slugs
    assert "astm" in slugs


def test_resolve_consolidated_astm_a106() -> None:
    root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    pack = resolve_standard_pack(root, "astm_a106")
    assert pack.name == "astm"
    assert (root / "astm" / "astm_a106.db").is_file()
