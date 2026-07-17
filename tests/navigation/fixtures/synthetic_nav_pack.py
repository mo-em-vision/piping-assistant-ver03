"""Temporary synthetic workflow pack for navigation architecture-contract tests."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from engine.graph.graph_builder import GraphBuilder
from engine.graph.graph_store import GraphStore
from engine.reference.standards_reader import StandardsReader

WORKFLOW_ROOT = "nav_contract_alpha"
WORKFLOW_NODE_ID = "WF-NAV-CONTRACT-ALPHA"
PACK_SLUG = "alpha_nav"
AUTHORITY_ID = "AUTH-NAV-ALPHA"


def _write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def _parameter_yaml(
    *,
    param_id: str,
    key: str,
    name: str,
    applies_when: list[dict] | None = None,
    resolution_branches: list[dict] | None = None,
    default_branch: str | None = None,
) -> str:
    applies_block = ""
    if applies_when:
        lines = ["applicability:", "  applies_when:"]
        for clause in applies_when:
            lines.append(f"  - parameter: {clause['parameter']}")
            lines.append(f"    operator: {clause['operator']}")
            lines.append(f"    value: {clause['value']}")
        applies_block = "\n".join(lines)

    resolution_block = ""
    if resolution_branches:
        branch_lines = ["  resolution_branches:"]
        for branch in resolution_branches:
            branch_lines.append(f"    - id: {branch['id']}")
            branch_lines.append(f"      label: {branch['label']}")
            branch_lines.append(f"      method: {branch['method']}")
            if branch.get("via_parameters"):
                branch_lines.append("      via_parameters:")
                for target in branch["via_parameters"]:
                    branch_lines.append(f"        - {target}")
            if branch.get("lookup"):
                branch_lines.append(f"      lookup: {branch['lookup']}")
        resolution_block = "\n".join(branch_lines)
        default_value = default_branch or resolution_branches[0]["id"]
        composer = "resolution_branch"
    else:
        default_value = ""
        composer = "number"

    return f"""---
id: {param_id}
type: parameter
key: {key}
name: {name}
parameter_class: physical_quantity
description: Synthetic navigation contract parameter {key}.
question: Provide {name}.
canonical_symbol: {key[:1].upper()}
edges: []
{applies_block}
metadata:
  status: active
  version: 1
  last_revision: 2026-07-16
  edited_by: test
  composer_input: {composer}
  default_value: {default_value}
{resolution_block}
---
"""


def _gathering_order_block(fields: Iterable[str]) -> str:
    lines = ["      parameter_gathering:"]
    for field in fields:
        lines.append(f"      - {field}")
    return "\n".join(lines)


def build_synthetic_nav_pack(
    tmp_path: Path,
    *,
    gathering_order: list[str] | None = None,
) -> tuple[StandardsReader, str]:
    """Build an isolated synthetic standards pack under ``tmp_path``."""
    standards_root = tmp_path / "standards"
    pack_root = standards_root / "alpha" / PACK_SLUG
    nodes = pack_root / "nodes"

    gathering = gathering_order or [
        "alpha_resolution",
        "alpha_input_x",
        "alpha_input_y",
        "alpha_lookup_key",
    ]

    _write_yaml(
        pack_root / "pack.yaml",
        f"""---
id: {PACK_SLUG}
title: Navigation Contract Alpha Pack
authority: {AUTHORITY_ID}
edition: 2026
source_language: en
---
""",
    )

    _write_yaml(
        nodes / "authority" / f"{AUTHORITY_ID}.yaml",
        f"""---
id: {AUTHORITY_ID}
type: authority
key: nav_alpha
name: Navigation Contract Alpha Authority
authority_class: design_code
publisher: TEST
title: Navigation Contract Alpha
description: Synthetic authority for navigation contract tests.
metadata:
  status: active
  last_revision: 2026-07-16
  edited_by: test
edges: []
---
""",
    )

    _write_yaml(
        nodes / "workflow" / f"{WORKFLOW_NODE_ID}.yaml",
        f"""---
id: {WORKFLOW_NODE_ID}
type: workflow
key: {WORKFLOW_ROOT}
name: Navigation Contract Alpha
workflow_class: design_calculation
description: Synthetic workflow for navigation ownership contract tests.
expected_authorities:
- {AUTHORITY_ID}
entry_points:
- parameter: PARAM-alpha-derived-output
  role: definition_anchor
goal_expansion:
  root_goal:
    goal_class: calculation_goal
    target_parameter: PARAM-alpha-derived-output
    completion:
      when: target_parameter_satisfied
      status: finished
runtime:
  navigation:
    assumption_gate_fields:
    - alpha_gate
    phases:
      expansion_assumptions:
      - alpha_gate
      path_decisions:
      - alpha_path
{_gathering_order_block(gathering)}
      coefficient_resolution: []
      execution_assumptions: []
      definition_equation_completion: []
  interactions:
  - variable: alpha_path
    mode: decision
    required: true
    required_for_expansion: true
    options:
    - path_x
    - path_y
    question: Select alpha path.
