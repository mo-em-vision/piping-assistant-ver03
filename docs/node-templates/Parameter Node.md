# Parameter Node Template

A Parameter node defines a reusable engineering concept. It does **not** store values, user inputs, runtime state, or execution resolution strategy.

Do **not** author a top-level `links` metadata block — object relationships belong in typed `edges` only ([`_relationship_schema.md`](_relationship_schema.md#on-disk-rule)). **Exception:** declare where a parameter is introduced in the top-level `introduced_by` list (not in `edges`); the graph compiler emits `introduced_by` edges at build time.

```yaml
---
id: PARAM-design-pressure
type: parameter

key: design_pressure
name: Design Pressure

parameter_class: physical_quantity
dimension: DIM-pressure

description: >
  Pressure used as the basis for engineering design calculations.

canonical_symbol: P

aliases:
  - design pressure
  - internal design pressure

introduced_by:
  - asme-b313-304-1-1-b

edges:
  - type: has_dimension
    target: DIM-pressure

  - type: used_by
    target: asme-b313-304-1-2-eq-3a

metadata:
  status: active
  version: 1
---
```

## Required fields

|Field|Purpose|
|---|---|
|`id`|Stable canonical parameter identity. Prefer `PARAM-*`, not standard-owned IDs.|
|`type`|Must be `parameter`.|
|`key`|Machine-safe semantic key.|
|`name`|Human-readable canonical name.|
|`parameter_class`|Kind of parameter.|
|`dimension`|Reference to a `DIM-*` node.|
|`description`|Stable semantic definition.|
|`introduced_by`|Pack-qualified paragraph id(s) where the symbol is introduced (top-level list only; not `edges`).|

## Recommended `parameter_class` values

```yaml
physical_quantity
geometric_quantity
material_designation
coefficient
factor
categorical
environmental_condition
calculated_quantity
selection
```

### `selection` and `categorical` control runtime behavior

These `parameter_class` values drive planner prompts, UI input type, and lookup gating. They do **not** belong on Concept nodes — Concepts only group semantic meaning. See [Engineering Concept](Engineering%20Concept.md#selection-vs-categorical-where-each-belongs).

- **`selection`**: discrete workflow choice (dropdown/confirmation); e.g. joint category before E lookup.
- **`categorical`**: label-based designation stored as a Fact `{label, normalized_key}`; e.g. material specification token.

## Composer metadata (workflow UI)

Gatherable parameters must declare how the desktop composer renders them. Author under the `metadata` block:

| Field | Purpose |
| --- | --- |
| `composer_input` | UI control: `number`, `dropdown`, `checkbox`, `material` |
| `composer_options` | Static choices: `[{value: internal_pressure, label: Internal Pressure}]` |
| `canonical_unit` | Default unit symbol or `UNIT-*` id (`UNIT-mm`, `NPS`) |
| `default_value` | Proposed default before user confirms |

## Prompt metadata (messaging)

Author user-facing prompt copy on PARAM nodes. Messaging reads these fields via `engine/messaging/parameter_prompt_context.py` (see [`docs/rules.md`](../rules.md) §12).

| Field | Purpose |
| --- | --- |
| `question` | Primary user-facing ask (priority over `description` for prompts) |
| `metadata.short_question` | One-line composer ask; if absent, derived from `name` and `canonical_symbol` |
| `metadata.input_examples` | Example values shown in prompts, e.g. `["500 psi", "8 bar"]` |
| `metadata.prompt_use_description` | Set `false` to skip thin `description` as prompt fallback |

`description` remains the stable engineering definition; `question` holds prompt-oriented copy.

`engine/reference/parameter_composer_spec.py` reads composer fields only — no engine fallbacks. Omit `composer_input` to infer from `parameter_class` + `dimension`. Dynamic option lists (NPS catalog, material tables) are loaded in `api/parameter_definitions.py` after the PARAM node sets type and default unit.

Full rule: [`docs/rules.md`](../rules.md) §17, [`.cursor/rules/param-composer-metadata.mdc`](../../.cursor/rules/param-composer-metadata.mdc).

Example:

```yaml
metadata:
  status: active
  version: 1
  last_revision: 2026-07-06
  edited_by: admin
  composer_input: dropdown
  composer_options:
    - value: internal_pressure
      label: Internal Pressure
    - value: external_pressure
      label: External Pressure
```

## Lookup conditionals (table-derived outputs)

When a parameter is resolved from a table lookup and needs boundary behavior outside the tabulated range, author `lookup_conditionals` on the **output** `PARAM-*` node. Keys must match lookup input / fact keys (`design_temperature`, …).

```yaml
lookup_conditionals:
  design_temperature:
    unit: UNIT-degF
    min: 900
    max: 1250
    below_min: use_min
    above_max: use_max
```

| Field | Purpose |
| --- | --- |
| `unit` | Unit for thresholds (`UNIT-degF`, `UNIT-degC`, …) |
| `min` / `max` | Tabulated range endpoints |
| `below_min: use_min` | Use the value at `min` when input is lower |
| `above_max: use_max` | Use the value at `max` when input is higher |

The lookup node keeps tabulated rows and `interpolation: true` only. The engine applies conditionals generically via `engine/graph/lookup_conditionals.py`.

Full rule: [`docs/rules.md`](../rules.md) §18, [`.cursor/rules/lookup-conditionals.mdc`](../../.cursor/rules/lookup-conditionals.mdc).

## Dimension examples

```yaml
dimension: DIM-pressure
dimension: DIM-length
dimension: DIM-temperature
dimension: DIM-dimensionless
dimension: DIM-material-designation
```

## Important rules

Parameter nodes must not contain:

```yaml
value:
unit:
resolution:
source:
timestamp:
execution_id:
workflow_id:
status:
```

Those belong to **Facts**, **Execution Context**, or **Workflow/Planner logic**.

## Cross-pack paragraph traceability

Global `PARAM-*` nodes live outside any standards pack. When a parameter is introduced or used by a **paragraph**, reference the paragraph with a **pack-qualified id** so multiple standards do not collide:

| Pack | Prefix | Bare paragraph `id` | Qualified reference |
| --- | --- | --- | --- |
| ASME B31.3 | `asme-b313` | `304.1.1-b` | `asme-b313-304-1-1-b` |
| ASME B31.3 | `asme-b313` | `302.3.5-e` | `asme-b313-302-3-5-e` |

Use pack-qualified ids in the top-level `introduced_by` list only — do **not** duplicate them as `introduced_by` edges. Paragraph nodes inside a pack keep their bare `id` (`304.1.1-b`); the graph compiler resolves qualified references at compile time. Helpers: [`engine/reference/asme_b313_node_ids.py`](../../engine/reference/asme_b313_node_ids.py).

## Parameter key consistency (lookup tables and databases)

**Runtime parameter keys, lookup-table input ids, and fact keys must match the global `PARAM-*` node `key` field.**

| Layer | Rule | Example |
| --- | --- | --- |
| Parameter node | Author `key` on `knowledge/global/parameters/nodes/PARAM-*.yaml` | `material_grade` on `PARAM-material-grade` |
| Lookup table node | Each `inputs[].id` equals the bound parameter `key` | `asme-b313-table-A-1` input `material_grade` → `PARAM-material-grade` |
| Workflow runtime | Phase field lists use parameter `key`, not abbreviations | `material_grade`, not `material` |
| Facts / API | Store and submit under the canonical `key` | Fact key `material_grade` |
| Material catalog | `material_id` values are catalog ids (e.g. `astm_a106_gr_b`), not parameter keys | Distinct from parameter `key` |

Implementation helper: `engine/reference/parameter_keys.py` (`MATERIAL_GRADE_KEY`, `canonical_parameter_key`, `read_parameter_value`). Legacy aliases (e.g. `material` → `material_grade`) are read-only for old sessions; do not author new YAML or nodes with legacy keys.

When adding a new parameter that drives a lookup table, use the same string for: `PARAM-*` `key`, lookup `inputs[].id`, workflow phase lists, and fact storage. Future material-related parameters (e.g. `metallurgical_group`) follow the same rule with their own unique keys.

Full template: [`docs/node-templates/Parameter Node.md`](node-templates/Parameter%20Node.md#parameter-key-consistency).

---


```yaml
---
id: PARAM-corrosion-allowance
type: parameter

key: corrosion_allowance
name: Corrosion Allowance

parameter_class: geometric_quantity
dimension: DIM-length

description: >
  Additional wall thickness allowance provided to account for expected
  corrosion, erosion, or mechanical allowance over the service life.

canonical_symbol: c

aliases:
  - corrosion allowance
  - mechanical allowance
  - allowance

introduced_by:
  - asme-b313-304-1-1-b

edges:
  - type: has_dimension
    target: DIM-length

  - type: used_by
    target: asme-b313-304-1-1-eq-2

metadata:
  status: active
  version: 1
---
```

## Example: joint category parameter

```yaml
---
id: PARAM-joint-category
type: parameter

key: joint_category
name: Joint Category

parameter_class: selection

description: >
  Pipe or joint construction category used to resolve weld joint quality
  factor E from Tables A-2 and A-3.

canonical_symbol: joint_category

aliases:
  - weld category
  - joint type
  - weld joint category

introduced_by:
  - asme-b313-304-1-2-a

edges:
  - type: used_by
    target: asme-b313-table-A-3

metadata:
  status: active
  version: 1
---
```

Semantic grouping lives on [`CONCEPT-joint-category`](../../knowledge/global/concepts/nodes/CONCEPT-joint-category.yaml); this Parameter owns the contextual role and selection behavior.

## Conceptual rule

```text
Concept defines semantic meaning.
Parameter defines contextual role and behavior class.
Dimension defines compatible units.
Unit defines conversion.
Fact stores actual value.
Workflow/Planner decides how the Fact is obtained.
```