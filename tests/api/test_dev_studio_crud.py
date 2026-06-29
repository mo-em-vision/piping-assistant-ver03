"""Tests for dev studio CRUD operations."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api.dev_studio.service import DevStudioService
from api.desktop_service import ApiError


@pytest.fixture
def dev_pack(tmp_path: Path) -> tuple[DevStudioService, str]:
    standards_root = tmp_path / "standards"
    pack_root = standards_root / "asme" / "test_pack"
    nodes_dir = pack_root / "nodes" / "parameters" / "TEST-param-x"
    nodes_dir.mkdir(parents=True)
    (nodes_dir / "node.yaml").write_text(
        """---
id: TEST-param-x
type: parameter
symbol: x
input_id: x
title: Test X
description: Test parameter
unit: mm
---
""",
        encoding="utf-8",
    )
    service = DevStudioService(standards_root=standards_root)
    return service, "test_pack"


def test_list_and_get_node(dev_pack: tuple[DevStudioService, str]) -> None:
    service, pack = dev_pack
    listed = service.list_nodes(pack)
    assert listed["count"] == 1
    assert listed["nodes"][0]["id"] == "TEST-param-x"

    detail = service.get_node(pack, "TEST-param-x")
    assert detail["metadata"]["symbol"] == "x"
    assert detail["body"] == ""


def test_create_update_delete_round_trip(dev_pack: tuple[DevStudioService, str]) -> None:
    service, pack = dev_pack
    created = service.create_node(
        pack,
        {
            "metadata": {
                "id": "TEST-param-y",
                "type": "parameter",
                "symbol": "y",
                "input_id": "y",
                "title": "Test Y",
                "description": "Another parameter",
            },
            "body": "Body text",
            "source_rel_path": "nodes/parameters/TEST-param-y",
        },
    )
    assert created["id"] == "TEST-param-y"
    assert created["body"] == "Body text"

    updated = service.update_node(
        pack,
        "TEST-param-y",
        {
            "metadata": {
                **created["metadata"],
                "title": "Updated Y",
            },
            "body": "Updated body",
        },
    )
    assert updated["metadata"]["title"] == "Updated Y"
    assert updated["body"] == "Updated body"

    deleted = service.delete_node(pack, "TEST-param-y")
    assert deleted["deleted"] is True
    with pytest.raises(ApiError):
        service.get_node(pack, "TEST-param-y")


def test_search_nodes(dev_pack: tuple[DevStudioService, str]) -> None:
    service, pack = dev_pack
    results = service.search_nodes(pack, query="test x")
    assert results["count"] >= 1
    assert any(node["id"] == "TEST-param-x" for node in results["nodes"])


def test_duplicate_node(dev_pack: tuple[DevStudioService, str]) -> None:
    service, pack = dev_pack
    dup = service.duplicate_node(pack, "TEST-param-x", new_id="TEST-param-x-copy")
    assert dup["id"] == "TEST-param-x-copy"
    assert dup["metadata"]["symbol"] == "x"


def test_dev_routes_disabled_without_env() -> None:
    from api.dev_studio.routes import dev_studio_enabled, require_dev_studio

    prev = os.environ.get("DEV_STUDIO_ENABLED")
    os.environ.pop("DEV_STUDIO_ENABLED", None)
    try:
        assert dev_studio_enabled() is False
        with pytest.raises(ApiError) as exc:
            require_dev_studio(None)
        assert exc.value.status == 404
    finally:
        if prev is not None:
            os.environ["DEV_STUDIO_ENABLED"] = prev
