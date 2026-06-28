---
id: B313-304.3.3
type: calculation
title: Reinforcement of Welded Branch Connections
version: "2026"
status: draft
created: "2026-06-28"
modified: "2026-06-28"

paragraph: "304.3.3"
section: "304 Pressure Design of Components"
topic: branch_connections
revision_year: 2024

purpose: >
  Define branch connection nomenclature, required reinforcement area, available
  reinforcement areas, reinforcement zone geometry, and rules for multiple branches
  and added reinforcement.
engineering_intent: branch_connection_design

depends_on:
  - node_id: B313-304.3.1
    dependency_type: reference
  - node_id: B313-304.3.2
    dependency_type: reference
  - node_id: B313-304.1.1
    dependency_type: reference
  - node_id: B313-304.1.2
    dependency_type: calculation
  - node_id: B313-302.3.5
    dependency_type: reference
    subsection: e
  - node_id: B313-table-A-1
    dependency_type: lookup

references:
  - node_id: B313-304.1.1
    reason: Corrosion allowance c and thickness nomenclature.
  - node_id: B313-304.1.2
    reason: Pressure design thickness t for run and branch pipe.
  - node_id: B313-302.3.5
    subsection: e
    reason: Weld joint strength reduction factor W.
  - node_id: B313-328.5.4
    reason: Minimum weld dimensions for area A_4.
  - node_id: B313-300.2
    reason: Branch connection fitting thickness definitions.
  - node_id: B313-Appendix-J
    reason: Supplemental nomenclature definitions.

subsections:
  - id: a
    label: "(a)"
    title: Nomenclature
    text: >
      Symbols for branch connection reinforcement design illustrated in
      Figure 304.3.3-1.
  - id: b
    label: "(b)"
    title: Required Reinforcement Area
    equations:
      - id: eq-6
        display: "A_1 = t_h d_1 (2 \\sin \\beta)"
        file: equations/eq_6_required_reinforcement_area.md
  - id: c
    label: "(c)"
    title: Available Area
    equations:
      - id: eq-6a
        display: "A_2 + A_3 + A_4 \\ge A_1"
        file: equations/eq_6a_available_area_check.md
      - id: eq-7
        display: "A_2 = (2d_2 - d_1)(T_h - t_h - c)"
        file: equations/eq_7_area_a2.md
      - id: eq-8
        display: "A_3 = 2L_4(T_b - t_b - c)/\\sin(\\beta)"
        file: equations/eq_8_area_a3.md
  - id: d
    label: "(d)"
    title: Reinforcement Zone
  - id: e
    label: "(e)"
    title: Multiple Branches
  - id: f
    label: "(f)"
    title: Added Reinforcement

equations:
  - id: eq-6
    file: equations/eq_6_required_reinforcement_area.md
  - id: eq-6a
    file: equations/eq_6a_available_area_check.md
  - id: eq-7
    file: equations/eq_7_area_a2.md
  - id: eq-8
    file: equations/eq_8_area_a3.md

nomenclature:
  - symbol: b
    description: Subscript referring to branch.
  - symbol: D_b
    description: Outside diameter of branch pipe.
    unit: mm
    allowed_units: [mm, in]
  - symbol: D_h
    description: Outside diameter of run pipe (or header pipe).
    unit: mm
    allowed_units: [mm, in]
  - symbol: D_s
    description: Outside diameter of reinforcing saddle.
    unit: mm
    allowed_units: [mm, in]
  - symbol: d_1
    description: >
      Effective length removed from pipe at branch. For pipe-to-pipe fabricated
      branches, d_1 = [D_b − 2(T_b − c)]/sin(β).
    unit: mm
    allowed_units: [mm, in]
  - symbol: d_2
    description: >
      Half width of reinforcement zone; d_1 or (T_b − c) + (T_h − c) + d_1/2,
      whichever is greater, but not more than D_h.
    unit: mm
    allowed_units: [mm, in]
  - symbol: h
    description: Subscript referring to run or header.
  - symbol: L_4
    description: >
      Height of reinforcement zone outside run pipe; 2.5(T_h − c) or
      2.5(T_b − c) + T_r, whichever is less.
    unit: mm
    allowed_units: [mm, in]
  - symbol: T_b
    description: Branch pipe wall thickness per purchase specification.
    unit: mm
    allowed_units: [mm, in]
  - symbol: T_h
    description: Run pipe wall thickness per purchase specification.
    unit: mm
    allowed_units: [mm, in]
  - symbol: T_r
    description: >
      Minimum thickness of reinforcing ring or saddle made from pipe, or height
      of the largest 60-deg right triangle in the integral reinforcement area.
    unit: mm
    allowed_units: [mm, in]
  - symbol: t
    description: Pressure design thickness per §304.1.
    unit: mm
    allowed_units: [mm, in]
  - symbol: β
    description: Smaller angle between axes of branch and run.
    unit: deg
  - symbol: A_1
    description: Required reinforcement area.
    unit: mm2
  - symbol: A_2
    description: Area from excess thickness in run pipe wall.
    unit: mm2
  - symbol: A_3
    description: Area from excess thickness in branch pipe wall.
    unit: mm2
  - symbol: A_4
    description: Area from welds and properly attached reinforcement.
    unit: mm2
  - symbol: c
    description: Corrosion allowance per §304.1.1.
    unit: mm
    allowed_units: [mm, in]
    references:
      - node_id: B313-304.1.1

