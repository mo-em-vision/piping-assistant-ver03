

**Document Type:** Node Specification & Authoring Standard  

# **Purpose:** 
Define the complete structure of every node file in the ASME B31.3 knowledge graph. Nodes are self-contained and self-executing. They carry the full paragraph text, a structured formula as ordered expression steps, post-execution checks, constants, dependency declarations, and report metadata. No per-case workflow files are needed. One generic executor runs every calculation node in the graph.  
`

---

## 1. What a Node Is

A node represents one ASME B31.3 paragraph or logical unit.

Each node is **self-contained** and **self-executing**. It carries:

- The full verbatim text of the paragraph (so the LLM never needs an external source)
- Structured metadata in YAML frontmatter (so the dependency resolver can parse it without reading prose)
- Its position in the hierarchy (parent, children, cross-references)
- Its applicability conditions (checked before the node runs)
- Its inputs and their sources (user, another node, or a confirmed default)
- Its formula as an ordered list of named expression steps (evaluated by the generic executor)
- Its constants (fixed values the node owns — no external lookup needed)
- Its post-execution checks (validations and re-routing logic)
- Its outputs (what is stored and passed to dependent nodes)
- Its dependencies on other nodes (for topological sort)
- Its report metadata (how its result appears in the grouped output)

**There is no `workflow_id`.** Nodes do not bind to per-case workflows.  
The generic executor reads any node's `formula.steps` and evaluates them in order.  
One executor handles every calculation node in the entire graph.

---

## 2. Generic Executor — Full Specification

There is one executor for all node types. It has no knowledge of any specific
ASME paragraph. It reads the node frontmatter and executes it mechanically.

### 2.1 Execution Sequence

```
Generic Executor receives: node, resolved_inputs, prior_node_outputs

STEP 1 — CONDITION CHECK
  For each condition in node.conditions (in order):
    Evaluate test expression against resolved_inputs
    If test is false:
      Emit routing message
      Follow else_goto → load that node → restart executor
      Stop processing this node
  All conditions passed → continue

STEP 2 — INPUT RESOLUTION
  Build execution scope:
    Start with resolved_inputs (from user and shared input registry)
    For each input where source starts with "node:":
      Look up that node's output in prior_node_outputs
      If not found → dependency not yet resolved → error: wrong execution order
    For each input where source is "default":
      If not yet confirmed → surface default_confirm_prompt to user
      Wait for confirmation → add to scope with source: "default"
    For each input where source is "user":
      If not in resolved_inputs → request from user (priority order, one at a time)
  Scope is now complete

STEP 3 — CONSTANTS
  Add all node.constants to scope by symbol
  Constants are always in scope — they cannot be overridden by inputs

STEP 4 — FORMULA EXECUTION
  For each step in node.formula.steps (in order):
    Evaluate step.expression using current scope
    Expression may only use: + - * / ** ( ) and symbols in scope
    Assign result to step.assign → add to scope immediately
    (each step result is available to all subsequent steps)
  All steps complete → results are in scope by symbol name

STEP 5 — CHECKS
  For each check in node.checks (in order):
    Evaluate check.condition against scope
    If condition is true:
      Emit check.message and check.action as a warning event
      If check.severity is "blocking":
        Halt formula output
        If check.goto is set → load that node → restart executor
        If check.goto is null → halt, return error state
        Stop evaluating further checks (unless check.always_run is true)
      If check.severity is "advisory":
        Continue to next check
  All checks evaluated → continue

STEP 6 — OUTPUT COLLECTION
  For each output in node.outputs:
    Read the value assigned in the step named by output.from_step
    Store in task state under output.symbol
    These values are now available to downstream nodes via source: node:<this-id>

STEP 7 — REPORT ATTACHMENT
  Attach node.report metadata to the stored result
  Report assembler reads this later to build the grouped output
  Execution complete
```

### 2.2 Expression Evaluator Rules

The expression evaluator is sandboxed. It must enforce these rules:

```
ALLOWED:
  Arithmetic operators:  + - * / ** ( )
  Symbols from scope:    any key present in the execution scope
  Numeric literals:      integers and decimals
  Function calls:        sin(), sqrt(), log() 

