# Concept Node YAML Audit

**Overall status:** PASS

_Filtered projection aligned with `audits/contracts/nodes/concept.md`._

## Summary

- Concept files inspected: 11
- Passing: 11
- Warnings: 0
- Failing: 0

## Enforcement policy

- Validator: `engine/validation/concept_node_validator.py`.
- `concept_class` must be in the allowed ontology list; `category` / `categorical` forbidden.
- Physical/geometric concepts require `dimension` and matching `has_dimension` edge.
- Supplementary tests: `tests/reference/test_concept_ontology.py`.

---

## Concept node inventory

| YAML file | Node ID | Validator | Result | Problems |
| --- | --- | --- | --- | --- |
| `knowledge/global/concepts/nodes/CONCEPT-allowable-stress.yaml` | `CONCEPT-allowable-stress` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-corrosion.yaml` | `CONCEPT-corrosion` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-material.yaml` | `CONCEPT-material` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pipe-construction.yaml` | `CONCEPT-pipe-construction` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pipe-diameter.yaml` | `CONCEPT-pipe-diameter` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pressure.yaml` | `CONCEPT-pressure` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-stress.yaml` | `CONCEPT-stress` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-temperature-coefficient.yaml` | `CONCEPT-temperature-coefficient` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-temperature.yaml` | `CONCEPT-temperature` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-wall-thickness.yaml` | `CONCEPT-wall-thickness` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-weld-joint-efficiency.yaml` | `CONCEPT-weld-joint-efficiency` | `validate_concept_node` | **PASS** | — |