limitations:
  - id: not_yet_implemented
    parameter: calculation
    condition: Branch reinforcement area calculation not yet implemented
    action: reject

trace:
  capture:
    - paragraph_text
    - nomenclature
    - equations
    - inputs
    - outputs
    - warnings

report:
  section_title: "Reinforcement of Welded Branch Connections — §304.3.3"
  include:
    - node_reference
    - paragraph_text
    - nomenclature
    - equations
    - warnings
  explanation_required: true

ai_hints:
  explanation_focus: >
    Explain the reinforcement zone, required area A_1, and how excess wall
    thickness and added metal contribute through A_2, A_3, and A_4.
  common_questions:
    - How is the reinforcement zone defined?
    - When is external pressure A_1 half of the internal value?
    - How does branch allowable stress affect A_3?
  avoid:
    - Do not double-count metal area across overlapping reinforcement zones.
---

# ASME B31.3 §304.3.3 — Reinforcement of Welded Branch Connections

## Paragraph Text

Added reinforcement is required to meet the criteria in (b) and (c) when it is not inherent in the components of the branch connection. Sample problems illustrating the calculations for branch reinforcement are shown in Appendix H.

## (a) Nomenclature

The nomenclature below is used in the pressure design of branch connections. It is illustrated in [Figure 304.3.3-1](figure:B313-304.3.3-1), which does not indicate preferred design or fabrication details. Some of the terms defined in [Appendix J](node:B313-Appendix-J) are subject to further definitions or variations, as follows:

| Symbol | Description |
| ------ | ----------- |
| **b** | subscript referring to branch |
| **D_b** | outside diameter of branch pipe |
| **D_h** | outside diameter of run pipe (or header pipe) |
| **D_s** | outside diameter of reinforcing saddle |
| **d_1** | effective length removed from pipe at branch. For branch intersections where the branch opening is a projection of the branch pipe inside diameter (e.g., pipe-to-pipe fabricated branch), $d_1 = [D_b − 2(T_b − c)]/\sin(\beta)$ |
| **d_2** | “half width” of reinforcement zone $= d_1$ or $(T_b − c) + (T_h − c) + d_1/2$, whichever is greater, but in any case not more than $D_h$ |
| **h** | subscript referring to run or header |
| **L_4** | height of reinforcement zone outside of run pipe $= 2.5(T_h − c)$ or $2.5(T_b − c) + T_r$, whichever is less |
| **T_b** | branch pipe thickness (measured or minimum in accordance with the purchase specification) except for branch connection fittings (see para. [300.2](node:B313-300.2)). For such connections the value of $T_b$ for use in calculating $L_4$, $d_2$, and $A_3$ is the thickness of the reinforcing barrel (minimum per purchase specification), provided that the barrel thickness is uniform (see [Figure K328.5.4-1](figure:K328.5.4-1)) and extends at least to the $L_4$ limit (see [Figure 304.3.3-1](figure:B313-304.3.3-1)) |
| **T_r** | minimum thickness of reinforcing ring or saddle made from pipe (use nominal thickness if made from plate) in Example A, or height of the largest 60-deg right triangle supported by the run and branch outside diameter projected surfaces and lying completely within the area of integral reinforcement in Example B. (=0 if there is no reinforcing ring or saddle) |
| **t** | pressure design thickness of pipe, according to the appropriate wall thickness equation or procedure in para. [304.1](node:B313-304.1.1). For welded pipe, when the branch does not intersect the longitudinal weld of the run, the basic allowable stress, $S$, for the pipe may be used in determining $t_h$ for the purpose of reinforcement calculation only. When the branch does intersect the longitudinal weld of the run, the product $SEW$ (of the stress value, $S$; the appropriate weld joint quality factor, $E_j$, from [Table A-3](table:asme_b31.3_A-3); and the weld joint strength reduction factor, $W$; see para. [302.3.5](node:B313-302.3.5)) for the run pipe shall be used in the calculation. The product $SEW$ of the branch shall be used in calculating $t_b$ |
| **β** | smaller angle between axes of branch and run |