NOT ALLOWED:
  
  String literals:       any quoted value
  Comparisons:           == != < > — these belong in conditions and checks, not formula steps
  Assignment:            = — steps use the assign field, not inline assignment
  Any code construct:    loops, conditionals, imports
```

If any expression contains a disallowed construct, the executor must reject
the node at load time (not at runtime) and emit a node validation error.

### 2.3 Node Type Dispatch

The executor dispatches to a sub-handler based on node.type:

```
node.type = "calculation"   → run full 7-step sequence above
node.type = "lookup-table"  → skip formula steps, run table match, return value
node.type = "decision-gate" → evaluate conditions only, follow goto, no outputs
node.type = "informational" → no execution, return content for LLM context only
```

### 2.4 What the Executor Does NOT Do

```
Does not choose which node to run     → dependency resolver decides order
Does not collect inputs from user     → input collector handles user interaction
Does not store events                 → task state manager handles event creation
Does not build the report             → report assembler reads outputs after all nodes complete
Does not know about ASME              → nodes carry all domain knowledge
```

---

## 3. Node Fields — Quick Reference

Before reading the full template, this table maps every frontmatter field to its consumer.

| Field | Read By | Purpose |
|---|---|---|
| `id` | All | Canonical key — used in depends_on, required_by, source: node: |
| `title` | Report assembler, UI | Human-readable name |
| `type` | Executor dispatcher | Determines which execution path to follow |
| `edition` | Dependency resolver | Version pinning — nodes from different editions must not mix |
| `parent` | Index builder | Navigation hierarchy |
| `children` | Index builder | Navigation hierarchy |
| `cross_refs` | LLM context builder | Surfaces related paragraphs to the user |
| `conditions` | Executor step 1 | Applicability gates before any input is collected |
| `inputs` | Executor step 2, input collector | What is needed and where it comes from |
| `constants` | Executor step 3 | Fixed values owned by the node |
| `formula.steps` | Executor step 4 | Ordered arithmetic expressions — the calculation |
| `checks` | Executor step 5 | Post-execution validations and re-routing |
| `outputs` | Executor step 6, downstream nodes | Named results stored in task state |
| `depends_on` | Dependency resolver | Builds execution DAG and topological sort |
| `required_by` | Traceability, reverse lookup | Which nodes consume this node's outputs |
| `report` | Report assembler | Controls appearance in grouped output |

---

## 4. Full Node File Template

Every node file is named `node.md` and lives in its own folder under `asme-b313/nodes/`.

```markdown
---
# ─────────────────────────────────────────────
# IDENTITY
# ─────────────────────────────────────────────
id: B313-304.1.1
title: "Straight Pipe Under Internal Pressure"
code_reference: "ASME B31.3 — 2022 Edition, Paragraph 304.1.1"
edition: "2022"
type: calculation   # calculation | lookup-table | decision-gate | informational

# ─────────────────────────────────────────────
# HIERARCHY
# ─────────────────────────────────────────────
parent: B313-304.1
children: []
cross_refs:
  - id: B313-302.3.1
    reason: "Design pressure definition"
  - id: B313-A-1
    reason: "Allowable stress values for material and temperature"
  - id: B313-302.3.4
    reason: "Quality factor E values by weld type"
  - id: B313-302.3.5e
    reason: "Weld joint strength reduction factor W at high temperature"
  - id: B313-302.4
    reason: "Corrosion allowance to be added to t"
  - id: B313-304.1.1a
    reason: "Thick-wall formula — required if t >= D/6"

# ─────────────────────────────────────────────
# APPLICABILITY CONDITIONS
# ─────────────────────────────────────────────
# Checked BEFORE inputs are collected or formula runs.
# All conditions must be true for this node to execute.
# If any condition is false, else_goto is followed instead.
conditions:
  - id: geometry_check
    test: "geometry == 'straight_pipe'"
    else_goto: B313-304.2
    message: "Pipe is not straight. Routing to fittings and components."

  - id: pressure_type_check
    test: "pressure_type == 'internal'"
    else_goto: B313-304.1.2
    message: "Loading is external pressure. Routing to 304.1.2."

