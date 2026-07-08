"""Tests for standards browse API."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.standards_browse import build_standards_browse_payload
from config.loader import CLIConfig
from engine.reference.standards_reader import StandardsReader

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _nodes_db_available(project_root: Path | None = None) -> bool:
    root = project_root or _REPO_ROOT
    return (
        root / "knowledge" / "standards" / "asme" / "asme_b31.3" / "asme_b313_nodes.db"
    ).exists()


def _service(project_root: Path, tmp_path: Path) -> DesktopApiService:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config)


def _collect_node_ids(tree: list[dict]) -> set[str]:
    found: set[str] = set()
    for item in tree:
        node_id = item.get("node_id")
        if isinstance(node_id, str) and node_id:
            found.add(node_id)
        children = item.get("children")
        if isinstance(children, list):
            found.update(_collect_node_ids(children))
    return found


def _find_leaf(tree: list[dict], node_id: str) -> dict | None:
    for item in tree:
        if item.get("node_id") == node_id:
            return item
        children = item.get("children")
        if isinstance(children, list):
            found = _find_leaf(children, node_id)
            if found is not None:
                return found
    return None


def _find_group_by_label(tree: list[dict], label: str) -> dict | None:
    for item in tree:
        if item.get("kind") == "group" and item.get("label") == label:
            return item
        children = item.get("children")
        if isinstance(children, list):
            found = _find_group_by_label(children, label)
            if found is not None:
                return found
    return None


@pytest.mark.skipif(
    not _nodes_db_available(),
    reason="Run scripts/build_standards_nodes_db.py to build asme_b313_nodes.db",
)
def test_build_standards_browse_tree_includes_known_nodes(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    payload = build_standards_browse_payload(reader, standard="asme_b31.3")

    node_ids = _collect_node_ids(payload["tree"])
    assert "304.1.1-a" in node_ids
    assert "asme-b313-table-A-1" in node_ids

    section_labels = [item["label"] for item in payload["tree"] if item.get("kind") == "group"]
    assert any(label == "Section 304" for label in section_labels)
    assert any(label == "Available tasks" for label in section_labels)


@pytest.mark.skipif(
    not _nodes_db_available(),
    reason="Run scripts/build_standards_nodes_db.py to build asme_b313_nodes.db",
)
def test_appendix_a_tree_omits_redundant_folder_group(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    payload = build_standards_browse_payload(reader, standard="asme_b31.3")

    appendix_group = _find_group_by_label(payload["tree"], "Appendix A")
    assert appendix_group is not None

    child_labels = [
        str(child.get("label") or "")
        for child in appendix_group.get("children", [])
        if isinstance(child, dict)
    ]
    assert "appendix_A" not in child_labels
    assert "tables" in child_labels
    assert _find_leaf(payload["tree"], "asme-b313-table-A-1") is not None


@pytest.mark.skipif(
    not _nodes_db_available(),
    reason="Run scripts/build_standards_nodes_db.py to build asme_b313_nodes.db",
)
def test_browse_links_pipe_wall_thickness_workflow(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    payload = build_standards_browse_payload(reader, standard="asme_b31.3")

    available_tasks_group = next(
        item for item in payload["tree"] if item.get("label") == "Available tasks"
    )
    workflow_leaves = [
        child
        for child in available_tasks_group.get("children", [])
        if child.get("kind") == "workflow"
    ]
    assert any(child.get("workflow_id") == "pipe_wall_thickness_design" for child in workflow_leaves)

    node_304 = _find_leaf(payload["tree"], "304.1.1-a")
    if node_304 is None:
        node_304 = _find_leaf(payload["tree"], "304.1.1")
    assert node_304 is not None
    related = node_304.get("related_workflows") or []
    assert any(item.get("id") == "pipe_wall_thickness_design" for item in related)

    table_a1 = _find_leaf(payload["tree"], "asme-b313-table-A-1")
    assert table_a1 is not None
    assert table_a1.get("table_id")
    table_related = table_a1.get("related_workflows") or []
    assert any(item.get("id") == "mawp_design" for item in table_related)


@pytest.mark.skipif(
    not _nodes_db_available(),
    reason="Run scripts/build_standards_nodes_db.py to build asme_b313_nodes.db",
)
def test_get_standards_browse_endpoint(project_root: Path, tmp_path: Path) -> None:
    service = _service(project_root, tmp_path)
    payload = service.get_standards_browse("asme_b31.3")

    assert payload["standard"] == "ASME B31.3"
    assert payload["standard_slug"] == "asme_b31.3"
    assert isinstance(payload["tree"], list)
    assert "304.1.1-a" in _collect_node_ids(payload["tree"])
