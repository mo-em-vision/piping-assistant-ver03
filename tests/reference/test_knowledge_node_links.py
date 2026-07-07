"""Tests that knowledge node validators reject links metadata."""

from __future__ import annotations

import pytest

from engine.validation.authority_node_validator import validate_authority_node
from engine.validation.equation_node_validator import validate_equation_node
from engine.validation.lookup_node_validator import validate_lookup_node
from engine.validation.parameter_node_validator import validate_parameter_node
from engine.validation.paragraph_node_validator import validate_paragraph_node
from engine.validation.unit_node_validator import validate_unit_node
from engine.validation.validation_rule_node_validator import validate_validation_rule_node
from engine.validation.workflow_node_validator import validate_workflow_node

_LINKS = {"equations": ["asme-b313-304-1-1-eq-2"]}
_EXPECTED_MSG = "knowledge nodes must not use links"


@pytest.mark.parametrize(
    ("validator", "meta"),
    [
        (
            validate_paragraph_node,
            {
                "type": "paragraph",
                "key": "test",
                "title": "Test",
                "authority": "AUTH-ASME-B31.3",
                "edition": 2024,
                "paragraph_number": "304.1.2-a",
                "id": "304.1.2-a",
                "text": {"original": "sample"},
                "hierarchy": {"parent": "304.1"},
                "metadata": {
                    "source_revision_year": 2024,
                    "last_revision": "2026-07-04",
                    "edited_by": "admin",
                },
                "links": _LINKS,
                "edges": [],
            },
        ),
        (
            validate_equation_node,
            {
                "type": "equation",
                "id": "asme-b313-test-eq",
                "key": "asme-b313-test-eq",
                "name": "Test",
                "equation_class": "calculation",
                "description": "Test equation",
                "authority": {
                    "authorized_by": ["304.1.1-a"],
                    "authority_context_required": True,
                },
                "requires": [{"symbol": "P", "parameter": "param-p"}],
                "metadata": {
                    "status": "active",
                    "last_revision": "2026-07-04",
                    "edited_by": "admin",
                },
                "links": _LINKS,
                "edges": [],
            },
        ),
        (
            validate_workflow_node,
            {
                "type": "workflow",
                "id": "WF-TEST",
                "key": "test_workflow",
                "name": "Test Workflow",
                "workflow_class": "design_calculation",
                "description": "Test workflow",
                "metadata": {
                    "status": "active",
                    "last_revision": "2026-07-04",
                    "edited_by": "admin",
                },
                "links": _LINKS,
                "edges": [],
            },
        ),
        (
            validate_parameter_node,
            {
                "type": "parameter",
                "id": "PARAM-test",
                "key": "test_param",
                "name": "Test Parameter",
                "parameter_class": "physical_quantity",
                "description": "Test parameter",
                "metadata": {
                    "last_revision": "2026-07-04",
                    "edited_by": "admin",
                },
                "links": _LINKS,
                "edges": [],
            },
        ),
        (
            validate_lookup_node,
            {
                "type": "lookup",
                "key": "test_lookup",
                "name": "Test Lookup",
                "description": "Test lookup",
                "metadata": {
                    "last_revision": "2026-07-04",
                    "edited_by": "admin",
                },
                "table_id": "asme-b313-table-A-1",
                "output_param": "PARAM-allowable-stress",
                "links": _LINKS,
                "edges": [],
            },
        ),
        (
            validate_validation_rule_node,
            {
                "type": "validation_rule",
                "key": "test_valrule",
                "name": "Test Rule",
                "description": "Test validation rule",
                "validates": ["PARAM-internal-design-gage-pressure"],
                "authority": {
                    "authorized_by": ["304.1.2-a"],
                    "authority_context_required": True,
                },
                "metadata": {
                    "status": "active",
                    "last_revision": "2026-07-04",
                    "edited_by": "admin",
                },
                "links": _LINKS,
                "edges": [],
            },
        ),
        (
            validate_unit_node,
            {
                "type": "unit",
                "id": "UNIT-test",
                "symbol": "test",
                "dimension": "DIM-pressure",
                "metadata": {
                    "last_revision": "2026-07-04",
                    "edited_by": "admin",
                },
                "conversion": {"target": "UNIT-test", "factor": 1, "offset": 0},
                "links": _LINKS,
                "edges": [],
            },
        ),
        (
            validate_authority_node,
            {
                "type": "authority",
                "id": "AUTH-TEST",
                "key": "test_auth",
                "name": "Test Authority",
                "authority_class": "design_code",
                "description": "Test authority",
                "metadata": {
                    "last_revision": "2026-07-04",
                    "edited_by": "admin",
                },
                "links": _LINKS,
            },
        ),
    ],
)
def test_knowledge_node_validators_reject_links_block(validator, meta) -> None:
    issues = validator(meta)
    assert any(_EXPECTED_MSG in issue for issue in issues)