# Note: the thin-wall ratio check (t < D/6) cannot be evaluated before the
# formula runs. It is declared as a post-execution blocking check instead.

# ─────────────────────────────────────────────
# INPUTS
# ─────────────────────────────────────────────
# source: user          collected from the user directly
# source: node:<id>     output of another node, injected automatically by executor
# source: default       safe default exists, must be confirmed by user before use
#
# priority determines the order in which missing inputs are requested.
# Ask one at a time, in priority order.
inputs:
  - symbol: P
    name: Internal Design Pressure
    unit: psi
    source: user
    priority: 1
    description: "Maximum sustained operating pressure plus surge allowance. See 302.2.2."

  - symbol: D
    name: Outside Diameter
    unit: inches
    source: user
    priority: 2
    description: "Nominal outside diameter of the pipe as listed in the applicable standard."

  - symbol: S
    name: Allowable Stress
    unit: psi
    source: node:B313-A-1
    priority: 3
    description: "Basic allowable stress for the pipe material at design temperature. From Appendix A."

  - symbol: E
    name: Longitudinal Quality Factor
    unit: dimensionless
    source: default
    default_value: 1.0
    default_condition: "Seamless pipe (no longitudinal weld)"
    default_confirm_prompt: "I will use E = 1.0 (seamless pipe). Is that correct, or does your pipe have a longitudinal weld?"
    priority: 4
    description: "Weld quality factor based on pipe manufacturing type. From Table 302.3.4."

  - symbol: W
    name: Weld Joint Strength Reduction Factor
    unit: dimensionless
    source: default
    default_value: 1.0
    default_condition: "T_design < 950°F (510°C)"
    default_confirm_prompt: "I will use W = 1.0 (design temperature below 950°F). Is that correct?"
    priority: 5
    description: "Reduction factor for longitudinal welds at elevated temperature. See 302.3.5(e)."

  - symbol: Y
    name: Temperature Coefficient
    unit: dimensionless
    source: node:B313-TABLE-304.1.1
    priority: 6
    description: "Coefficient that accounts for material behavior at temperature. From Table 304.1.1."

  - symbol: c
    name: Corrosion and Erosion Allowance
    unit: inches
    source: user
    priority: 7
    description: "Additional thickness for corrosion, erosion, or mechanical allowance. See 302.4."

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
# Fixed values this node owns.
# No external lookup needed. Referenced by symbol in formula.steps.
constants:
  - symbol: mill_undertolerance
    value: 0.125
    description: "Standard ASTM mill undertolerance — 12.5%. Verify against mill certificate if available."
    source_note: "ASTM product standards (A53, A106, A333, etc.)"

# ─────────────────────────────────────────────
# FORMULA
# ─────────────────────────────────────────────
# Ordered list of expression steps.
# The generic executor evaluates these in sequence.
# Each step assigns a named variable that is available to all subsequent steps.
# Inputs, constants, and prior step results are all in scope by symbol name.
#
# expression syntax: standard arithmetic — +  -  *  /  **  ( )
# No functions, no code — pure arithmetic expressions only.
# The executor uses a sandboxed math evaluator (AST-based, not eval()).
formula:
  steps:
    - id: step_1
      expression: "S * E * W"
      assign: SEW
      description: "Combined allowable stress factor"
      unit: psi

    - id: step_2
      expression: "P * Y"
      assign: PY
      description: "Pressure-temperature correction term"
      unit: psi

    - id: step_3
      expression: "(P * D) / (2 * (SEW + PY))"
      assign: t_min
      description: "Minimum required pressure thickness — Barlow thin-wall formula"
      unit: inches

    - id: step_4
      expression: "t_min + c"
      assign: T_min
      description: "Total minimum required thickness including corrosion allowance"
      unit: inches

    - id: step_5
      expression: "T_min / (1 - mill_undertolerance)"
      assign: T_ordered
      description: "Minimum ordered wall thickness adjusted for mill undertolerance"
      unit: inches