## (b) Required Reinforcement Area

The reinforcement area, $A_1$, required for a branch connection under internal pressure is:

```
$$
A_1 = t_h d_1 (2 \sin \beta)
\tag{6}
$$
```

For a branch connection under external pressure, area $A_1$ is one-half the area calculated by eq. (6), using as $t_h$ the thickness required for external pressure.

## (c) Available Area

The area available for reinforcement is defined as:

```
$$
A_2 + A_3 + A_4 \ge A_1
\tag{6a}
$$
```

These areas are all within the reinforcement zone and are further defined below.

**(1) Area $A_2$** is the area resulting from excess thickness in the run pipe wall:

```
$$
A_2 = (2d_2 - d_1)(T_h - t_h - c)
\tag{7}
$$
```

**(2) Area $A_3$** is the area resulting from excess thickness in the branch pipe wall:

```
$$
A_3 = 2L_4(T_b - t_b - c)/\sin(\beta)
\tag{8}
$$
```

If the allowable stress for the branch pipe wall is less than that for the run pipe, its calculated area shall be reduced in the ratio of allowable stress values of the branch to the run in determining its contributions to area $A_3$.

**(3) Area $A_4$** is the area of other metal provided by welds and properly attached reinforcement [see (f)](node:B313-304.3.3/f). Weld areas shall be based on the minimum dimensions specified in para. [328.5.4](node:B313-328.5.4), except that larger dimensions may be used if the welder has been specifically instructed to make the welds to those dimensions.

## (d) Reinforcement Zone

The reinforcement zone is a parallelogram whose length extends a distance, $d_2$, on each side of the centerline of the branch pipe and whose width starts at the inside surface of the run pipe (in its corroded condition) and extends beyond the outside surface of the run pipe a perpendicular distance, $L_4$.

## (e) Multiple Branches

When two or more branch connections are so closely spaced that their reinforcement zones overlap, the distance between centers of the openings should be at least $1\frac{1}{2}$ times their average diameter, and the area of reinforcement between any two openings shall be not less than 50% of the total that both require. Each opening shall have adequate reinforcement in accordance with (b) and (c). No part of the metal cross section may apply to more than one opening or be evaluated more than once in any combined area. (Consult PFI Standard ES-7, Minimum Length and Spacing for Branch Connections, for detailed recommendations on spacing of welded nozzles.)

## (f) Added Reinforcement

**(1)** Reinforcement added in the form of a ring or saddle as part of area $A_4$ shall be of reasonably constant width.

**(2)** Material used for reinforcement may differ from that of the run pipe provided it is compatible with run and branch pipes with respect to weldability, heat treatment requirements, galvanic corrosion, thermal expansion, etc.

**(3)** If the allowable stress for the reinforcement material is less than that for the run pipe, its calculated area shall be reduced in the ratio of allowable stress values in determining its contribution to area $A_4$.

**(4)** No additional credit may be taken for a material having higher allowable stress value than the run pipe.

---

# Engineering Explanation

This node records the welded branch reinforcement calculation framework. Pressure design thicknesses $t_h$ and $t_b$ come from §304.1; excess wall thickness and added metal within the reinforcement zone supply areas $A_2$ through $A_4$ to satisfy required area $A_1$.

Calculation execution is deferred until branch reinforcement equation executors are implemented.

---

# Decision Logic

This node applies when:

- A welded branch connection requires reinforcement calculation per §304.3.2.
- §304.3.1 applicability limits in subsection (b) are satisfied.

This node does not apply when:

- A §304.3.2 exception allows assuming adequate strength without calculation.
- Branch design is governed by §304.3.4 instead of welded reinforcement rules.

---

# Equation Documentation

See `equations/` for equation definitions:

- `eq_6_required_reinforcement_area.md`
- `eq_6a_available_area_check.md`
- `eq_7_area_a2.md`
- `eq_8_area_a3.md`