edges:
- type: depends_on
  target: ALPHA-ROOT
metadata:
  status: active
  version: 1
  last_revision: 2026-07-16
  edited_by: test
---
""",
    )

    _write_yaml(
        nodes / "paragraph" / "ALPHA-ROOT.yaml",
        f"""---
id: ALPHA-ROOT
type: paragraph
key: alpha_root
title: Alpha Root Section
authority: {AUTHORITY_ID}
paragraph_number: ALPHA-ROOT
text:
  original: Synthetic root paragraph for navigation contract tests.
hierarchy:
  parent: ALPHA-ROOT
  children:
  - ALPHA-PATH-X
  - ALPHA-PATH-Y
edges:
- type: belongs_to_authority
  target: {AUTHORITY_ID}
- type: depends_on
  target: ALPHA-PATH-X
  when:
    field: alpha_path
    in: [path_x]
- type: depends_on
  target: ALPHA-PATH-Y
  when:
    field: alpha_path
    in: [path_y]
execution:
  assumptions:
  - id: alpha_gate
    field: alpha_gate
    description: Expansion gate for alpha workflow.
    required_for_expansion: true
    allowed_values: [true]
    default: true
interactions:
- variable: alpha_path
  mode: decision
  required: true
  required_for_expansion: true
  options:
  - path_x
  - path_y
metadata:
  status: active
  last_revision: 2026-07-16
  edited_by: test
---
""",
    )

    _write_yaml(
        nodes / "paragraph" / "ALPHA-PATH-X.yaml",
        f"""---
id: ALPHA-PATH-X
type: paragraph
key: alpha_path_x
title: Alpha Path X
authority: {AUTHORITY_ID}
paragraph_number: ALPHA-PATH-X
text:
  original: Path X branch for alpha workflow.
hierarchy:
  parent: ALPHA-ROOT
  children: []
edges:
- type: belongs_to_authority
  target: {AUTHORITY_ID}
- type: introduces_parameter
  target: PARAM-alpha-input-x
- type: references_lookup
  target: ALPHA-LOOKUP
- type: references_equation
  target: ALPHA-EQ
metadata:
  status: active
  last_revision: 2026-07-16
  edited_by: test
---
""",
    )

    _write_yaml(
        nodes / "paragraph" / "ALPHA-PATH-Y.yaml",
        f"""---
id: ALPHA-PATH-Y
type: paragraph
key: alpha_path_y
title: Alpha Path Y
authority: {AUTHORITY_ID}
paragraph_number: ALPHA-PATH-Y
text:
  original: Path Y branch for alpha workflow.
hierarchy:
  parent: ALPHA-ROOT
  children: []
edges:
- type: belongs_to_authority
  target: {AUTHORITY_ID}
- type: introduces_parameter
  target: PARAM-alpha-input-y
metadata:
  status: active
  last_revision: 2026-07-16
  edited_by: test
---
""",
    )

    _write_yaml(
        nodes / "parameter" / "PARAM-alpha-gate.yaml",
        _parameter_yaml(
            param_id="PARAM-alpha-gate",
            key="alpha_gate",
            name="Alpha Gate",
        ),
    )
    _write_yaml(
        nodes / "parameter" / "PARAM-alpha-path.yaml",
        _parameter_yaml(
            param_id="PARAM-alpha-path",
            key="alpha_path",
            name="Alpha Path",
        ),
    )
    _write_yaml(
        nodes / "parameter" / "PARAM-alpha-input-x.yaml",
        _parameter_yaml(
            param_id="PARAM-alpha-input-x",
            key="alpha_input_x",
            name="Alpha Input X",
            applies_when=[
                {"parameter": "PARAM-alpha-path", "operator": "equals", "value": "path_x"},
            ],
        ),
    )
    _write_yaml(
        nodes / "parameter" / "PARAM-alpha-input-y.yaml",
        _parameter_yaml(
            param_id="PARAM-alpha-input-y",
            key="alpha_input_y",
            name="Alpha Input Y",
            applies_when=[
                {"parameter": "PARAM-alpha-path", "operator": "equals", "value": "path_y"},
            ],
        ),
    )
    _write_yaml(
        nodes / "parameter" / "PARAM-alpha-lookup-key.yaml",
        _parameter_yaml(
            param_id="PARAM-alpha-lookup-key",
            key="alpha_lookup_key",
            name="Alpha Lookup Key",
            applies_when=[
                {"parameter": "PARAM-alpha-path", "operator": "equals", "value": "path_x"},
            ],
        ),
    )
    _write_yaml(
        nodes / "parameter" / "PARAM-alpha-lookup-output.yaml",
        _parameter_yaml(
            param_id="PARAM-alpha-lookup-output",
            key="alpha_lookup_output",
            name="Alpha Lookup Output",
            applies_when=[
                {"parameter": "PARAM-alpha-path", "operator": "equals", "value": "path_x"},
            ],
        ),
    )
    _write_yaml(
        nodes / "parameter" / "PARAM-alpha-derived-output.yaml",
        _parameter_yaml(
            param_id="PARAM-alpha-derived-output",
            key="alpha_derived_output",
            name="Alpha Derived Output",
            applies_when=[
                {"parameter": "PARAM-alpha-path", "operator": "equals", "value": "path_x"},
            ],
        ),
    )
    _write_yaml(
        nodes / "parameter" / "PARAM-alpha-resolution.yaml",
        _parameter_yaml(
            param_id="PARAM-alpha-resolution",
            key="alpha_resolution",
            name="Alpha Resolution",
            resolution_branches=[
                {
                    "id": "branch_x",
                    "label": "Branch X",
                    "method": "user_input",
                    "via_parameters": ["PARAM-alpha-input-x"],
                },
                {
                    "id": "branch_y",
                    "label": "Branch Y",
                    "method": "user_input",
                    "via_parameters": ["PARAM-alpha-input-y"],
                },
            ],
            default_branch="branch_x",
        ),
    )

    _write_yaml(
        nodes / "lookup" / "ALPHA-LOOKUP.yaml",
        """---