# ─────────────────────────────────────────────
# CHECKS
# ─────────────────────────────────────────────
# Post-execution validations evaluated after formula.steps complete.
# severity: blocking  — halt execution, emit warning, follow goto if set
# severity: advisory  — emit warning, continue execution
#
# Checks are evaluated in order. Blocking checks stop further checks.
checks:
  - id: thin_wall_validity
    condition: "t_min >= D / 6"
    severity: blocking
    message: "Calculated t_min is >= D/6. The thin-wall (Barlow) formula is not valid for this geometry."
    action: "Use the thick-wall (Lamé) formula per paragraph 304.1.1(a)."
    goto: B313-304.1.1a

  - id: positive_result
    condition: "t_min <= 0"
    severity: blocking
    message: "Calculated t_min is zero or negative. Check input values."
    action: "Verify P, D, S, E, W, and Y are all positive and correctly unitised."
    goto: null

  - id: mill_tolerance_advisory
    condition: "mill_undertolerance == 0.125"
    severity: advisory
    always_run: true    # runs even when a prior blocking check fires, so the warning is never silently skipped
    message: "Standard ASTM mill undertolerance of 12.5% has been applied."
    action: "Verify undertolerance against the actual pipe mill certificate if available."
    goto: null

# ─────────────────────────────────────────────
# OUTPUTS
# ─────────────────────────────────────────────
# Named results stored in task state after successful execution.
# downstream nodes reference these by symbol via source: node:B313-304.1.1
outputs:
  - symbol: t_min
    name: Minimum Required Pressure Thickness
    unit: inches
    from_step: step_3
    description: "Pressure design thickness before allowances. Do not use directly for pipe selection."

  - symbol: T_min
    name: Minimum Required Total Thickness
    unit: inches
    from_step: step_4
    description: "t_min plus corrosion allowance. Minimum thickness the pipe must have in service."

  - symbol: T_ordered
    name: Minimum Ordered Wall Thickness
    unit: inches
    from_step: step_5
    description: "Minimum wall thickness to specify when purchasing pipe. Select the next heavier schedule."

# ─────────────────────────────────────────────
# DEPENDENCIES
# ─────────────────────────────────────────────
# Nodes that must complete before this node can run.
# The dependency resolver uses this list to build the execution DAG
# and determine topological sort order.
depends_on:
  - node_id: B313-A-1
    provides: S
    reason: "Allowable stress S must be resolved before the formula runs"

  - node_id: B313-TABLE-304.1.1
    provides: Y
    reason: "Y coefficient is resolved from material category and T_design"

# Nodes that consume outputs of this node.
# Populated here for traceability and reverse-lookup.
# The resolver also builds this automatically from all nodes' depends_on lists.
required_by:
  - node_id: B313-345.4
    consumes: T_ordered
    reason: "Hydrostatic test pressure is based on the ordered wall thickness"

# ─────────────────────────────────────────────
# REPORT METADATA
# ─────────────────────────────────────────────
# Controls how this node's result appears in the grouped integrity report.
report:
  section_title: "Wall Thickness Verification"
  paragraph_reference: "ASME B31.3 §304.1.1"
  show_inputs: true
  show_formula_steps: true
  show_outputs: true
  show_checks: true
  show_decision_path: true
  pass_condition: "T_ordered <= T_actual"
  pass_label: "Selected pipe schedule satisfies minimum ordered thickness"
  fail_label: "Selected pipe schedule does not satisfy minimum ordered thickness"
---

# 304.1.1 Straight Pipe Under Internal Pressure

## Scope

This paragraph establishes the minimum required wall thickness for straight pipe
subjected to internal pressure in process piping systems governed by ASME B31.3.

---

## Applicability

This paragraph applies when all of the following are true:

- The pipe is straight (no bends, elbows, or curvature)
- The loading is internal pressure
- The calculated thickness t satisfies t < D/6

If t ≥ D/6, the pipe is classified as thick-wall and the Lamé equation in
paragraph 304.1.1(a) must be used instead.

---

## Formula

The minimum required thickness t is:

```
        P × D
t = ─────────────────
     2 (S × E × W + P × Y)
```

Where:

