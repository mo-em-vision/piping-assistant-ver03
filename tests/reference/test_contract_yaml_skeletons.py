"""Validate minimal YAML skeletons in node contracts against existing validators."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from engine.validation.authority_node_validator import validate_authority_node
from engine.validation.equation_node_validator import validate_equation_node
from engine.validation.lookup_node_validator import validate_lookup_node
from engine.validation.node_revision_metadata import validate_revision_metadata
from engine.validation.parameter_node_validator import validate_parameter_node
from engine.validation.paragraph_node_validator import validate_paragraph_node
from engine.validation.unit_node_validator import validate_unit_node
from engine.validation.validation_rule_node_validator import validate_validation_rule_node
from engine.validation.workflow_node_validator import validate_workflow_node

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "audits" / "contracts" / "nodes"

_SECTION6_HEADING = re.compile(r"^##\s+6\.\s+Copyable minimal YAML skeleton\s*$", re.MULTILINE)
_FENCE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


def _extract_section6_yaml(contract_path: Path) -> str:
    text = contract_path.read_text(encoding="utf-8")
    match = _SECTION6_HEADING.search(text)
    if not match:
        raise AssertionError(f"{contract_path.name}: missing section 6 heading")
    rest = text[match.end() :]
    fence = _FENCE.search(rest)
    if not fence:
        raise AssertionError(f"{contract_path.name}: missing yaml fence in section 6")
    return fence.group(1).strip()


def _parse_frontmatter(yaml_text: str) -> dict:
    if yaml_text.startswith("---"):
        parts = yaml_text.split("---", 2)
        if len(parts) >= 3:
            loaded = yaml.safe_load(parts[1])
            if isinstance(loaded, dict):
                return loaded
    loaded = yaml.safe_load(yaml_text)
    if not isinstance(loaded, dict):
        raise AssertionError("skeleton did not parse to a mapping")
    return loaded


def _assert_no_issues(issues: list[str], *, contract: str) -> None:
    assert not issues, f"{contract}: validator issues: {issues}"


def test_paragraph_skeleton() -> None:
    meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / "paragraph.md"))
    _assert_no_issues(validate_paragraph_node(meta), contract="paragraph.md")


def test_parameter_skeleton() -> None:
    meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / "parameter.md"))
    _assert_no_issues(validate_parameter_node(meta), contract="parameter.md")


def test_equation_skeleton() -> None:
    meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / "equation.md"))
    _assert_no_issues(validate_equation_node(meta), contract="equation.md")


def test_lookup_skeleton() -> None:
    meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / "lookup.md"))
    _assert_no_issues(validate_lookup_node(meta), contract="lookup.md")


def test_validation_rule_skeleton() -> None:
    meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / "validation-rule.md"))
    _assert_no_issues(validate_validation_rule_node(meta), contract="validation-rule.md")


def test_workflow_skeleton() -> None:
    meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / "workflow.md"))
    _assert_no_issues(validate_workflow_node(meta), contract="workflow.md")


def test_unit_skeleton() -> None:
    meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / "unit.md"))
    _assert_no_issues(validate_unit_node(meta), contract="unit.md")


def test_authority_skeleton() -> None:
    meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / "authority.md"))
    _assert_no_issues(validate_authority_node(meta), contract="authority.md")


def test_types_without_dedicated_validator_have_revision_metadata() -> None:
    for name in ("text.md", "quantity.md", "designation.md", "table.md", "dimension.md", "concept.md"):
        meta = _parse_frontmatter(_extract_section6_yaml(CONTRACTS_DIR / name))
        _assert_no_issues(validate_revision_metadata(meta), contract=name)


def test_audit_script_does_not_parse_contract_markdown() -> None:
    audit_source = (PROJECT_ROOT / "scripts" / "audit_current_node_yaml.py").read_text(encoding="utf-8")
    assert "audits/contracts" not in audit_source
    assert "contracts/nodes" not in audit_source
    assert ".md" not in audit_source.split("REPORT_PATH")[0]
