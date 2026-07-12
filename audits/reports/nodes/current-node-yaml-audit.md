# Current Node YAML Audit

**Overall status:** FAIL

## Summary

- Total files inspected: 137
- Passing: 87
- Warnings: 35
- Failing: 15

### Section totals

- A. Node YAML: 126 files (FAIL)
- B. Node sidecar YAML: 4 files (WARN)
- C. Workflow configuration YAML: 2 files (PASS)
- D. Pack/catalog YAML: 5 files (WARN)

### Node counts by canonical type (Section A)

- `authority`: 3
- `concept`: 11
- `dimension`: 6
- `equation`: 17
- `lookup`: 10
- `material_catalog`: 1
- `paragraph`: 30
- `parameter`: 24
- `text`: 5
- `unit`: 13
- `validation_rule`: 4
- `workflow`: 2

---

## A. Node YAML inventory

| YAML file | Node ID | Canonical type | Validator | Result | Problems |
| --- | --- | --- | --- | --- | --- |
| `knowledge/global/authorities/nodes/AUTH-ASME-B31.3.yaml` | `AUTH-ASME-B31.3` | `authority` | `validate_authority_node` | **PASS** | — |
| `knowledge/global/authorities/nodes/AUTH-ASME-B36.10M.yaml` | `AUTH-ASME-B36.10M` | `authority` | `validate_authority_node` | **WARN** | edge target not in repository index: PARAM-nominal-wall-thickness |
| `knowledge/global/authorities/nodes/AUTH-ASTM-A106.yaml` | `AUTH-ASTM-A106` | `authority` | `validate_authority_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-allowable-stress.yaml` | `CONCEPT-allowable-stress` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-corrosion.yaml` | `CONCEPT-corrosion` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-material.yaml` | `CONCEPT-material` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pipe-construction.yaml` | `CONCEPT-pipe-construction` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pipe-diameter.yaml` | `CONCEPT-pipe-diameter` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pressure.yaml` | `CONCEPT-pressure` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-stress.yaml` | `CONCEPT-stress` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-temperature-coefficient.yaml` | `CONCEPT-temperature-coefficient` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-temperature.yaml` | `CONCEPT-temperature` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-wall-thickness.yaml` | `CONCEPT-wall-thickness` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-weld-joint-efficiency.yaml` | `CONCEPT-weld-joint-efficiency` | `concept` | `ontology_concept_checks` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-dimensionless.yaml` | `DIM-dimensionless` | `dimension` | `ontology_dimension_checks` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-length.yaml` | `DIM-length` | `dimension` | `ontology_dimension_checks` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-material-designation.yaml` | `DIM-material-designation` | `dimension` | `ontology_dimension_checks` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-pressure.yaml` | `DIM-pressure` | `dimension` | `ontology_dimension_checks` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-temperature.yaml` | `DIM-temperature` | `dimension` | `ontology_dimension_checks` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-velocity.yaml` | `DIM-velocity` | `dimension` | `ontology_dimension_checks` | **PASS** | — |
| `knowledge/global/materials/nodes/MAT-catalog.yaml` | `MAT-catalog` | `material_catalog` | `none` | **WARN** | non-canonical type material_catalog; no validator mapped |
| `knowledge/global/parameters/nodes/PARAM-actual-wall-thickness.yaml` | `PARAM-actual-wall-thickness` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-1-a |
| `knowledge/global/parameters/nodes/PARAM-allowable-stress.yaml` | `PARAM-allowable-stress` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-2-a |
| `knowledge/global/parameters/nodes/PARAM-corrosion-allowance.yaml` | `PARAM-corrosion-allowance` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-design-temperature.yaml` | `PARAM-design-temperature` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-external-design-pressure.yaml` | `PARAM-external-design-pressure` | `parameter` | `validate_parameter_node` | **FAIL** | introduced_by paragraph reference must use pack-qualified id, not bare: 304.1.3 |
| `knowledge/global/parameters/nodes/PARAM-geometry-input-mode.yaml` | `PARAM-geometry-input-mode` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-inside-diameter.yaml` | `PARAM-inside-diameter` | `parameter` | `validate_parameter_node` | **FAIL** | introduced_by paragraph reference must use pack-qualified id, not bare: 304.1.2-a |
| `knowledge/global/parameters/nodes/PARAM-internal-design-gage-pressure.yaml` | `PARAM-internal-design-gage-pressure` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-2-a |
| `knowledge/global/parameters/nodes/PARAM-material-grade.yaml` | `PARAM-material-grade` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-maximum-allowable-working-pressure.yaml` | `PARAM-maximum-allowable-working-pressure` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-metallurgical-group.yaml` | `PARAM-metallurgical-group` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-minimum-required-thickness.yaml` | `PARAM-minimum-required-thickness` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-nominal-pipe-size.yaml` | `PARAM-nominal-pipe-size` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: B3610-table-2-1 |
| `knowledge/global/parameters/nodes/PARAM-outside-diameter.yaml` | `PARAM-outside-diameter` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: B3610-table-2-1 |
| `knowledge/global/parameters/nodes/PARAM-pipe-construction-type.yaml` | `PARAM-pipe-construction-type` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-pipe-schedule.yaml` | `PARAM-pipe-schedule` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: B3610-table-2-1 |
| `knowledge/global/parameters/nodes/PARAM-pressure-loading.yaml` | `PARAM-pressure-loading` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-2-a; edge target not in repository index: asme-b313-304-1-3 |
| `knowledge/global/parameters/nodes/PARAM-required-wall-thickness.yaml` | `PARAM-required-wall-thickness` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-1-a; edge target not in repository index: asme-b313-304-1-2-a; edge target not in repository index: asme-b313-304-1-2-b |
| `knowledge/global/parameters/nodes/PARAM-straight-pipe-section.yaml` | `PARAM-straight-pipe-section` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-1-a |
| `knowledge/global/parameters/nodes/PARAM-temperature-coefficient-Y.yaml` | `PARAM-temperature-coefficient-Y` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-thin-wall-applicability.yaml` | `PARAM-thin-wall-applicability` | `parameter` | `validate_parameter_node` | **FAIL** | introduced_by paragraph reference must use pack-qualified id, not bare: 304.1.2-a |
| `knowledge/global/parameters/nodes/PARAM-wall-thickness-basis.yaml` | `PARAM-wall-thickness-basis` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-weld-joint-efficiency.yaml` | `PARAM-weld-joint-efficiency` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-weld-strength-reduction-factor-W.yaml` | `PARAM-weld-strength-reduction-factor-W` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-K.yaml` | `UNIT-K` | `unit` | `validate_unit_node` | **FAIL** | unknown equation referenced by converts_to: EQ-unit-K-to-degC; unknown equation referenced by converts_to: EQ-unit-K-to-degF |
| `knowledge/global/units/nodes/UNIT-MPa.yaml` | `UNIT-MPa` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-Pa.yaml` | `UNIT-Pa` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-bar.yaml` | `UNIT-bar` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-degC.yaml` | `UNIT-degC` | `unit` | `validate_unit_node` | **FAIL** | unknown equation referenced by converts_to: EQ-unit-degC-to-K; unknown equation referenced by converts_to: EQ-unit-degC-to-degF |
| `knowledge/global/units/nodes/UNIT-degF.yaml` | `UNIT-degF` | `unit` | `validate_unit_node` | **FAIL** | unknown equation referenced by converts_to: EQ-unit-degF-to-K; unknown equation referenced by converts_to: EQ-unit-degF-to-degC |
| `knowledge/global/units/nodes/UNIT-dimensionless.yaml` | `UNIT-dimensionless` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-ft_s.yaml` | `UNIT-ft_s` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-in.yaml` | `UNIT-in` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-m.yaml` | `UNIT-m` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-m_s.yaml` | `UNIT-m_s` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-mm.yaml` | `UNIT-mm` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/UNIT-psi.yaml` | `UNIT-psi` | `unit` | `validate_unit_node` | **PASS** | — |
| `knowledge/global/units/nodes/equation/EQ-unit-K-to-degC.yaml` | `EQ-unit-K-to-degC` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/global/units/nodes/equation/EQ-unit-K-to-degF.yaml` | `EQ-unit-K-to-degF` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/global/units/nodes/equation/EQ-unit-degC-to-K.yaml` | `EQ-unit-degC-to-K` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/global/units/nodes/equation/EQ-unit-degC-to-degF.yaml` | `EQ-unit-degC-to-degF` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/global/units/nodes/equation/EQ-unit-degF-to-K.yaml` | `EQ-unit-degF-to-K` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/global/units/nodes/equation/EQ-unit-degF-to-degC.yaml` | `EQ-unit-degF-to-degC` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-302-3-5-eq-1a.yaml` | `asme-b313-302-3-5-eq-1a` | `equation` | `validate_equation_node` | **WARN** | edge target not in repository index: PARAM-allowable-displacement-stress-range |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-302-3-5-eq-1b.yaml` | `asme-b313-302-3-5-eq-1b` | `equation` | `validate_equation_node` | **WARN** | edge target not in repository index: PARAM-allowable-displacement-stress-range |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-302-3-5-eq-1c.yaml` | `asme-b313-302-3-5-eq-1c` | `equation` | `validate_equation_node` | **WARN** | edge target not in repository index: PARAM-stress-range-factor |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-1-eq-2.yaml` | `asme-b313-304-1-1-eq-2` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3a.yaml` | `asme-b313-304-1-2-eq-3a` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3b.yaml` | `asme-b313-304-1-2-eq-3b` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-3-3-eq-6.yaml` | `asme-b313-304-3-3-eq-6` | `equation` | `validate_equation_node` | **WARN** | edge target not in repository index: PARAM-required-reinforcement-area |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-3-3-eq-7.yaml` | `asme-b313-304-3-3-eq-7` | `equation` | `validate_equation_node` | **WARN** | edge target not in repository index: PARAM-run-excess-thickness-area |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-3-3-eq-8.yaml` | `asme-b313-304-3-3-eq-8` | `equation` | `validate_equation_node` | **WARN** | edge target not in repository index: PARAM-branch-excess-thickness-area |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-mawp-pressure.yaml` | `asme-b313-mawp-pressure` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-pressure-design-thickness.yaml` | `asme-b313-pressure-design-thickness` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-a.yaml` | `302.3.3-a` | `paragraph` | `validate_paragraph_node` | **FAIL** | broken resolved reference: PARAM-casting-quality-factor |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-b.yaml` | `302.3.3-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-c.yaml` | `302.3.3-c` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-a.yaml` | `302.3.5-a` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-b.yaml` | `302.3.5-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-c.yaml` | `302.3.5-c` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-d.yaml` | `302.3.5-d` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-e.yaml` | `302.3.5-e` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-f.yaml` | `302.3.5-f` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-a.yaml` | `304.1.1-a` | `paragraph` | `validate_paragraph_node` | **WARN** | assumptions belongs in execution sidecar; migration required |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-b.yaml` | `304.1.1-b` | `paragraph` | `validate_paragraph_node` | **WARN** | parameter_defaults belongs in execution sidecar; migration required |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.yaml` | `304.1.2-a` | `paragraph` | `validate_paragraph_node` | **FAIL** | forbidden field: applicability; Execution metadata split across two authoring surfaces: frontmatter has ['applicability']; sidecar has ['conditions', 'provisional_assumptions', 'subsections']; consolidate into sidecar |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-b.yaml` | `304.1.2-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.3.yaml` | `304.1.3` | `paragraph` | `validate_paragraph_node` | **FAIL** | forbidden field: applicability |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.yaml` | `304.1` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.1-b.yaml` | `304.3.1-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.1-c.yaml` | `304.3.1-c` | `paragraph` | `validate_paragraph_node` | **WARN** | unresolved related_to target: 304.7.2 — register or author node |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.1-d.yaml` | `304.3.1-d` | `paragraph` | `validate_paragraph_node` | **WARN** | unresolved related_to target: 304.3.5 — register or author node |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.1.yaml` | `304.3.1` | `paragraph` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 328.5.4; registered external/unmodeled reference: 300.2 |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.2-a.yaml` | `304.3.2-a` | `paragraph` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 303 |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.2-b.yaml` | `304.3.2-b` | `paragraph` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 328.5.4 |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.2-c.yaml` | `304.3.2-c` | `paragraph` | `validate_paragraph_node` | **WARN** | registered external/unmodeled reference: 300.2; unresolved related_to target: 304.7.2 — register or author node |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-a.yaml` | `304.3.3-a` | `paragraph` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 300.2; registered external/unmodeled reference: Appendix-J |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-b.yaml` | `304.3.3-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-c.yaml` | `304.3.3-c` | `paragraph` | `validate_paragraph_node` | **PASS** | registered external/unmodeled reference: 328.5.4 |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-d.yaml` | `304.3.3-d` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-e.yaml` | `304.3.3-e` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.3-f.yaml` | `304.3.3-f` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.3.yaml` | `304.3` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.yaml` | `304` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-note-302-3-3C-1.yaml` | `asme-b313-note-302-3-3C-1` | `text` | `revision_only` | **WARN** | no dedicated validator for type text |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-note-302-3-3C-2a.yaml` | `asme-b313-note-302-3-3C-2a` | `text` | `revision_only` | **WARN** | no dedicated validator for type text |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-note-302-3-3C-2b.yaml` | `asme-b313-note-302-3-3C-2b` | `text` | `revision_only` | **WARN** | no dedicated validator for type text |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-note-302-3-3C-3a.yaml` | `asme-b313-note-302-3-3C-3a` | `text` | `revision_only` | **WARN** | no dedicated validator for type text |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-note-302-3-3C-3b.yaml` | `asme-b313-note-302-3-3C-3b` | `text` | `revision_only` | **WARN** | no dedicated validator for type text |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3C.yaml` | `asme-b313-table-302-3-3C` | `lookup` | `validate_lookup_node` | **FAIL** | lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: quality_factor |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-5-1.yaml` | `asme-b313-table-302-3-5-1` | `lookup` | `validate_lookup_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-304-1-1-1.yaml` | `asme-b313-table-304-1-1-1` | `lookup` | `validate_lookup_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-1.yaml` | `asme-b313-table-A-1` | `lookup` | `validate_lookup_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-2.yaml` | `asme-b313-table-A-2` | `lookup` | `validate_lookup_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-3.yaml` | `asme-b313-table-A-3` | `lookup` | `validate_lookup_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-1-valrule-a.yaml` | `asme-b313-304-1-1-valrule-a` | `validation_rule` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-wall-thickness-adequacy |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-2-valrule-a.yaml` | `asme-b313-304-1-2-valrule-a` | `validation_rule` | `validate_validation_rule_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-2-valrule-b.yaml` | `asme-b313-304-1-2-valrule-b` | `validation_rule` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-thick-wall-special-consideration-required |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-3-3-valrule-6a.yaml` | `asme-b313-304-3-3-valrule-6a` | `validation_rule` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-reinforcement-adequate |
| `knowledge/standards/astm/nodes/A105.yaml` | `A105` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: material_properties |
| `knowledge/standards/astm/nodes/A106.yaml` | `A106` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: mechanical_properties |
| `knowledge/standards/astm/nodes/A312.yaml` | `A312` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: mechanical_properties |
| `knowledge/standards/astm/nodes/A53.yaml` | `A53` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: material_properties |
| `workflows/mawp.yaml` | `WF-MAWP` | `workflow` | `validate_workflow_node` | **FAIL** | forbidden field in frontmatter: assumptions; filename stem 'mawp' differs from id 'WF-MAWP' |
| `workflows/pipe-wall-thickness.yaml` | `WF-PIPE-WALL-THICKNESS` | `workflow` | `validate_workflow_node` | **WARN** | filename stem 'pipe-wall-thickness' differs from id 'WF-PIPE-WALL-THICKNESS' |

## B. Node sidecar YAML inventory

| YAML file | Parent node | Contract | Result | Problems |
| --- | --- | --- | --- | --- |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.execution.yaml` | `304.1.2-a` | `paragraph-execution.md` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme_b313_304_1_1_valrule_a/execution.yaml` | `asme_b313_304_1_1_valrule_a` | `equation-execution.md` | **WARN** | parent node 'asme_b313_304_1_1_valrule_a' not found in section A index |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme_b313_304_1_2_valrule_b/execution.yaml` | `asme_b313_304_1_2_valrule_b` | `equation-execution.md` | **WARN** | parent node 'asme_b313_304_1_2_valrule_b' not found in section A index |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme_b313_304_3_3_valrule_6a/execution.yaml` | `asme_b313_304_3_3_valrule_6a` | `equation-execution.md` | **WARN** | parent node 'asme_b313_304_3_3_valrule_6a' not found in section A index |

## C. Workflow configuration YAML inventory

| YAML file | Parent workflow | Contract | Result | Problems |
| --- | --- | --- | --- | --- |
| `workflows/WF-MAWP/runtime.yaml` | `WF-MAWP` | `workflow-runtime.md` | **PASS** | — |
| `workflows/WF-PIPE-WALL-THICKNESS/runtime.yaml` | `WF-PIPE-WALL-THICKNESS` | `workflow-runtime.md` | **PASS** | — |

## D. Pack/catalog YAML inventory

| YAML file | Role | Contract | Result | Problems |
| --- | --- | --- | --- | --- |
| `knowledge/standards/asme/asme_b31.3/pack.yaml` | pack metadata | `pack-metadata.md` | **PASS** | — |
| `knowledge/global/materials/registry.yaml` | catalog registry | `pack-metadata.md` | **PASS** | — |
| `knowledge/global/materials/supplemental.yaml` | supplemental catalog | `pack-metadata.md` | **PASS** | — |
| `knowledge/global/dimensions/registry.yaml` | catalog registry | `pack-metadata.md` | **PASS** | — |
| `knowledge/standards/asme/asme_b36.10/tables/B3610-table-2-1.yaml` | raw table data | `pack-metadata.md` | **WARN** | raw table data without node frontmatter |

---

## Implementation inconsistencies affecting YAML authoring

- Production table nodes use `type: lookup`, not `table`.
- `material_catalog` (`MAT-catalog.yaml`) is not in `CANONICAL_NODE_TYPES`.
- Flat `{id}.execution.yaml` files are loaded as sidecars but may also match node discovery if given frontmatter.
- Paragraph field placement policy: `engine/reference/paragraph_authoring_policy.py`.
- Paragraph frontmatter validators forbid fields that paragraph execution sidecars merge at compile time.
- Types `text`, `quantity`, `designation`, `table` have no dedicated validators — audit uses revision + generic checks only.
- Human-readable contract documents are not parsed by this audit script; validators remain enforcement authority.

