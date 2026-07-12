# Equation Execution Sidecar Contract

## 1. Purpose

The equation execution sidecar holds execution metadata for an equation node — variables, steps, executor hooks, display overrides — when authors prefer to split execution detail from citation frontmatter.

## 2. Use this sidecar when

- Execution fields would make the main equation YAML too large.
- You are migrating legacy sidecar-only execution layouts.
- You need `variables`, `steps`, `executor`, or `display` separate from standards citation fields.

## 3. Do not use this sidecar when

- All execution fields fit cleanly in the flat `asme-b313-*.yaml` file (preferred for B31.3 pack).
- You need governing paragraph authorization (belongs in frontmatter `authority` block).
- Content is paragraph-scoped branching (paragraph execution sidecar).

## 4. File location

| Layout | Path |
| --- | --- |
| Flat file | `knowledge/standards/<pack>/nodes/equation/{id}.execution.yaml` |
| Directory | `knowledge/standards/<pack>/nodes/equation/{id}/execution.yaml` |

## 5. ID convention

Inherits parent equation `id`. Sidecar keys use the equation execution key set (section 7). `equation_id` inside sidecar is an optional runtime alias, not the graph node id.

## 6. Copyable minimal YAML skeleton

```yaml
variables:
  P:
    parameter: PARAM-internal-design-gage-pressure
    unit: UNIT-psi
  t:
    parameter: PARAM-required-wall-thickness
    unit: UNIT-mm
steps:
  - id: compute_t
    expression: t = P * D / (2 * (S * E * W + P * Y))
display:
  text: t = PD / 2(SEW + PY)
nomenclature_ref: 304.1.1-b
```

## 7. Required fields

No keys are strictly required in an empty sidecar. Valid keys:

```text
variables, steps, executor, execution_function, calculation_module,
outputs, equation_id, nomenclature_ref, display, applies_when, paragraph
```

When the sidecar exists, at least one key should be non-empty. Parent frontmatter must still satisfy `validate_equation_node` (requires/calculates, authority, metadata.status).

## 8. Optional fields

| Key | Purpose |
| --- | --- |
| `variables` | Symbol → parameter/unit map |
| `steps` | Ordered execution steps |
| `executor` | Named executor function |
| `execution_function` | Module path to callable |
| `calculation_module` | Python module for calculation |
| `outputs` | Result descriptors (`symbol`, `unit`, `type`) |
| `equation_id` | Legacy runtime alias |
| `nomenclature_ref` | Paragraph id for symbol table |
| `display` | `text`, `latex` overrides |
| `applies_when` | Applicability conditions |
| `paragraph` | Citing paragraph number |

Frontmatter may also inline these keys; sidecar values merge over empty frontmatter fields.

## 9. Forbidden fields

```text
id, type, authority, requires, calculates, edges, links
```

Do not move `authority.authorized_by` or `requires`/`calculates` exclusively to sidecar without frontmatter copies — validator reads frontmatter first.

## 10. Permitted outgoing relationships

Sidecars do not use `edges`. Reference nodes by id in `variables`, `nomenclature_ref`, and `paragraph` fields.

## 11. Fields consumed by runtime components

Equation sidecar merge runs before execution adapters build the calculation context. Execution kernel reads `steps`, `executor`, and `variables` for evaluation. Presentation reads merged `display` for equation blocks. Graph expansion may read merged `applies_when`.

## 12. Validation procedure

1. Confirm parent equation frontmatter passes `validate_equation_node`.
2. Confirm sidecar uses only keys from section 7.
3. Confirm `nomenclature_ref` points to an existing nomenclature paragraph.
4. Rebuild graph DB after edits.
5. Run equation execution tests in `tests/` targeting B31.3 equations.

## 13. Common authoring mistakes

- Putting `authority` only in sidecar (validator requires frontmatter `authority` block).
- Omitting `requires`/`calculates` from frontmatter when relying on sidecar `variables` alone.
- Divergent `display` in sidecar vs frontmatter without intentional override.
- Using legacy `B313-eq-*` ids as file ids instead of `asme-b313-*`.
- Empty execution sidecar file committed alongside complete inline frontmatter.

## 14. Current repository examples

Inline execution in frontmatter (preferred pattern):

- `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3a.yaml`

## 15. Implementation evidence appendix

- Loader keys: `engine/reference/equation_sidecar.py` — `_EXECUTION_KEYS`, `merge_equation_sidecar_metadata`, `equation_sidecar_dir`
- Also merges `equation_number`, `paragraph_number` from frontmatter file
- Validator: `engine/validation/equation_node_validator.py`
