"""Tests for dev studio validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.dev_studio.service import DevStudioService
from api.desktop_service import ApiError


@pytest.fixture
def dev_service(tmp_path: Path) -> tuple[DevStudioService, str]:
    standards_root = tmp_path / "standards"
    pack_root = standards_root / "asme" / "test_pack"
    param_dir = pack_root / "nodes" / "parameters" / "TEST-param-a"
    param_dir.mkdir(parents=True)
    (param_dir / "node.yaml").write_text(
        """---
id: TEST-param-a
type: parameter
symbol: a
input_id: a
title: A
description: Parameter A
---
""",
        encoding="utf-8",
    )
    eq_dir = pack_root / "nodes" / "equations" / "TEST-eq-1"
    eq_dir.mkdir(parents=True)
    (eq_dir / "node.yaml").write_text(
        """---
id: TEST-eq-1
type: equation
sympy: "b = a + 1"
display_latex: "b = a + 1"
requires:
  - TEST-param-a
calculates:
  - TEST-param-b
---
""",
        encoding="utf-8",
    )
    return DevStudioService(standards_root=standards_root), "test_pack"


def test_validation_rejects_duplicate_id(dev_service: tuple[DevStudioService, str]) -> None:
    service, pack = dev_service
    result = service.validate_payload(
        pack,
        metadata={
            "id": "TEST-param-a",
            "type": "parameter",
            "symbol": "dup",
            "input_id": "dup",
            "description": "dup",
        },
    )
    assert result["valid"] is False
    assert any(item["field"] == "id" for item in result["errors"])


def test_validation_rejects_bad_sympy(dev_service: tuple[DevStudioService, str]) -> None:
    service, pack = dev_service
    result = service.validate_payload(
        pack,
        metadata={
            "id": "TEST-eq-bad",
            "type": "equation",
            "sympy": "not valid = = =",
            "display_latex": "bad",
            "requires": ["TEST-param-a"],
            "calculates": ["TEST-param-b"],
        },
    )
    assert result["valid"] is False
    assert any(item["field"] == "sympy" for item in result["errors"])


def test_validation_rejects_broken_reference(dev_service: tuple[DevStudioService, str]) -> None:
    service, pack = dev_service
    result = service.validate_payload(
        pack,
        metadata={
            "id": "TEST-eq-2",
            "type": "equation",
            "sympy": "c = 1",
            "display_latex": "c = 1",
            "requires": ["MISSING-NODE"],
            "calculates": ["TEST-param-a"],
        },
    )
    assert result["valid"] is False
    assert any("MISSING-NODE" in item["message"] for item in result["errors"])


def test_create_rejects_invalid_payload(dev_service: tuple[DevStudioService, str]) -> None:
    service, pack = dev_service
    with pytest.raises(ApiError) as exc:
        service.create_node(
            pack,
            {
                "metadata": {
                    "id": "TEST-bad",
                    "type": "parameter",
                },
            },
        )
    assert exc.value.code == "validation_failed"
