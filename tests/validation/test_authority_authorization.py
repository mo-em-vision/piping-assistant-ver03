"""Tests for equation/validation_rule authority block rules."""

from engine.reference.graph_compile import compile_metadata_edges
from engine.validation.authority_authorization import validate_authority_authorization


def test_authorization_rejects_duplicate_edge() -> None:
    meta = {
        "authority": {
            "authorized_by": ["304.1.2-a"],
            "authority_context_required": True,
        },
        "edges": [{"type": "authorized_by", "target": "304.1.2-a"}],
    }
    issues = validate_authority_authorization(meta, node_type="equation")
    assert any("must not declare authorized_by edges" in issue for issue in issues)


def test_authorization_requires_authority_list() -> None:
    meta = {
        "authority": {"authority_context_required": True},
        "edges": [],
    }
    issues = validate_authority_authorization(meta, node_type="equation")
    assert "authority.authorized_by required" in issues


def test_authorization_valid_with_authority_block_only() -> None:
    meta = {
        "authority": {
            "authorized_by": ["304.1.2-a"],
            "authority_context_required": True,
        },
        "edges": [],
    }
    assert validate_authority_authorization(meta, node_type="equation") == []


def test_compile_metadata_edges_from_authority_block() -> None:
    edges = compile_metadata_edges(
        "asme-b313-test-eq",
        {
            "type": "equation",
            "authority": {
                "authorized_by": ["304.1.2-a"],
                "authority_context_required": True,
            },
            "edges": [],
        },
    )
    assert ("asme-b313-test-eq", "304.1.2-a", "authorized_by", None) in edges
