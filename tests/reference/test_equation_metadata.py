"""Tests for equation node citation metadata helpers."""

from __future__ import annotations

from engine.reference.equation_metadata import (
    equation_paragraph_reference,
    equation_reference,
    format_equation_citation,
)


def test_equation_reference_prefers_explicit_number() -> None:
    meta = {"id": "asme-b313-304-1-2-eq-3a", "equation_number": "3a"}
    assert equation_reference(meta) == "3a"


def test_equation_reference_derives_from_node_id() -> None:
    meta = {"id": "asme-b313-304-1-1-eq-2"}
    assert equation_reference(meta) == "2"


def test_equation_paragraph_reference_uses_authority() -> None:
    meta = {
        "id": "asme-b313-304-1-2-eq-3a",
        "authority": {"authorized_by": ["304.1.2-a"]},
    }
    assert equation_paragraph_reference(meta) == "304.1.2-a"


def test_format_equation_citation() -> None:
    assert (
        format_equation_citation(
            standard_label="ASME B31.3",
            equation_number="3a",
            paragraph_number="304.1.2-a",
        )
        == "ASME B31.3 Eq. (3a) (para. 304.1.2-a)"
    )
