"""Tests for dev studio search."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.dev_studio.service import DevStudioService


@pytest.fixture
def search_service(tmp_path: Path) -> tuple[DevStudioService, str]:
    standards_root = tmp_path / "standards"
    pack_root = standards_root / "asme" / "test_pack"
    for node_id, title, unit in [
        ("TEST-a", "Alpha pipe", "mm"),
        ("TEST-b", "Beta equation", "Pa"),
    ]:
        folder = pack_root / "nodes" / "parameters" / node_id
        folder.mkdir(parents=True)
        (folder / "node.yaml").write_text(
            f"""---
id: {node_id}
type: parameter
symbol: x
input_id: x
title: {title}
description: Search fixture
unit: {unit}
---
""",
            encoding="utf-8",
        )
    return DevStudioService(standards_root=standards_root), "test_pack"


def test_search_by_title(search_service: tuple[DevStudioService, str]) -> None:
    service, pack = search_service
    results = service.search_nodes(pack, query="alpha")
    assert results["count"] == 1
    assert results["nodes"][0]["id"] == "TEST-a"


def test_search_by_unit(search_service: tuple[DevStudioService, str]) -> None:
    service, pack = search_service
    results = service.search_nodes(pack, query="pa")
    assert any(node["id"] == "TEST-b" for node in results["nodes"])
