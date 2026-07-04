"""Qualified paragraph ids for cross-pack traceability on global ontology nodes."""

from __future__ import annotations

from engine.reference.asme_b313_node_ids import (
    ASME_B313_PREFIX,
    is_lettered_paragraph_ref,
    is_qualified_paragraph_ref,
    paragraph_subsection_letter,
    qualify_paragraph_ref,
    qualify_paragraph_ref_for_authority,
    resolve_qualified_paragraph_ref,
)

# Backward-compatible alias used by tests and imports.
ASME_B313_PARAGRAPH_PREFIX = ASME_B313_PREFIX

__all__ = [
    "ASME_B313_PARAGRAPH_PREFIX",
    "ASME_B313_PREFIX",
    "is_lettered_paragraph_ref",
    "is_qualified_paragraph_ref",
    "paragraph_subsection_letter",
    "qualify_paragraph_ref",
    "qualify_paragraph_ref_for_authority",
    "resolve_qualified_paragraph_ref",
]
