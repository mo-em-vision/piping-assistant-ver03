# Paragraph Execution Sidecar Contract

## 1. Purpose

The paragraph execution sidecar holds runtime-adjacent metadata for a paragraph node — branch interactions, applicability gates, assumptions, and execution hooks — without bloating the paragraph frontmatter.

## 2. Use this sidecar when

- A paragraph participates in graph expansion (`applicability`, `interactions`, `assumptions`).
- You need `depends_on`, `equations`, `validation_rules`, or `conditions` scoped to one paragraph.
- Provisional defaults or parameter defaults apply before user confirmation.

## 3. Do not use this sidecar when

- You only need official standard text (paragraph frontmatter `text.original` suffices).
- You are defining symbols introduced in nomenclature (use nomenclature sidecar or `introduces_parameter` edges).
- Content belongs on a workflow (`runtime.yaml`) or equation file.

## 4. File location

| Layout | Path |
| --- | --- |
| Flat file | `knowledge/standards/<pack>/nodes/paragraph/{id}.execution.yaml` |
| Directory | `knowledge/standards/<pack>/nodes/paragraph/{id}/execution.yaml` |

Loaded beside `{id}.yaml` paragraph frontmatter.

## 5. ID convention

No separate node `id`. The sidecar inherits identity from the parent paragraph `{id}.yaml`. Keys inside the sidecar use field names from the execution key set (section 7).

## 6. Copyable minimal YAML skeleton

```yaml
interactions:
  - variable: pressure_loading
    mode: decision
    required: true
    options:
      - internal_pressure
      - external_pressure
applicability:
  applies_when:
    - parameter: PARAM-straight-pipe-section
      operator: equals
      value: true
```

## 7. Required fields

No fields are strictly required in an empty sidecar. When present, keys must conform to the loader key set:

```text
interactions, assumptions, applicability, provisional_assumptions,
parameter_defaults, inputs, depends_on, equations, validation_rules,
conditions, kind, outputs, lookups, notes
```

At least one key should be non-empty when the sidecar file exists.

## 8. Optional fields

All keys in section 7 are optional individually. Common combinations:

| Key | Purpose |
| --- | --- |
| `interactions` | Pre-expansion decision gates |
| `applicability.applies_when` | Branch inclusion conditions |
| `assumptions` | Confirmed assumptions list |
| `provisional_assumptions` | Defaults until confirmed |
| `parameter_defaults` | Suggested values with confirmation flags |
| `conditions` | Post-calculation checks routing |
| `depends_on` | Edge-like dependencies with `when` |
| `equations` | Inline equation references |
| `validation_rules` | Inline rule references |
| `lookups` | Inline lookup references |
| `outputs` | Expected output descriptors |
| `notes` | Authoring notes (non-executable) |

## 9. Forbidden fields

```text
id, type, paragraph_number, text, authority, edition, hierarchy, edges, links
```

Do not duplicate paragraph frontmatter identity or prose in the execution sidecar.

## 10. Permitted outgoing relationships

Sidecars do not use `edges`. Reference other nodes by id inside structured blocks (`depends_on[].target`, `equations[]`, `validation_rules[]`, parameter ids in `applicability`).

## 11. Fields consumed by runtime components

Graph expansion merges execution keys into paragraph metadata before evaluating branch gates. Expansion policy reads `applicability` and `interactions` to prune paths. Planner consumes gate outcomes from expanded graph state. Parameter defaults may seed provisional Facts pending user confirmation.

## 12. Validation procedure

1. Confirm file naming matches parent paragraph id.
2. Confirm only execution keys from section 7 are used.
3. Confirm referenced `PARAM-*` and equation ids exist in the pack graph.
4. Rebuild graph: `python scripts/build_graph_db.py`.
5. Run `python -m pytest tests/graph/test_expansion_policy.py`.

## 13. Common authoring mistakes

- Putting `applicability` in paragraph frontmatter (validator forbids it there).
- Creating an execution sidecar with only empty keys.
- Using slash paragraph notation in conditions instead of hyphen ids.
- Duplicating workflow-level `navigation` in paragraph execution.
- Mixing nomenclature symbol tables into execution sidecar.

## 14. Current repository examples

- `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.execution.yaml`

## 15. Implementation evidence appendix

- Loader keys: `engine/reference/paragraph_sidecar.py` — `_EXECUTION_KEYS`, `merge_paragraph_sidecar_metadata`, `paragraph_sidecar_dir`
- Applicability parse: `engine/reference/paragraph_sidecar.py` — `parse_applicability_as_interactions`
- Frontmatter forbidden overlap: `engine/validation/paragraph_node_validator.py` — `_FORBIDDEN_FIELDS` includes `applicability`
