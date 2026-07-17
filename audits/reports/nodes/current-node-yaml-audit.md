# Current Node YAML Audit

**Overall status:** FAIL

## Summary

- Total files inspected: 140
- Passing: 103
- Warnings: 22
- Failing: 15

### Section totals

- A. Node YAML: 135 files (FAIL)
- B. Node sidecar YAML: 0 files (PASS)
- C. Workflow configuration YAML: 0 files (PASS)
- D. Pack/catalog YAML: 5 files (WARN)

### Node counts by canonical type (Section A)

- `authority`: 3
- `concept`: 12
- `dimension`: 6
- `equation`: 17
- `lookup`: 12
- `material_catalog`: 1
- `paragraph`: 30
- `parameter`: 29
- `table`: 1
- `table_note`: 5
- `unit`: 13
- `validation_rule`: 4
- `workflow`: 2

---

## A. Node YAML inventory

| YAML file | Node ID | Canonical type | Validator | Result | Problems |
| --- | --- | --- | --- | --- | --- |
| `knowledge/global/authorities/nodes/AUTH-ASME-B31.3.yaml` | `AUTH-ASME-B31.3` | `authority` | `validate_authority_node` | **PASS** | — |
| `knowledge/global/authorities/nodes/AUTH-ASME-B36.10M.yaml` | `AUTH-ASME-B36.10M` | `authority` | `validate_authority_node` | **PASS** | — |
| `knowledge/global/authorities/nodes/AUTH-ASTM-A106.yaml` | `AUTH-ASTM-A106` | `authority` | `validate_authority_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-allowable-stress.yaml` | `CONCEPT-allowable-stress` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-corrosion.yaml` | `CONCEPT-corrosion` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-material.yaml` | `CONCEPT-material` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pipe-construction.yaml` | `CONCEPT-pipe-construction` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pipe-diameter.yaml` | `CONCEPT-pipe-diameter` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pipe-geometry.yaml` | `CONCEPT-pipe-geometry` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-pressure.yaml` | `CONCEPT-pressure` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-stress.yaml` | `CONCEPT-stress` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-temperature-coefficient.yaml` | `CONCEPT-temperature-coefficient` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-temperature.yaml` | `CONCEPT-temperature` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-wall-thickness.yaml` | `CONCEPT-wall-thickness` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/concepts/nodes/CONCEPT-weld-joint-efficiency.yaml` | `CONCEPT-weld-joint-efficiency` | `concept` | `validate_concept_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-dimensionless.yaml` | `DIM-dimensionless` | `dimension` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-length.yaml` | `DIM-length` | `dimension` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-material-designation.yaml` | `DIM-material-designation` | `dimension` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-pressure.yaml` | `DIM-pressure` | `dimension` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-temperature.yaml` | `DIM-temperature` | `dimension` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/dimensions/nodes/DIM-velocity.yaml` | `DIM-velocity` | `dimension` | `validate_dimension_node` | **PASS** | — |
| `knowledge/global/materials/nodes/MAT-catalog.yaml` | `MAT-catalog` | `material_catalog` | `none` | **WARN** | non-canonical type material_catalog; no validator mapped |
| `knowledge/global/parameters/nodes/PARAM-actual-wall-thickness.yaml` | `PARAM-actual-wall-thickness` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-1-a |
| `knowledge/global/parameters/nodes/PARAM-allowable-displacement-stress-range.yaml` | `PARAM-allowable-displacement-stress-range` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-allowable-stress.yaml` | `PARAM-allowable-stress` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-2-a |
| `knowledge/global/parameters/nodes/PARAM-basic-casting-quality-factor.yaml` | `PARAM-basic-casting-quality-factor` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes.yaml` | `PARAM-basic-quality-factors-for-longitudinal-weld-joints-in-pipes-and-tubes` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-corrosion-allowance.yaml` | `PARAM-corrosion-allowance` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-design-temperature.yaml` | `PARAM-design-temperature` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-excess-thickness-in-the-branch-pipe-wall.yaml` | `PARAM-excess-thickness-in-the-branch-pipe-wall` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: DIM-area |
| `knowledge/global/parameters/nodes/PARAM-external-design-pressure.yaml` | `PARAM-external-design-pressure` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-inside-diameter.yaml` | `PARAM-inside-diameter` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-internal-design-gage-pressure.yaml` | `PARAM-internal-design-gage-pressure` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-2-a |
| `knowledge/global/parameters/nodes/PARAM-material-grade.yaml` | `PARAM-material-grade` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-maximum-allowable-working-pressure.yaml` | `PARAM-maximum-allowable-working-pressure` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-metallurgical-group.yaml` | `PARAM-metallurgical-group` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-minimum-required-thickness.yaml` | `PARAM-minimum-required-thickness` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-nominal-pipe-size.yaml` | `PARAM-nominal-pipe-size` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: B3610-table-2-1 |
| `knowledge/global/parameters/nodes/PARAM-outside-diameter.yaml` | `PARAM-outside-diameter` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-pipe-construction-type.yaml` | `PARAM-pipe-construction-type` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-pipe-schedule.yaml` | `PARAM-pipe-schedule` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: B3610-table-2-1 |
| `knowledge/global/parameters/nodes/PARAM-pressure-loading.yaml` | `PARAM-pressure-loading` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-2-a; edge target not in repository index: asme-b313-304-1-3 |
| `knowledge/global/parameters/nodes/PARAM-required-reinforcement-area.yaml` | `PARAM-required-reinforcement-area` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: DIM-area |
| `knowledge/global/parameters/nodes/PARAM-required-wall-thickness.yaml` | `PARAM-required-wall-thickness` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-1-a; edge target not in repository index: asme-b313-304-1-2-a; edge target not in repository index: asme-b313-304-1-2-b |
| `knowledge/global/parameters/nodes/PARAM-run-excess-thickness-area.yaml` | `PARAM-run-excess-thickness-area` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: DIM-area |
| `knowledge/global/parameters/nodes/PARAM-straight-pipe-section.yaml` | `PARAM-straight-pipe-section` | `parameter` | `validate_parameter_node` | **WARN** | edge target not in repository index: asme-b313-304-1-1-a |
| `knowledge/global/parameters/nodes/PARAM-stress-range-factor.yaml` | `PARAM-stress-range-factor` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-temperature-coefficient-Y.yaml` | `PARAM-temperature-coefficient-y` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-thin-wall-applicability.yaml` | `PARAM-thin-wall-applicability` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-wall-thickness-basis.yaml` | `PARAM-wall-thickness-basis` | `parameter` | `validate_parameter_node` | **PASS** | — |
| `knowledge/global/parameters/nodes/PARAM-weld-strength-reduction-factor-W.yaml` | `PARAM-weld-strength-reduction-factor-w` | `parameter` | `validate_parameter_node` | **PASS** | — |
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
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-302-3-5-eq-1a.yaml` | `asme-b313-302-3-5-eq-1a` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-302-3-5-eq-1b.yaml` | `asme-b313-302-3-5-eq-1b` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-302-3-5-eq-1c.yaml` | `asme-b313-302-3-5-eq-1c` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-1-eq-2.yaml` | `asme-b313-304-1-1-eq-2` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3a.yaml` | `asme-b313-304-1-2-eq-3a` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-1-2-eq-3b.yaml` | `asme-b313-304-1-2-eq-3b` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-3-3-eq-6.yaml` | `asme-b313-304-3-3-eq-6` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-3-3-eq-7.yaml` | `asme-b313-304-3-3-eq-7` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-304-3-3-eq-8.yaml` | `asme-b313-304-3-3-eq-8` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-mawp-pressure.yaml` | `asme-b313-mawp-pressure` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/equation/asme-b313-pressure-design-thickness.yaml` | `asme-b313-pressure-design-thickness` | `equation` | `validate_equation_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/lookups/asme-b3610-nps-outside-diameter-lookup.yaml` | `asme-b3610-nps-outside-diameter-lookup` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; requires_parameter edge targets PARAM-nominal-pipe-size but requires block omits it |
| `knowledge/standards/asme/asme_b31.3/nodes/lookups/asme-b3610-pipe-dimensions-lookup.yaml` | `asme-b3610-pipe-dimensions-lookup` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; requires_parameter edge targets PARAM-nominal-pipe-size but requires block omits it; requires_parameter edge targets PARAM-pipe-schedule but requires block omits it |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-a.yaml` | `302.3.3-a` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-b.yaml` | `302.3.3-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.3-c.yaml` | `302.3.3-c` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-a.yaml` | `302.3.5-a` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-b.yaml` | `302.3.5-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-c.yaml` | `302.3.5-c` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-d.yaml` | `302.3.5-d` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-e.yaml` | `302.3.5-e` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/302.3.5-f.yaml` | `302.3.5-f` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-a.yaml` | `304.1.1-a` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.1-b.yaml` | `304.1.1-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-a.yaml` | `304.1.2-a` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.2-b.yaml` | `304.1.2-b` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/paragraph/304.1.3.yaml` | `304.1.3` | `paragraph` | `validate_paragraph_node` | **PASS** | — |
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
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1-note-1.yaml` | `asme-b313-table-302-3-3-1-note-1` | `table_note` | `validate_table_note_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1-note-2a.yaml` | `asme-b313-table-302-3-3-1-note-2a` | `table_note` | `validate_table_note_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1-note-2b.yaml` | `asme-b313-table-302-3-3-1-note-2b` | `table_note` | `validate_table_note_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1-note-3a.yaml` | `asme-b313-table-302-3-3-1-note-3a` | `table_note` | `validate_table_note_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1-note-3b.yaml` | `asme-b313-table-302-3-3-1-note-3b` | `table_note` | `validate_table_note_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-1.yaml` | `asme-b313-table-302-3-3-1` | `lookup` | `validate_lookup_node` | **FAIL** | lookup.keys is deprecated; use lookup.bindings; lookup.bindings is required |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-3-2.yaml` | `asme-b313-table-302-3-3-2` | `table` | `revision_only` | **WARN** | no dedicated validator for type table |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-302-3-5-1.yaml` | `asme-b313-table-302-3-5-1` | `lookup` | `validate_lookup_node` | **FAIL** | requires_parameter edge targets PARAM-design-temperature but requires block omits it; requires_parameter edge targets PARAM-material-grade but requires block omits it; requires_parameter edge targets PARAM-pipe-construction-type but requires block omits it |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-304-1-1-1.yaml` | `asme-b313-table-304-1-1-1` | `lookup` | `validate_lookup_node` | **FAIL** | requires_parameter edge targets PARAM-design-temperature but requires block omits it; requires_parameter edge targets PARAM-metallurgical-group but requires block omits it |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-1.yaml` | `asme-b313-table-A-1` | `lookup` | `validate_lookup_node` | **FAIL** | requires_parameter edge targets PARAM-design-temperature but requires block omits it; requires_parameter edge targets PARAM-material-grade but requires block omits it |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-2.yaml` | `asme-b313-table-A-2` | `lookup` | `validate_lookup_node` | **FAIL** | requires_parameter edge targets PARAM-material-grade but requires block omits it |
| `knowledge/standards/asme/asme_b31.3/nodes/tables/asme-b313-table-A-3.yaml` | `asme-b313-table-A-3` | `lookup` | `validate_lookup_node` | **FAIL** | requires_parameter edge targets PARAM-material-grade but requires block omits it; requires_parameter edge targets PARAM-pipe-construction-type but requires block omits it |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-1-valrule-a.yaml` | `asme-b313-304-1-1-valrule-a` | `validation_rule` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-wall-thickness-adequacy |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-2-valrule-a.yaml` | `asme-b313-304-1-2-valrule-a` | `validation_rule` | `validate_validation_rule_node` | **PASS** | — |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-1-2-valrule-b.yaml` | `asme-b313-304-1-2-valrule-b` | `validation_rule` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-thick-wall-special-consideration-required |
| `knowledge/standards/asme/asme_b31.3/nodes/validation_rule/asme-b313-304-3-3-valrule-6a.yaml` | `asme-b313-304-3-3-valrule-6a` | `validation_rule` | `validate_validation_rule_node` | **WARN** | edge target not in repository index: PARAM-reinforcement-adequate |
| `knowledge/standards/astm/nodes/A105.yaml` | `A105` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: material_properties |
| `knowledge/standards/astm/nodes/A106.yaml` | `A106` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: mechanical_properties |
| `knowledge/standards/astm/nodes/A312.yaml` | `A312` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: mechanical_properties |
| `knowledge/standards/astm/nodes/A53.yaml` | `A53` | `lookup` | `validate_lookup_node` | **FAIL** | missing table_number; lookup requires table_id, lookup.table, or reads_table edge; lookup requires output_param, returns, or returns_parameter edge; introduces_parameter not allowed from source type 'lookup'; introduces_parameter not allowed from source type 'lookup'; broken resolved reference: material_properties |
| `workflows/mawp.yaml` | `WF-MAWP` | `workflow` | `validate_workflow_node` | **WARN** | filename stem 'mawp' differs from id 'WF-MAWP' |
| `workflows/pipe-wall-thickness.yaml` | `WF-PIPE-WALL-THICKNESS` | `workflow` | `validate_workflow_node` | **WARN** | filename stem 'pipe-wall-thickness' differs from id 'WF-PIPE-WALL-THICKNESS' |

## B. Node sidecar YAML inventory

| YAML file | Parent node | Contract | Result | Problems |
| --- | --- | --- | --- | --- |

## C. Workflow configuration YAML inventory

| YAML file | Parent workflow | Contract | Result | Problems |
| --- | --- | --- | --- | --- |

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
- One primary YAML per node: nested `execution` / `runtime` blocks in primary files.
- `material_catalog` (`MAT-catalog.yaml`) is not in `CANONICAL_NODE_TYPES`.
- Legacy node-owned sidecars are rejected when `LEGACY_SIDECAR_COMPAT` is false.
- Legacy `workflows/*/runtime.yaml` and `navigation.yaml` files are rejected when `LEGACY_SIDECAR_COMPAT` is false; canonical runtime metadata is nested `runtime` in primary workflow YAML.
- Types `text`, `quantity`, `table` have no dedicated validators — audit uses revision + generic checks only.
- `designation` uses `validate_designation_node` (see `audits/contracts/nodes/designation.md`).
- `table_note` uses `validate_table_note_node` (see `audits/contracts/nodes/table-note.md`).
- `dimension` uses `validate_dimension_node` (see `audits/contracts/nodes/dimension.md`).
- `concept` uses `validate_concept_node` (see `audits/contracts/nodes/concept.md`).
- Human-readable contract documents are not parsed by this audit script; validators remain enforcement authority.

