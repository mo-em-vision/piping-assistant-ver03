"""Canonical ASME B31.3 pack node id helpers (prefix ``asme-b313-``)."""

from __future__ import annotations

import re

# Cross-pack qualified prefix for ASME B31.3 nodes (hyphen-separated).
ASME_B313_PREFIX = "asme-b313"

# Legacy qualified paragraph prefix (underscore-separated).
_LEGACY_PARAGRAPH_PREFIX = "asme_b313"

_AUTHORITY_PARAGRAPH_PREFIX: dict[str, str] = {
    "AUTH-ASME-B31.3": ASME_B313_PREFIX,
}

_BARE_PARAGRAPH_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:-([a-z]))?$")


def is_qualified_pack_ref(reference: str) -> bool:
    text = str(reference or "").strip()
    return text.startswith(f"{ASME_B313_PREFIX}-")


def is_qualified_paragraph_ref(reference: str) -> bool:
    return resolve_qualified_paragraph_ref(reference) is not None


def qualify_paragraph_ref(
    paragraph_id: str,
    *,
    pack_prefix: str = ASME_B313_PREFIX,
) -> str:
    """Build a pack-qualified paragraph id (e.g. ``304.1.1-b`` → ``asme-b313-304-1-1-b``)."""
    text = str(paragraph_id or "").strip()
    if not text:
        return text
    resolved = resolve_qualified_paragraph_ref(text)
    if resolved:
        text = resolved
    if is_qualified_pack_ref(text):
        return text
    section, letter = _split_paragraph_id(text)
    section_token = section.replace(".", "-")
    if letter:
        return f"{pack_prefix}-{section_token}-{letter}"
    return f"{pack_prefix}-{section_token}"


def resolve_qualified_paragraph_ref(reference: str) -> str | None:
    """Resolve a qualified paragraph id to the pack-local paragraph ``id``."""
    text = str(reference or "").strip()
    if not text:
        return None
    if text.startswith(f"{_LEGACY_PARAGRAPH_PREFIX}_"):
        rest = text[len(_LEGACY_PARAGRAPH_PREFIX) + 1 :]
        if not rest:
            return None
        parts = rest.split("_")
        if len(parts) >= 2 and len(parts[-1]) == 1 and parts[-1].isalpha():
            letter = parts[-1]
            section = ".".join(parts[:-1])
            return f"{section}-{letter}"
        return ".".join(parts)
    if is_qualified_pack_ref(text):
        rest = _strip_pack_prefix(text)
        if "-eq-" in rest or "-valrule-" in rest or rest.startswith("table-") or rest.startswith("note-"):
            return None
        return _resolve_hyphenated_paragraph_rest(rest)
    return None


def qualify_paragraph_ref_for_authority(paragraph_id: str, authority_id: str) -> str:
    prefix = _AUTHORITY_PARAGRAPH_PREFIX.get(str(authority_id or "").strip())
    if not prefix:
        return str(paragraph_id or "").strip()
    return qualify_paragraph_ref(paragraph_id, pack_prefix=prefix)


def is_lettered_paragraph_ref(reference: str) -> bool:
    text = str(reference or "").strip()
    if not text:
        return False
    bare = resolve_qualified_paragraph_ref(text) or text
    _, letter = _split_paragraph_id(bare)
    return bool(letter)


def paragraph_subsection_letter(reference: str) -> str | None:
    text = str(reference or "").strip()
    if not text:
        return None
    bare = resolve_qualified_paragraph_ref(text) or text
    _, letter = _split_paragraph_id(bare)
    return letter or None


def canonical_pack_node_id(node_id: str) -> str:
    """Return the canonical on-disk id for a non-paragraph ASME B31.3 pack node."""
    text = str(node_id or "").strip()
    if not text:
        return text
    if is_bare_paragraph_id(text):
        return text
    if is_qualified_pack_ref(text):
        resolved = resolve_qualified_paragraph_ref(text)
        if resolved:
            return resolved
        return text
    if text.startswith(f"{_LEGACY_PARAGRAPH_PREFIX}_"):
        resolved = resolve_qualified_paragraph_ref(text)
        return resolved or text
    if text.startswith(f"{_LEGACY_PARAGRAPH_PREFIX.replace('-', '_')}_"):
        rest = text[len("asme_b313_") :]
        return f"{ASME_B313_PREFIX}-{rest.replace('_', '-')}"
    if text.startswith("asme_b313_"):
        rest = text[len("asme_b313_") :]
        return f"{ASME_B313_PREFIX}-{rest.replace('_', '-')}"
    if text.startswith("B313-"):
        return f"{ASME_B313_PREFIX}-{text[len('B313-'):]}"
    return text


def resolve_pack_node_ref(reference: str) -> str | None:
    """Resolve a qualified pack reference to a pack-local node id."""
    text = str(reference or "").strip()
    if not text:
        return None
    paragraph = resolve_qualified_paragraph_ref(text)
    if paragraph:
        return paragraph
    if is_qualified_pack_ref(text):
        return text
    if text.startswith("asme_b313_"):
        return canonical_pack_node_id(text)
    if text.startswith("B313-"):
        return canonical_pack_node_id(text)
    return None


def is_bare_paragraph_id(node_id: str) -> bool:
    text = str(node_id or "").strip()
    return bool(_BARE_PARAGRAPH_RE.match(text))


def qualify_cross_pack_ref(node_id: str) -> str:
    """Qualify any ASME B31.3 pack node id for cross-pack references."""
    text = str(node_id or "").strip()
    if not text:
        return text
    if is_qualified_pack_ref(text):
        return text
    if text.startswith(f"{_LEGACY_PARAGRAPH_PREFIX}_"):
        resolved = resolve_qualified_paragraph_ref(text)
        if resolved:
            return qualify_paragraph_ref(resolved)
        return canonical_pack_node_id(text)
    if is_bare_paragraph_id(text):
        return qualify_paragraph_ref(text)
    return canonical_pack_node_id(text)


def _strip_pack_prefix(reference: str) -> str:
    prefix = f"{ASME_B313_PREFIX}-"
    if reference.startswith(prefix):
        return reference[len(prefix) :]
    return reference


def _split_paragraph_id(paragraph_id: str) -> tuple[str, str]:
    text = str(paragraph_id or "").strip()
    match = re.match(r"^(.+)-([a-z])$", text)
    if match:
        return match.group(1), match.group(2)
    return text, ""


def _resolve_hyphenated_paragraph_rest(rest: str) -> str | None:
    parts = rest.split("-")
    if not parts or not parts[0].isdigit():
        return None
    if len(parts) >= 2 and len(parts[-1]) == 1 and parts[-1].isalpha():
        section = ".".join(parts[:-1])
        return f"{section}-{parts[-1]}"
    return ".".join(parts)
