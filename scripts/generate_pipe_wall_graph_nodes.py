#!/usr/bin/env python3
"""Generate micro-graph parameter and support nodes for pipe wall thickness."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODES = ROOT / "standards" / "asme" / "asme_b31.3" / "nodes"

PATHS = {
    "B313-WF-PIPE-WALL-THICKNESS": "workflows/B313-WF-PIPE-WALL-THICKNESS",
    "B313-WF-MAWP": "workflows/B313-WF-MAWP",
    "B313-304.1.1": "304/304.1/304.1.1",
    "B313-304.1.2": "304/304.1/304.1.2",
    "B313-304.1.3": "304/304.1/304.1.3",
    "B313-MAWP-SECTION": "304/304.1/mawp_definition",
    "B313-304.1.1-init-text": "304/304.1/304.1.1/text/initiation",
    "B313-assumption-straight-pipe": "304/304.1/304.1.1/assumptions/straight-pipe",
    "B313-interaction-pressure-loading": "304/304.1/304.1.1/interactions/pressure-loading",
    "B313-eq-2": "304/304.1/304.1.1/equations/eq-2",
    "B313-eq-2-intro": "304/304.1/304.1.1/equations/eq-2-intro",
    "B313-eq-2-result": "304/304.1/304.1.1/equations/eq-2-result",
    "B313-eq-wall-thickness": "304/304.1/304.1.2/equations/wall-thickness",
    "B313-eq-wall-thickness-intro": "304/304.1/304.1.2/equations/wall-thickness-intro",
    "B313-eq-wall-thickness-result": "304/304.1/304.1.2/equations/wall-thickness-result",
    "B313-eq-mawp": "304/304.1/mawp_definition/equations/mawp",
    "B313-lookup-allowable-stress": "appendix_A/lookups/allowable-stress",
    "B313-table-A-1-REF": "appendix_A/tables/B313-table-A-1-ref",
}


def write_node(rel_path: str, yaml_body: str, md_body: str = "") -> None:
    folder = NODES / rel_path
    folder.mkdir(parents=True, exist_ok=True)
    content = f"---\n{yaml_body.strip()}\n---\n\n{md_body}".rstrip() + "\n"
    (folder / "node.yaml").write_text(content, encoding="utf-8")


def write_param(node_id: str, yaml_body: str) -> None:
    write_node(f"parameters/{node_id}", yaml_body)


PARAMS = [
    ("B313-param-c", "c", "corrosion_allowance", "Corrosion allowance", "mm", None,
     "Sum of mechanical allowances plus corrosion and erosion allowances.",
     "For c (mechanical allowances): confirm the corrosion allowance value.",
     {"method": "user_input", "default": {"value": 0.5, "unit": "mm", "requires_confirmation": True}}),
    ("B313-param-D", "D", "outside_diameter", "Outside diameter", "mm", None,
     "Outside diameter of pipe as listed in tables or as measured.",
     "Please provide the outside diameter of the pipe (mm or in).",
     {"method": "table_lookup", "keys": ["nominal_pipe_size"], "table_id": "asme_b36.10"}),
    ("B313-param-P", "P", "design_pressure", "Design pressure", "Pa", None,
     "Internal design gage pressure.",
     "To continue the calculation, I need the design pressure.",
     {"method": "user_input"}),
    ("B313-param-S", "S", "allowable_stress", "Allowable stress", "Pa", None,
     "Stress value from Table A-1.",
     "Allowable stress will be looked up from Table A-1.",
     {"method": "table_lookup", "keys": ["material", "design_temperature"], "table_id": "asme_b31.3_A-1"}),
    ("B313-param-E", "E", "weld_joint_efficiency", "Joint efficiency", "dimensionless", None,
     "Quality factor from Tables A-1A and A-1B.",
     "Please confirm the weld joint quality factor E.",
     {"method": "table_lookup", "keys": ["material", "joint_category"]}),
    ("B313-param-W", "W", "weld_strength_reduction", "Weld strength reduction", "dimensionless", None,
     "Weld strength reduction factor per para. 302.3.5(e).",
     "Please confirm the weld strength reduction factor W.",
     {"method": "table_lookup", "keys": ["material", "design_temperature", "joint_category"]}),
    ("B313-param-Y", "Y", "temperature_coefficient", "Temperature coefficient", "dimensionless", None,
     "Coefficient from Table 304.1.1.",
     "Temperature coefficient Y from Table 304.1.1.",
     {"method": "table_lookup", "keys": ["design_temperature"], "table_id": "asme_b31.3_table_304_1_1"}),
    ("B313-param-t", "t", "thickness", "Pressure design thickness", "mm", None,
     "Pressure design thickness from §304.1.2 or §304.1.3.",
     None,
     {"method": "equation"}),
    ("B313-param-t_m", "t_m", "minimum_required_thickness", "Minimum required thickness", "mm", None,
     "Minimum required thickness including allowances (t + c).",
     None,
     {"method": "equation"}),
    ("B313-param-material", "material", "material", "Material", "dimensionless", 30,
     "Pipe material specification.",
     "I need the pipe material specification to look up allowable stress.",
     {"method": "user_input"}),
    ("B313-param-design_temperature", "T", "design_temperature", "Design temperature", "K", 35,
     "Design metal temperature.",
     "Please provide the design temperature.",
     {"method": "user_input"}),
    ("B313-param-nps", "NPS", "nominal_pipe_size", "Nominal pipe size", "dimensionless", 45,
     "Nominal pipe size for dimension lookup.",
     "Please provide the nominal pipe size (NPS).",
     {"method": "user_input"}),
    ("B313-param-joint_category", "joint", "joint_category", "Joint category", "dimensionless", 65,
     "Weld joint category for quality factor lookup.",
     "Please provide the joint category.",
     {"method": "user_input"}),
    ("B313-param-mawp", "MAWP", "mawp", "Maximum allowable working pressure", "Pa", None,
     "Calculated maximum allowable working pressure.",
     None,
     {"method": "equation"}),
]


def _requires_yaml(entries: list[tuple[str, int]]) -> str:
    lines = ["requires:"]
    for node_id, priority in entries:
        lines.append(f"  - node_id: {node_id}")
        lines.append(f"    priority: {priority}")
    return "\n".join(lines)

SECTION_304_1_1 = """id: B313-304.1.1
type: standard_section
title: Required Thickness and Nomenclature for Straight Pipe
paragraph: "304.1.1"
section: "304 Pressure Design of Components"
topic: pipe_wall_thickness
revision_year: 2024

