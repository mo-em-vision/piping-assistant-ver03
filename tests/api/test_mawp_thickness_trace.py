"""MAWP thickness derivation and trace display tests."""

from __future__ import annotations

from api.output_blocks import _mawp_thickness_derivation_block


def test_mawp_thickness_derivation_block_from_trace() -> None:
    trace = [
        {
            "node_id": "asme-b313-pressure-design-thickness",
            "trace": {
                "variables_si": {"t_actual": 6.35, "c": 0.5},
                "calculation": {"final_result": {"value": 5.85, "unit": "mm"}},
            },
        }
    ]
    block = _mawp_thickness_derivation_block(trace)
    assert block is not None
    assert block["id"] == "mawp-thickness-derivation"
    assert "t_actual" in block["display"]
    assert "5.850 mm" in block["display"]


def test_mawp_thickness_derivation_block_accepts_legacy_node_id() -> None:
    trace = [
        {
            "node_id": "B313-MAWP-PRESSURE-DESIGN",
            "trace": {
                "variables_si": {"t_actual": 4.0, "c": 0.25},
                "calculation": {"final_result": {"value": 3.75, "unit": "mm"}},
            },
        }
    ]
    block = _mawp_thickness_derivation_block(trace)
    assert block is not None
    assert "3.750 mm" in block["display"]
