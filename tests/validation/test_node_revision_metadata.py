"""Tests for shared revision metadata on knowledge nodes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from engine.reference.standards_markdown import split_frontmatter
from engine.validation.node_revision_metadata import (
    stamp_revision_metadata,
    validate_revision_metadata,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_validate_revision_metadata_requires_fields() -> None:
    assert validate_revision_metadata({}) == ["metadata block required"]
    assert validate_revision_metadata({"metadata": {}}) == [
        "metadata.last_revision required",
        "metadata.edited_by required",
    ]


def test_stamp_revision_metadata_sets_today_and_editor() -> None:
    stamped = stamp_revision_metadata({"type": "parameter", "id": "PARAM-test"})
    metadata = stamped["metadata"]
    assert metadata["last_revision"] == date.today().isoformat()
    assert metadata["edited_by"] == "admin"


def test_stamp_revision_metadata_preserves_existing_metadata() -> None:
    stamped = stamp_revision_metadata(
        {
            "type": "paragraph",
            "metadata": {"status": "active", "source_revision_year": 2024},
        },
        edited_by="reviewer",
        last_revision="2026-07-04",
    )
    metadata = stamped["metadata"]
    assert metadata["status"] == "active"
    assert metadata["source_revision_year"] == 2024
    assert metadata["last_revision"] == "2026-07-04"
    assert metadata["edited_by"] == "reviewer"


@pytest.mark.parametrize(
    "relative",
    [
        "knowledge/global/parameters/nodes/PARAM-internal-design-gage-pressure.yaml",
        "knowledge/global/concepts/nodes/CONCEPT-pressure.yaml",
        "knowledge/global/units/nodes/UNIT-K.yaml",
        "knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-a.yaml",
        "knowledge/standards/asme/asme_b31.3/nodes/equation/304.1.1.eq.2.yaml",
    ],
)
def test_sample_knowledge_nodes_have_revision_metadata(relative: str) -> None:
    path = _project_root() / relative
    meta, _ = split_frontmatter(path.read_text(encoding="utf-8"))
    assert validate_revision_metadata(meta) == [], relative


def test_all_knowledge_nodes_have_revision_metadata() -> None:
    knowledge = _project_root() / "knowledge"
    missing: list[str] = []
    for path in sorted(knowledge.rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        meta, _ = split_frontmatter(text)
        if not meta.get("type"):
            continue
        issues = validate_revision_metadata(meta)
        if issues:
            missing.append(f"{path.relative_to(knowledge)}: {', '.join(issues)}")
    assert missing == []