contains:
  - B313-eq-2
  - B313-interaction-pressure-loading
  - B313-assumption-straight-pipe
  - B313-304.1.1-init-text

defines:
  - B313-param-c
  - B313-param-D
  - B313-param-P
  - B313-param-S
  - B313-param-E
  - B313-param-W
  - B313-param-Y
  - B313-param-t
  - B313-param-t_m
"""

SECTION_304_1_2 = """id: B313-304.1.2
type: standard_section
title: Straight Pipe Under Internal Pressure
paragraph: "304.1.2"
section: "304 Pressure Design of Components"
revision_year: 2024

contains:
  - B313-eq-wall-thickness
  - B313-eq-wall-thickness-intro
  - B313-eq-wall-thickness-result

requires:
  - B313-param-P
  - B313-param-D
  - B313-param-S
  - B313-param-E
  - B313-param-W
  - B313-param-Y

calculates:
  - B313-param-t
"""

MAWP_SECTION = """id: B313-MAWP-SECTION
type: standard_section
title: MAWP Pressure Design
paragraph: mawp
section: "304 Pressure Design of Components"
revision_year: 2024

contains:
  - B313-eq-mawp

requires:
  - B313-param-material
  - B313-param-design_temperature
  - B313-param-t

calculates:
  - B313-param-mawp
"""


def main() -> None:
    write_node(
        PATHS["B313-WF-PIPE-WALL-THICKNESS"],
        """id: B313-WF-PIPE-WALL-THICKNESS
