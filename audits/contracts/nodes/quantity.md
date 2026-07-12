# Quantity Node Contract

## 1. Purpose

A quantity node represents a physical engineering quantity (pressure, temperature, thickness) as immutable semantic knowledge — legacy and embed use; modern authoring prefers `parameter` with `parameter_class: physical_quantity`.

## 2. Use this node when

- You are maintaining legacy embedded `outputs` entries with `type: quantity` inside equation metadata.
- Documentation requires a quantity symbol table separate from parameter binding.
- A section node embeds outputs under the `outputs:` container.

## 3. Do not use this node when

- You need a gatherable workflow field (use `parameter`).
- You need a named classification like NPS or schedule (use `designation`).
- You are starting new global ontology work (prefer `PARAM-*` + `CONCEPT-*`).

## 4. File location

| Form | Path |
| --- | --- |
| Legacy standalone | `knowledge/**/nodes/**/B313-quantity-*.yaml` (template) |
| Embedded | Equation or section `outputs:` / `nomenclature` containers |

## 5. ID convention

| Field | Rule |
| --- | --- |
| `id` | Descriptive slug (template: `B313-quantity-{name}`) |
| `dimension` | Dimension key string (`pressure`, `length`) — not necessarily `DIM-*` in legacy embeds |
| `name` | Human-readable quantity name |

## 6. Copyable minimal YAML skeleton

Standalone:

```yaml
---
id: B313-quantity-pressure
type: quantity
name: Pressure
dimension: pressure
description: >
  Internal or external gage pressure used in pressure design equations.
metadata:
  last_revision: 2026-07-04
  edited_by: admin
---
```

Embedded in equation `outputs:`:

```yaml
outputs:
  - symbol: t
    name: required_thickness
    unit: mm
    type: quantity
```

## 7. Required fields

| Field | Rule |
| --- | --- |
| `id` | Unique identity |
| `type` | `quantity` |
| `name` | Human-readable name |
| `dimension` | Physical dimension key |
| `metadata.last_revision`, `metadata.edited_by` | When standalone file |

## 8. Optional fields

| Field | Purpose |
| --- | --- |
| `description` | Engineering definition |
| `documentation` | Longer narrative (markdown body) |
| `symbol` | When embedded in outputs |
| `unit` | Display unit hint when embedded (not runtime) |

## 9. Forbidden fields

```text
value, user_input, runtime_value, fact_value, runtime_unit,
runtime_units, resolution, execution_id
```

Also forbidden:

- Task binding fields (`input_id`, `question`) — belong on `parameter`
- Top-level `links` block

## 10. Permitted outgoing relationships

Quantity nodes rarely author `edges` directly. Parameters link to quantities via legacy `references` patterns in older templates; prefer `has_parameter` on concepts and `requires` on equations pointing at `PARAM-*`.

## 11. Fields consumed by runtime components

Embedded quantity entries in equation `outputs` inform display metadata for result symbols. Legacy references may resolve through graph compile embedded node expansion. Execution binds engineering values through `PARAM-*` Facts, not quantity nodes directly.

## 12. Validation procedure

No dedicated validator. Validate manually:

1. Confirm `type: quantity` and required name/dimension.
2. Confirm no forbidden runtime fields.
3. Confirm equations `require` `PARAM-*` nodes, not quantity nodes, for execution.
4. Rebuild graph when changing embedded outputs.

## 13. Common authoring mistakes

- Creating quantity nodes instead of `PARAM-*` for new gatherable fields.
- Storing `value` or `user_input` on quantity nodes.
- Pointing equation `requires` at quantity nodes instead of parameters.
- Mixing `dimension: pressure` string with `DIM-pressure` id inconsistently.
- Omitting revision metadata on standalone files.

## 14. Current repository examples

Embedded in equations:

- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3a.yaml` (`outputs` with `type: quantity`)
- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3b.yaml`
- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-pressure-design-thickness.yaml`

Template standalone:

- Embedded outputs pattern in equation nodes

## 15. Implementation evidence appendix

- Embedded defaults: `engine/reference/embedded_nodes.py` — `_DEFAULT_TYPES` maps `outputs` → `quantity`
- Validator: none dedicated
- Parameter relationship: [`parameter.md`](parameter.md)
