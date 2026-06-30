"""Tests for dev studio import formats."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.dev_studio.service import DevStudioService


@pytest.fixture
def import_service(tmp_path: Path) -> tuple[DevStudioService, str]:
    standards_root = tmp_path / "standards"
    pack_root = standards_root / "asme" / "test_pack"
    pack_root.mkdir(parents=True)
    (pack_root / "nodes").mkdir()
    return DevStudioService(standards_root=standards_root), "test_pack"


def test_import_markdown_creates_node(import_service: tuple[DevStudioService, str]) -> None:
    service, pack = import_service
    content = """---
id: TEST-md-1
type: parameter
symbol: md1
input_id: md1
title: Markdown import
description: From markdown
---
Body here
"""
    result = service.import_nodes(pack, {"format": "markdown", "content": content})
    assert "TEST-md-1" in result["created"]
    node = service.get_node(pack, "TEST-md-1")
    assert node["body"].strip() == "Body here"
    assert node["metadata"]["title"] == "Markdown import"


def test_import_csv_creates_parameter(import_service: tuple[DevStudioService, str]) -> None:
    service, pack = import_service
    content = (
        "id,type,title,source_rel_path,description\n"
        "TEST-csv-1,parameter,CSV Param,nodes/parameters/TEST-csv-1,From csv\n"
    )
    result = service.import_nodes(pack, {"format": "csv", "content": content})
    assert "TEST-csv-1" in result["created"]
    node = service.get_node(pack, "TEST-csv-1")
    assert node["metadata"]["description"] == "From csv"