| Symbol | Description | Source |
|---|---|---|
| P | Internal design pressure (psi) | User input — see 302.2.2 |
| D | Outside diameter of pipe (inches) | User input — pipe standard |
| S | Allowable stress at design temperature (psi) | Appendix A |
| E | Longitudinal quality factor (dimensionless) | Table 302.3.4 |
| W | Weld joint strength reduction factor (dimensionless) | 302.3.5(e) |
| Y | Temperature coefficient (dimensionless) | Table 304.1.1 |

The formula may also be rearranged to solve for the allowable pressure P:

```
       2t (S × E × W + P × Y)
P = ─────────────────────────────
              D - 2tY
```

---

## Table 304.1.1 — Values of Y

| Material | ≤ 900°F (482°C) | 950°F (510°C) | 1000°F (538°C) | 1050°F (566°C) | 1100°F (593°C) | ≥ 1150°F (621°C) |
|---|---|---|---|---|---|---|
| Ferritic steels | 0.4 | 0.5 | 0.7 | 0.7 | 0.7 | 0.7 |
| Austenitic steels | 0.4 | 0.4 | 0.4 | 0.4 | 0.5 | 0.7 |
| Other ductile metals | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 |
| Cast iron | 0.0 | — | — | — | — | — |

For design temperatures between listed values, linear interpolation is permitted.

---

## Required Thickness After Allowances

The calculated t is the pressure design thickness only. The total minimum
required thickness T_min must include the corrosion and erosion allowance c:

```
T_min = t + c
```

---

## Mill Undertolerance

Purchased pipe is subject to wall thickness undertolerance permitted by its
product standard. The ordered wall thickness T_ordered must be sufficient so
that even at the minimum manufacturing tolerance, T_min is satisfied:

```
              T_min
T_ordered = ─────────────────────────
             1 − undertolerance (decimal)
```

For ASTM pipe products, the standard mill undertolerance is 12.5% (0.125).

Example:

```
T_min    = 0.200 inches
T_ordered = 0.200 / (1 − 0.125) = 0.200 / 0.875 = 0.229 inches
```

Select the next heavier standard wall schedule with T_actual ≥ 0.229 inches.

---

## Decision Branch After Solving

```
Solve for t_min using formula.steps
│
├── t_min < D/6 ?
│     YES → Formula valid. Proceed to T_min and T_ordered.
│     NO  → STOP. blocking check thin_wall_validity fires.
│             Executor routes to B313-304.1.1a (thick-wall formula).
│
└── T_ordered computed?
├── Select pipe schedule where T_actual >= T_ordered
├── Confirm corrosion allowance c was included (step_4)
└── Verify P-T rating of listed components per 302.2.1

---

## Mandatory Next Steps After This Paragraph

The following must also be satisfied before the piping system is complete:

1. **302.4** — Verify corrosion and erosion allowance c is appropriate for the fluid service
2. **302.2.1** — If using listed components (flanges, fittings), verify their P-T rating is not exceeded
3. **305.2 / 319.4** — Perform flexibility analysis; wall thickness affects stress intensification factors
4. **345** — Establish hydrostatic test pressure based on T_ordered produced by this node

---

## Cross-References

| Paragraph | Topic | Relationship |
|---|---|---|
| 302.2.2 | Design pressure definition | Defines P used in this formula |
| 302.3.1 | Allowable stress basis | Governs how S is selected |
| 302.3.4 / Table 302.3.4 | Quality factor E | Source of E value |
| 302.3.5(e) | Weld joint strength reduction W | Required for T ≥ 950°F |
| 302.4 | Corrosion allowance | c must be added to t (step_4) |
| 304.1.1(a) | Thick-wall formula | Required when t_min ≥ D/6 — triggered by check |
| 304.1.2 | External pressure | Different formula, different path |
| Appendix A | Allowable stress tables | Source of S — resolved by node B313-A-1 |
| Table 302.3.4 | Quality factor table | Source of E value |
| Table 304.1.1 | Y coefficient table | Resolved by node B313-TABLE-304.1.1 |
| 345 | Pressure testing | Consumes T_ordered output of this node |