type: workflow
title: Pipe Wall Thickness Design
version: "1.0"
status: draft
engineering_intent: pipe_wall_thickness_design
slug: pipe_wall_thickness_design
purpose: >
  Entry point for designing or verifying required pipe wall thickness under
  internal or external pressure per ASME B31.3 pressure design provisions.
anchors_to: B313-304.1.1
goal_output: B313-param-t_m
contains:
  - B313-304.1.1-init-text
requires:
  - B313-assumption-straight-pipe
  - B313-interaction-pressure-loading
""",
        "Verify or calculate the minimum required wall thickness for piping.",
    )

    write_node(
        PATHS["B313-WF-MAWP"],
        """id: B313-WF-MAWP
type: workflow
title: Maximum Allowable Working Pressure (MAWP)
version: "1.0"
status: draft
engineering_intent: mawp_design
slug: mawp_design
purpose: >
  Calculate the maximum allowable working pressure of piping components per ASME B31.3.
anchors_to: B313-MAWP-SECTION
goal_output: B313-param-mawp
requires:
  - B313-assumption-straight-pipe
""",
        "Calculate maximum allowable working pressure for piping components.",
    )

    write_node(PATHS["B313-304.1.1"], SECTION_304_1_1, "# ASME B31.3 §304.1.1")
    write_node(PATHS["B313-304.1.2"], SECTION_304_1_2, "# ASME B31.3 §304.1.2")
    write_node(PATHS["B313-MAWP-SECTION"], MAWP_SECTION, "# MAWP calculation section")

    write_node(
        PATHS["B313-304.1.1-init-text"],
        """id: B313-304.1.1-init-text
type: text
role: initiation
title: Calculation of Minimum Required Thickness
display_order: 1
""",
        "Calculation of minimum required thickness of a straight section pipe (ASME B31.3 §304.1.1).",
    )

    write_node(
        PATHS["B313-assumption-straight-pipe"],
        """id: B313-assumption-straight-pipe
type: assumption
field: straight_pipe_section
required_for_expansion: true
requires_confirmation: true
allowed_values: [true, false]
blocks_expansion_on: [false]
question: >
  Is the pipe wall thickness you would like to calculate for a straight section of pipe?
expansion_block_message: Non-straight pipe sections are not yet supported.
located_in: B313-304.1.1
""",
    )

    write_node(
        PATHS["B313-interaction-pressure-loading"],
        """id: B313-interaction-pressure-loading
type: interaction
field: pressure_loading
mode: decision
required: true
required_for_expansion: true
options:
  - internal_pressure
  - external_pressure
question: >
  Is the pipe subjected to internal or external pressure?
edges:
  - to: B313-304.1.2
    type: next_step
    when: {field: pressure_loading, in: [internal_pressure]}
  - to: B313-304.1.3
    type: next_step
    when: {field: pressure_loading, in: [external_pressure]}
""",
    )

    write_node(
        PATHS["B313-304.1.3"],
        """id: B313-304.1.3
type: standard_section
title: Straight Pipe Under External Pressure
paragraph: "304.1.3"
section: "304 Pressure Design of Components"
revision_year: 2024
requires:
  - B313-param-P
calculates:
  - B313-param-t
""",
        "# External pressure path (stub — expands when external_pressure selected)",
    )

    write_node(
        PATHS["B313-eq-2"],
        f"""id: B313-eq-2
type: equation
equation_id: eq-2
execution_phase: definition
sympy: "t_m = t + c"
display_latex: "t_m = t + c"
{_requires_yaml([("B313-param-t", 85), ("B313-param-c", 90)])}
calculates:
  - B313-param-t_m
explains:
  - B313-eq-2-intro
  - B313-eq-2-result
""",
    )

    write_node(
        PATHS["B313-eq-2-intro"],
        """id: B313-eq-2-intro
type: text
role: equation_intro
""",
        "The required thickness of straight sections of pipe shall be determined in accordance with eq. (2): t_m = t + c.",
    )

    write_node(
        PATHS["B313-eq-2-result"],
        """id: B313-eq-2-result
