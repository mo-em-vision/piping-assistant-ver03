"""Tests for PARAM id-aligned display helpers."""

from __future__ import annotations

import pytest

from engine.reference.knowledge_paths import parameters_root
from engine.reference.parameter_keys import (
    param_display_name_from_id,
    param_name_matches_id_slug,
)
from engine.reference.standards_markdown import split_frontmatter


def test_param_display_name_from_id() -> None:
    assert param_display_name_from_id("PARAM-required-wall-thickness") == "Required Wall Thickness"
    assert param_display_name_from_id("PARAM-internal-design-gage-pressure") == (
        "Internal Design Gage Pressure"
    )


@pytest.mark.parametrize(
    ("filename",),
    [(path.name,) for path in sorted(parameters_root().glob("nodes/PARAM-*.yaml"))],
)
def test_param_names_match_id_slug(filename: str) -> None:
    path = parameters_root() / "nodes" / filename
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    node_id = str(meta.get("id") or path.stem)
    name = str(meta.get("name") or "")
    assert param_name_matches_id_slug(node_id, name), (
        f"{node_id} name {name!r} should match id slug"
    )
