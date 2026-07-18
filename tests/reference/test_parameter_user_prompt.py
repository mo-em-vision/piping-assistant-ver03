"""Tests for PARAM user_prompt metadata normalization and validation."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from engine.reference.parameter_metadata import normalize_user_prompt, prepare_parameter_metadata
from engine.reference.standards_markdown import split_frontmatter
from engine.validation.parameter_node_validator import validate_parameter_node

_UNIT_ENTRY_PATTERNS = (
    r"\bincluding units\b",
    r"\binclude units\b",
    r"\benter units\b",
    r"\bprovide units\b",
)


def _parameters_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge" / "global" / "parameters" / "nodes"


def _assert_no_unit_entry_instructions(text: str) -> None:
    lowered = text.casefold()
    for pattern in _UNIT_ENTRY_PATTERNS:
        assert not re.search(pattern, lowered), f"unit-entry instruction found: {pattern}"


def test_normalize_user_prompt_maps_legacy_fields_for_fixtures() -> None:
    meta = {
        "id": "PARAM-example",
        "type": "parameter",
        "question": (
            "Enter the corrosion allowance c, including units.\n"
            "This will be added to the calculated pressure design thickness.\n"
            "Example: 1.5 mm."
        ),
        "short_question": "Enter corrosion allowance c.",
    }
    normalized = normalize_user_prompt(meta)
    assert normalized["user_prompt"]["prompt"] == "Enter corrosion allowance c."
    assert "pressure design thickness" in normalized["user_prompt"]["help_text"]
    assert "question" not in normalized
    assert "short_question" not in normalized


def test_normalize_user_prompt_preserves_canonical_block() -> None:
    meta = {
        "user_prompt": {
            "prompt": "Enter design temperature.",
            "help_text": "Used with the selected material to resolve allowable stress.",
        }
    }
    normalized = normalize_user_prompt(meta)
    assert normalized["user_prompt"]["prompt"] == "Enter design temperature."
    assert "allowable stress" in normalized["user_prompt"]["help_text"]


def test_validator_accepts_prompt_only_user_prompt() -> None:
    meta = {
        "id": "PARAM-example",
        "type": "parameter",
        "key": "example",
        "name": "Example",
        "parameter_class": "physical_quantity",
        "description": "Stable semantic definition of the example engineering field with enough length.",
        "introduced_by": ["asme-b313-304-1-1-b"],
        "user_prompt": {"prompt": "Enter example value."},
        "metadata": {"last_revision": "2026-07-04", "edited_by": "admin"},
    }
    assert validate_parameter_node(meta) == []


def test_validator_rejects_empty_help_text() -> None:
    meta = {
        "id": "PARAM-example",
        "type": "parameter",
        "key": "example",
        "name": "Example",
        "parameter_class": "physical_quantity",
        "description": "Stable semantic definition of the example engineering field with enough length.",
        "introduced_by": ["asme-b313-304-1-1-b"],
        "user_prompt": {"prompt": "Enter example value.", "help_text": "   "},
        "metadata": {"last_revision": "2026-07-04", "edited_by": "admin"},
    }
    issues = validate_parameter_node(meta)
    assert any("help_text must be non-empty" in issue for issue in issues)


def test_validator_rejects_legacy_question_fields() -> None:
    meta = {
        "id": "PARAM-example",
        "type": "parameter",
        "key": "example",
        "name": "Example",
        "parameter_class": "physical_quantity",
        "description": "Stable semantic definition of the example engineering field with enough length.",
        "introduced_by": ["asme-b313-304-1-1-b"],
        "question": "Enter example value.",
        "metadata": {"last_revision": "2026-07-04", "edited_by": "admin"},
    }
    issues = validate_parameter_node(meta)
    assert any("legacy field forbidden: question" in issue for issue in issues)


def test_validator_rejects_legacy_metadata_question_fields() -> None:
    meta = {
        "id": "PARAM-example",
        "type": "parameter",
        "key": "example",
        "name": "Example",
        "parameter_class": "physical_quantity",
        "description": "Stable semantic definition of the example engineering field with enough length.",
        "introduced_by": ["asme-b313-304-1-1-b"],
        "metadata": {
            "last_revision": "2026-07-04",
            "edited_by": "admin",
            "question": "Enter example value.",
        },
    }
    issues = validate_parameter_node(meta)
    assert any("metadata.question" in issue for issue in issues)


def test_validator_rejects_legacy_short_question_fields() -> None:
    meta = {
        "id": "PARAM-example",
        "type": "parameter",
        "key": "example",
        "name": "Example",
        "parameter_class": "physical_quantity",
        "description": "Stable semantic definition of the example engineering field with enough length.",
        "introduced_by": ["asme-b313-304-1-1-b"],
        "metadata": {
            "last_revision": "2026-07-04",
            "edited_by": "admin",
            "short_question": "Enter example value.",
        },
    }
    issues = validate_parameter_node(meta)
    assert any("legacy field forbidden" in issue and "short_question" in issue for issue in issues)


def test_canonical_parameter_nodes_have_no_legacy_prompt_fields() -> None:
    for path in sorted(_parameters_dir().glob("PARAM-*.yaml")):
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        assert "question" not in meta, path.name
        assert "short_question" not in meta, path.name
        nested = meta.get("metadata")
        if isinstance(nested, dict):
            assert "short_question" not in nested, path.name
            assert "question" not in nested, path.name


def test_canonical_user_prompts_do_not_instruct_unit_entry() -> None:
    for path in sorted(_parameters_dir().glob("PARAM-*.yaml")):
        meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
        user_prompt = meta.get("user_prompt")
        if not isinstance(user_prompt, dict):
            continue
        prompt = str(user_prompt.get("prompt") or "")
        help_text = str(user_prompt.get("help_text") or "")
        _assert_no_unit_entry_instructions(prompt)
        if help_text.strip():
            _assert_no_unit_entry_instructions(help_text)


def test_prepare_parameter_metadata_preserves_multiline_help_text() -> None:
    yaml_text = """
id: PARAM-example
type: parameter
user_prompt:
  prompt: Enter corrosion allowance c.
  help_text: >
    This value is added to the calculated pressure design
    thickness to determine the minimum required thickness.
"""
    meta = yaml.safe_load(yaml_text)
    prepared = prepare_parameter_metadata(meta)
    assert prepared["user_prompt"]["prompt"] == "Enter corrosion allowance c."
    assert "pressure design" in prepared["user_prompt"]["help_text"]


def test_outside_diameter_is_prompt_only() -> None:
    meta, _body = split_frontmatter(
        (_parameters_dir() / "PARAM-outside-diameter.yaml").read_text(encoding="utf-8")
    )
    user_prompt = meta["user_prompt"]
    assert user_prompt["prompt"] == "Enter outside diameter D."
    assert "help_text" not in user_prompt