type: text
role: result_explanation
""",
        "The minimum required thickness t_m is the sum of pressure design thickness t and total allowances c.",
    )

    write_node(
        PATHS["B313-eq-wall-thickness"],
        f"""id: B313-eq-wall-thickness
type: equation
equation_id: wall_thickness
sympy: "t = P*D / (2*(S*E*W + P*Y))"
display_latex: "t = PD / (2(SEW + PY))"
{_requires_yaml([
    ("B313-param-P", 40),
    ("B313-param-D", 50),
    ("B313-param-S", 60),
    ("B313-param-E", 70),
    ("B313-param-W", 75),
    ("B313-param-Y", 80),
])}
calculates:
  - B313-param-t
explains:
  - B313-eq-wall-thickness-intro
  - B313-eq-wall-thickness-result
next_step:
  - B313-eq-2
""",
    )

    write_node(
        PATHS["B313-eq-wall-thickness-intro"],
        """id: B313-eq-wall-thickness-intro
type: text
role: equation_intro
""",
        "For straight pipe under internal pressure, the pressure design thickness is calculated per eq. (3).",
    )

    write_node(
        PATHS["B313-eq-wall-thickness-result"],
        """id: B313-eq-wall-thickness-result
type: text
role: result_explanation
""",
        "The calculated t is the pressure design thickness before adding mechanical and corrosion allowances.",
    )

    write_node(
        PATHS["B313-eq-mawp"],
        f"""id: B313-eq-mawp
type: equation
equation_id: mawp
sympy: "MAWP = S*E*W*t / (D - 2*t*Y)"
display_latex: "MAWP = SEWt / (D - 2tY)"
{_requires_yaml([
    ("B313-param-S", 60),
    ("B313-param-E", 70),
    ("B313-param-W", 75),
    ("B313-param-t", 85),
    ("B313-param-D", 50),
    ("B313-param-Y", 80),
])}
calculates:
  - B313-param-mawp
""",
    )

    write_node(
        PATHS["B313-lookup-allowable-stress"],
        """id: B313-lookup-allowable-stress
type: lookup
table_id: asme_b31.3_A-1
output_param: B313-param-S
keys:
  - material
  - design_temperature
interpolation: true
uses_table:
  - B313-table-A-1-REF
requires:
  - B313-param-material
  - B313-param-design_temperature
outputs:
  - B313-param-S
""",
    )

    write_node(
        PATHS["B313-table-A-1-REF"],
        """id: B313-table-A-1-REF
type: table
table_id: asme_b31.3_A-1
standard: asme_b31.3
title: Table A-1 Allowable Stress
lookup_keys:
  - material
  - design_temperature
""",
    )

    write_param(
        "B313-param-S",
        """id: B313-param-S
type: parameter
symbol: S
input_id: allowable_stress
title: Allowable stress
unit: Pa
description: Stress value from Table A-1.
question: Allowable stress will be looked up from Table A-1.
resolution:
  method: table_lookup
  keys: [material, design_temperature]
  table_id: asme_b31.3_A-1
defined_in:
  - B313-304.1.1
""",
    )

    for node_id, symbol, input_id, title, unit, _priority, desc, question, resolution in PARAMS:
        if node_id == "B313-param-S":
            continue
        q_line = f'question: >\n  {question}\n' if question else ""
        res_yaml = f'resolution:\n  method: {resolution["method"]}\n'
        if "table_id" in resolution:
            res_yaml += f'  table_id: {resolution["table_id"]}\n'
        if "keys" in resolution:
            res_yaml += f'  keys: {resolution["keys"]}\n'
        write_param(
            node_id,
            f"""id: {node_id}
type: parameter
symbol: {symbol}
input_id: {input_id}
title: {title}
unit: {unit}
description: >
  {desc}
{q_line}{res_yaml}defined_in:
  - B313-304.1.1
""",
        )

    print(f"Generated micro-graph nodes under {NODES}")


if __name__ == "__main__":
    main()
