"""Legacy B313 node id aliases after pack reorganization (old id -> canonical id)."""

from __future__ import annotations

import re


def _strip_b313(node_id: str) -> str:
    if node_id.startswith("B313-"):
        return node_id[len("B313-") :]
    return node_id


_NOTE_REMAP = {
    "table-302-3-3C-note1": "asme-b313-note-302-3-3C-1",
    "table-302-3-3C-note2a": "asme-b313-note-302-3-3C-2a",
    "table-302-3-3C-note2b": "asme-b313-note-302-3-3C-2b",
    "table-302-3-3C-note3a": "asme-b313-note-302-3-3C-3a",
    "table-302-3-3C-note3b": "asme-b313-note-302-3-3C-3b",
}

_TABLE_REMAP = {
    "table-A-1": "asme-b313-table-A-1",
    "table-A-1A": "asme-b313-table-A-2",
    "B313-table-A-1A": "asme-b313-table-A-2",
    "table-A-1B": "asme-b313-table-A-3",
    "B313-table-A-1B": "asme-b313-table-A-3",
    "table-302-3-3C": "asme-b313-table-302-3-3C",
    "table-302-3-5": "asme-b313-table-302-3-5-1",
    "B313-table-302-3-5": "asme-b313-table-302-3-5-1",
    "table-304-1-1": "asme-b313-table-304-1-1-1",
    "B313-table-304-1-1": "asme-b313-table-304-1-1-1",
    "B313-table-A-1": "asme-b313-table-A-1",
    "B313-table-A-2": "asme-b313-table-A-2",
    "B313-table-A-3": "asme-b313-table-A-3",
    "B313-table-302-3-3C": "asme-b313-table-302-3-3C",
    "B313-table-302-3-5-1": "asme-b313-table-302-3-5-1",
    "B313-table-304-1-1-1": "asme-b313-table-304-1-1-1",
}

_PARAM_REMAP = {
    f"B313-param-{suffix}": f"param-{suffix}"
    for suffix in (
        "c",
        "D",
        "design_temperature",
        "E",
        "joint_category",
        "material",
        "mawp",
        "nps",
        "P",
        "S",
        "t",
        "t_m",
        "W",
        "Y",
    )
}

_ABSORBED_NO_FILE = {
    "B313-MAWP-SECTION",
    "B313-MAWP-CALCULATION",
    "B313-MAWP-PRESSURE-DESIGN",
    "B313-table-A-1-REF",
    "B313-interaction-pressure-loading",
    "B313-designation-joint-category",
    "B313-designation-material",
    "B313-designation-nps",
    "B313-quantity-diameter",
    "B313-quantity-pressure",
    "B313-quantity-stress",
    "B313-quantity-temperature",
    "B313-quantity-thickness",
    "B313-eq-2-intro",
    "B313-eq-2-result",
    "B313-lookup-allowable-stress",
    "B313-eq-wall-thickness-intro",
    "B313-eq-wall-thickness-result",
    "B313-eq-mawp",
    "B313-assumption-straight-pipe",
}

_SECTION_SUFFIX_ALIASES = {
    "B313-304.1.1": "304.1.1-SECTION",
    "B313-304.1.2": "304.1.2-SECTION",
    "B313-304.1.3": "304.1.3-SECTION",
}

_PARAGRAPH_PRIMARY_SUBSECTION = {
    "304.1.2": "304.1.2-a",
    "302.3.3": "302.3.3-a",
    "302.3.5": "302.3.5-a",
    "304.3.2": "304.3.2-a",
    "304.3.3": "304.3.3-a",
}

_SUBSECTION_SLASH_ALIASES = {
    "302.3.5/e": "302.3.5-e",
    "302.3.3/b": "302.3.3-b",
    "302.3.3/c": "302.3.3-c",
    "304.3.3/f": "304.3.3-f",
    "304.3.3/a": "304.3.3-a",
    "304.3.3/b": "304.3.3-b",
    "304.3.3/c": "304.3.3-c",
}


