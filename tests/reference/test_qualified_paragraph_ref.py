"""Tests for qualified paragraph reference helpers."""

from __future__ import annotations

from engine.reference.qualified_paragraph_ref import (
    ASME_B313_PARAGRAPH_PREFIX,
    is_lettered_paragraph_ref,
    is_qualified_paragraph_ref,
    qualify_paragraph_ref,
    qualify_paragraph_ref_for_authority,
    resolve_qualified_paragraph_ref,
)


def test_qualify_lettered_paragraph() -> None:
    assert qualify_paragraph_ref("304.1.1-b") == "asme-b313-304-1-1-b"
    assert qualify_paragraph_ref("302.3.5-e") == "asme-b313-302-3-5-e"


def test_qualify_unlettered_paragraph() -> None:
    assert qualify_paragraph_ref("304.1.3") == "asme-b313-304-1-3"


def test_resolve_qualified_paragraph() -> None:
    assert resolve_qualified_paragraph_ref("asme-b313-304-1-1-b") == "304.1.1-b"
    assert resolve_qualified_paragraph_ref("asme-b313-302-3-5-e") == "302.3.5-e"
    assert resolve_qualified_paragraph_ref("asme-b313-304-1-3") == "304.1.3"
    assert resolve_qualified_paragraph_ref("asme_b313_304_1_1_b") == "304.1.1-b"
    assert resolve_qualified_paragraph_ref("304.1.1-b") is None


def test_is_qualified_paragraph_ref() -> None:
    assert is_qualified_paragraph_ref("asme-b313-304-1-1-b")
    assert is_qualified_paragraph_ref("asme_b313_304_1_1_b")
    assert not is_qualified_paragraph_ref("304.1.1-b")


def test_qualify_for_authority() -> None:
    assert (
        qualify_paragraph_ref_for_authority("304.1.2-a", "AUTH-ASME-B31.3")
        == "asme-b313-304-1-2-a"
    )
    assert qualify_paragraph_ref_for_authority("304.1.2-a", "AUTH-OTHER") == "304.1.2-a"


def test_is_lettered_paragraph_ref() -> None:
    assert is_lettered_paragraph_ref("302.3.5-e")
    assert is_lettered_paragraph_ref("asme-b313-304-1-1-b")
    assert is_lettered_paragraph_ref("302.3.3-a")
    assert not is_lettered_paragraph_ref("304.1.3")


def test_prefix_constant() -> None:
    assert ASME_B313_PARAGRAPH_PREFIX == "asme-b313"
