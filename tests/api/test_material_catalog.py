"""API tests for ASTM material search."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.material_catalog import search_astm_materials


@pytest.fixture
def standards_root(project_root: Path) -> Path:
    return project_root / "knowledge" / "standards"


def test_search_requires_three_characters(standards_root: Path) -> None:
    assert search_astm_materials(standards_root, "sa") == []
    assert search_astm_materials(standards_root, "  sa  ") == []


def test_search_finds_a106_grade_b_alias(standards_root: Path) -> None:
    results = search_astm_materials(standards_root, "106")
    labels = {item["label"] for item in results}
    a106 = [item for item in results if item["standard"] == "astm_a106"]

    assert len(a106) == 3
    assert labels == {
        "ASTM A106 Grade A",
        "ASTM A106 Grade B",
        "ASTM A106 Grade C",
    }
    assert {item["value"] for item in a106} == {
        "astm_a106_gr_a",
        "astm_a106_gr_b",
        "astm_a106_gr_c",
    }


def test_search_finds_single_a105_from_astm_pack(standards_root: Path) -> None:
    results = search_astm_materials(standards_root, "a105")
    a105 = [item for item in results if item["value"] == "astm_a105"]

    assert len(a105) == 1
    assert a105[0]["standard"] == "a_105"
    assert a105[0]["label"] == "ASTM A105 — Carbon Steel Forgings"


def test_search_finds_stainless_tp316(standards_root: Path) -> None:
    results = search_astm_materials(standards_root, "tp3")
    assert results
    assert any(
        "tp316" in item["value"] or "tp304" in item["value"] for item in results
    )
    assert all(item["standard"].startswith("astm_") for item in results)


def test_warm_material_catalog_endpoint_shape(standards_root: Path) -> None:
    from api.material_catalog import warm_astm_material_catalog

    payload = warm_astm_material_catalog(standards_root)
    assert payload["ready"] is True


def test_get_material_detail_returns_a106_grade_b(standards_root: Path) -> None:
    from api.material_detail import get_material_detail

    detail = get_material_detail(standards_root, "astm_a106_gr_b")

    assert detail["material_id"] == "astm_a106_gr_b"
    assert detail["display_name"] == "ASTM A106 Grade B"
    assert detail["standard_slug"] == "astm_a106"
    assert detail["product_form"] == "seamless_pipe"
    assert detail["uns_number"] == "K03006"
    assert detail["mechanical_properties"]["room_temperature"]["tensile_strength_min"]["ksi"] == 60
    assert detail["source_node"] == "A106"


def test_get_material_detail_unknown_raises(standards_root: Path) -> None:
    from api.material_detail import get_material_detail

    with pytest.raises(FileNotFoundError):
        get_material_detail(standards_root, "unknown_material_id")