def build_b313_legacy_aliases() -> dict[str, str]:
    """Map legacy ``B313-*`` ids to post-migration canonical ids."""
    aliases: dict[str, str] = {}

    for old, new in _NOTE_REMAP.items():
        aliases[old] = new

    for old, new in _TABLE_REMAP.items():
        aliases[old] = new

    for old, new in _PARAM_REMAP.items():
        aliases[old] = new

    # Workflows
    aliases["B313-WF-PIPE-WALL-THICKNESS"] = "WF-PIPE-WALL-THICKNESS"
    aliases["B313-WF-MAWP"] = "WF-MAWP"

    # Paragraphs — B313- prefix strip
    for stem in (
        "302.3.3-a",
        "302.3.3-b",
        "302.3.3-c",
        "302.3.5-a",
        "302.3.5-b",
        "302.3.5-c",
        "302.3.5-d",
        "302.3.5-e",
        "302.3.5-f",
        "304.1.1-a",
        "304.1.1-b",
        "304.1.2-a",
        "304.1.2-b",
        "304.1.3",
        "304.3.1",
        "304.3.1-b",
        "304.3.1-c",
        "304.3.1-d",
        "304.3.2-a",
        "304.3.2-b",
        "304.3.2-c",
        "304.3.3-a",
        "304.3.3-b",
        "304.3.3-c",
        "304.3.3-d",
        "304.3.3-e",
        "304.3.3-f",
    ):
        aliases[f"B313-{stem}"] = stem

    aliases["B313-304.1.1"] = "304.1.1-a"
    aliases["304.1.1"] = "304.1.1-a"

    for old, new in _PARAGRAPH_PRIMARY_SUBSECTION.items():
        aliases[old] = new
        aliases[f"B313-{old}"] = new

    for old, new in _SUBSECTION_SLASH_ALIASES.items():
        aliases[old] = new
        aliases[f"B313-{old}"] = new

    # Absorbed nodes point at workflow or paragraph anchor
    aliases["B313-MAWP-SECTION"] = "WF-MAWP"
    aliases["B313-MAWP-CALCULATION"] = "WF-MAWP"
    aliases["B313-MAWP-PRESSURE-DESIGN"] = "WF-MAWP"
    aliases["B313-MAWP-DEFINITION"] = "WF-MAWP"
    aliases["B313-table-A-1-REF"] = "asme-b313-table-A-1"
    aliases["B313-interaction-pressure-loading"] = "WF-PIPE-WALL-THICKNESS"
    aliases["B313-304.1.1-init-text"] = "WF-PIPE-WALL-THICKNESS"
    aliases["B313-assumption-straight-pipe"] = "WF-PIPE-WALL-THICKNESS"
    aliases["B313-eq-mawp"] = "asme-b313-mawp-pressure"
    aliases["B313-eq-2"] = "asme-b313-304-1-1-eq-2"
    aliases["304.1.1-eq-2"] = "asme-b313-304-1-1-eq-2"
    aliases["B313-eq-2-intro"] = "304.1.1-a"
    aliases["B313-eq-2-result"] = "304.1.1-a"
    aliases["B313-eq-wall-thickness"] = "asme-b313-304-1-2-eq-3a"
    aliases["B313-eq-wall-thickness-intro"] = "304.1.2-a"
    aliases["B313-eq-wall-thickness-result"] = "304.1.2-a"
    aliases["B313-lookup-allowable-stress"] = "asme-b313-table-A-1"
    aliases["wall_thickness"] = "asme-b313-304-1-2-eq-3a"
    aliases["asme_b313_304_1_2_wall_thickness"] = "asme-b313-304-1-2-eq-3a"
    aliases["b313-3a"] = "asme-b313-304-1-2-eq-3a"
    aliases["B313-eq-3a"] = "asme-b313-304-1-2-eq-3a"
    aliases["304.1.2-eq-3a"] = "asme-b313-304-1-2-eq-3a"
    aliases["b313-3b"] = "asme-b313-304-1-2-eq-3b"
    aliases["B313-eq-3b"] = "asme-b313-304-1-2-eq-3b"
    aliases["304.1.2-eq-3b"] = "asme-b313-304-1-2-eq-3b"
    aliases["thick_wall_y"] = "asme-b313-304-1-2-eq-3b"
    aliases["asme_b313_thick_wall_y"] = "asme-b313-304-1-2-eq-3b"
    aliases["asme-b313-thick-wall-y"] = "asme-b313-304-1-2-eq-3b"
    aliases["mawp_pressure"] = "asme-b313-mawp-pressure"
    aliases["pressure_design_thickness"] = "asme-b313-pressure-design-thickness"
    aliases["asme_b313_304_3_3_eq_6a"] = "asme-b313-304-3-3-valrule-6a"

    from engine.reference.asme_b313_node_ids import canonical_pack_node_id

    for legacy_id in (
        "asme_b313_304_1_1_eq_2",
        "asme_b313_304_1_2_eq_3a",
        "asme_b313_304_1_2_eq_3b",
        "asme_b313_302_3_5_eq_1a",
        "asme_b313_302_3_5_eq_1b",
        "asme_b313_302_3_5_eq_1c",
        "asme_b313_304_3_3_eq_6",
        "asme_b313_304_3_3_eq_7",
        "asme_b313_304_3_3_eq_8",
        "asme_b313_mawp_pressure",
        "asme_b313_pressure_design_thickness",
        "asme_b313_304_1_1_valrule_a",
        "asme_b313_304_1_2_valrule_b",
        "asme_b313_304_3_3_valrule_6a",
    ):
        aliases[legacy_id] = canonical_pack_node_id(legacy_id)

    for old in _ABSORBED_NO_FILE:
        if old not in aliases:
            stripped = _strip_b313(old)
            if old.startswith("B313-designation-"):
                aliases[old] = "304.1.1-b"
            elif old.startswith("B313-quantity-"):
                aliases[old] = "304.1.1-b"

    return aliases


def rewrite_b313_references(text: str) -> str:
    """Replace legacy B313 node ids in YAML/markdown text."""
    aliases = build_b313_legacy_aliases()
    # Longest ids first to avoid partial replacements.
    for old in sorted(aliases, key=len, reverse=True):
        text = text.replace(old, aliases[old])
    # Generic B313- prefix strip for paragraphs/params, not table/note ids.
    text = re.sub(
        r"\bB313-(?!table-|note-)([A-Za-z0-9_.-]+)\b",
        r"\1",
        text,
    )
    return text