id: ALPHA-LOOKUP
type: lookup
key: alpha_lookup
name: Alpha Lookup
description: Synthetic lookup from alpha_lookup_key to alpha_lookup_output.
inputs:
- id: alpha_lookup_key
  name: alpha_lookup_key
  task_input_id: alpha_lookup_key
  required: true
  source: user_input
  unit: dimensionless
returns:
- parameter: PARAM-alpha-lookup-output
  symbol: L
lookup:
  table: ALPHA-TABLE
  rule: by_key
  bindings:
    alpha_lookup_key: PARAM-alpha-lookup-key
applicability:
  applies_when:
  - parameter: PARAM-alpha-path
    operator: equals
    value: path_x
edges:
- type: returns_parameter
  target: PARAM-alpha-lookup-output
- type: requires_parameter
  target: PARAM-alpha-lookup-key
metadata:
  status: active
  version: 1
  last_revision: 2026-07-16
  edited_by: test
---
""",
    )

    _write_yaml(
        nodes / "tables" / "ALPHA-TABLE.yaml",
        """---
id: ALPHA-TABLE
type: table
key: alpha_table
title: Alpha Lookup Table
table_number: ALPHA-1
status: active
revision_year: 2026
columns:
- id: alpha_lookup_key
  name: alpha_lookup_key
- id: alpha_lookup_output
  name: alpha_lookup_output
rows:
- alpha_lookup_key: key_a
  alpha_lookup_output: 10.0
- alpha_lookup_key: key_b
  alpha_lookup_output: 20.0
lookup_rules:
  by_key:
    strategy: identity
    inputs:
      alpha_lookup_key:
        resolver: identity
        column: alpha_lookup_key
    outputs:
      alpha_lookup_output:
        column: alpha_lookup_output
        parameter: PARAM-alpha-lookup-output
metadata:
  status: active
  last_revision: 2026-07-16
  edited_by: test
edges: []
---
""",
    )

    _write_yaml(
        nodes / "equation" / "ALPHA-EQ.yaml",
        """---
id: ALPHA-EQ
type: equation
key: alpha_eq
name: Alpha Derived Equation
equation_class: calculation
calculation_kind: expression
description: Synthetic equation producing alpha_derived_output.
authority:
  authorized_by:
  - ALPHA-PATH-X
  authority_context_required: false
requires:
- symbol: L
  required: true
  description: Lookup output
  parameter: PARAM-alpha-lookup-output
- symbol: X
  required: true
  description: Path X input
  parameter: PARAM-alpha-input-x
calculates:
- symbol: D
  parameter: PARAM-alpha-derived-output
edges:
- type: requires_parameter
  target: PARAM-alpha-lookup-output
  alias: L
- type: requires_parameter
  target: PARAM-alpha-input-x
  alias: X
- type: calculates_parameter
  target: PARAM-alpha-derived-output
metadata:
  status: active
  version: 1
  last_revision: 2026-07-16
  edited_by: test
display:
  text: D = L + X
variables:
  L:
    symbol: L
    description: Lookup output
    unit: dimensionless
  X:
    symbol: X
    description: Path X input
    unit: dimensionless
steps:
- name: compute_alpha_derived_output
  description: Combine lookup output with branch input.
  expressions:
  - expression: L + X
    assign: D
outputs:
- symbol: D
  parameter: PARAM-alpha-derived-output
  unit: dimensionless
---
""",
    )

    GraphBuilder(pack_root).build()
    store = GraphStore(pack_root)
    store.load(prefer_cache=False)
    if not store.available:
        raise RuntimeError("Synthetic navigation pack failed to compile")

    reader = StandardsReader(standards_root, standard=PACK_SLUG)
    return reader, WORKFLOW_ROOT


def synthetic_gate_open_facts(task_id: str = "alpha-nav-test"):
    from models.input import InputSource, InputStatus
    from tests.helpers.facts import facts_from_inputs, legacy_input

    return facts_from_inputs(
        {
            "alpha_gate": legacy_input(
                "alpha_gate",
                True,
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "alpha_path": legacy_input(
                "alpha_path",
                "path_x",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id=task_id,
    )
