# Table Node Template

A Table node represents authoritative structured data from a standard, code, specification, company document, or project document.

A Table belongs to an Authority.  
A Table may provide values for Parameters.  
A Table is consumed by Lookup nodes.

A Table does not execute itself.  
A Table does not create Facts directly.  
A Lookup node reads the Table and produces Facts.

```yaml
---
id: TABLE-B313-allowable-stress
type: table

key: b313_allowable_stress
name: ASME B31.3 Allowable Stress Table

table_class: material_property_table

authority: AUTH-ASME-B31.3
edition: 2024

description: >
  Authoritative allowable stress table used to resolve allowable stress
  based on material specification and design temperature.

provides_parameters:
  - PARAM-allowable-stress

lookup_keys:
  - parameter: PARAM-material-specification
    role: row_key
    required: true

  - parameter: PARAM-design-temperature
    role: column_key
    required: true

provided_values:
  - parameter: PARAM-allowable-stress
    dimension: DIM-pressure

lookup_rules:
  interpolation: false
  temperature_selection: lower_applicable_value
  missing_material: error
  missing_temperature: error
  out_of_range_temperature: warning_or_error

source:
  authority: AUTH-ASME-B31.3
  paragraph: null
  table_number: "A-1"
  source_revision_year: 2024

data:
  storage: external_yaml
  path: standards/asme/asme_b31.3/tables/material_allowable_stress.yaml

edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B31.3

  - type: provides_parameter_values_for
    target: PARAM-allowable-stress

  - type: requires_parameter
    target: PARAM-material-specification

  - type: requires_parameter
    target: PARAM-design-temperature

metadata:
  status: active
  version: 1
---
```

---

# Purpose

A Table answers:

```text
Which authoritative structured data source provides values for this engineering lookup?
```

Examples:

```text
ASME B31.3 allowable stress table
ASME B31.3 Y coefficient table
ASME B36.10M pipe dimension table
ASTM A106 chemical composition table
ASTM A106 mechanical properties table
Company corrosion allowance table
Project line class table
```

A Table stores or references structured authority data.

A Table does not decide when it applies.  
Applicability comes from Authority Context, Paragraphs, Lookup nodes, and Validation rules.

---

# Required fields

|Field|Purpose|
|---|---|
|`id`|Stable table identity. Must use `TABLE-*`.|
|`type`|Must be `table`.|
|`key`|Machine-safe table key.|
|`name`|Human-readable table name.|
|`table_class`|Kind of table.|
|`authority`|Parent Authority node.|
|`description`|Stable engineering description.|
|`source`|Source locator within the authority.|
|`metadata`|Status and versioning.|

---

# Recommended `table_class` values

```yaml
material_property_table
allowable_stress_table
dimensional_table
coefficient_table
chemical_composition_table
mechanical_property_table
selection_table
rating_table
limit_table
acceptance_criteria_table
company_rule_table
project_data_table
```

---

# Table vs Lookup node

A Table stores authoritative data.

A Lookup node defines how to use that data.

```text
Table:
  ASME B31.3 allowable stress data

Lookup node:
  Given material + temperature, retrieve allowable stress

Fact:
  Allowable Stress = 138 MPa
```

Do not put lookup behavior only inside the Table.

The Table may define default lookup rules, but the Lookup node is the executable contract.

---

# Table vs Fact

A Table row is not a runtime Fact.

Example table row:

```text
ASTM A106 Grade B at 400°F → allowable stress = 20,000 psi
```

This is authority data.

It becomes a Fact only when selected during execution:

```text
FACT-allowable-stress-001
  parameter: PARAM-allowable-stress
  value: 20,000 psi
  source: TABLE-B313-allowable-stress
```

---

# Example: ASME B36.10M pipe dimensions table

```yaml
---
id: TABLE-B36.10M-pipe-dimensions
type: table

key: b36_10m_pipe_dimensions
name: ASME B36.10M Pipe Dimensions

table_class: dimensional_table

authority: AUTH-ASME-B36.10M
edition: 2022

description: >
  Pipe dimensional table used to resolve outside diameter and nominal wall
  thickness from nominal pipe size and schedule.

lookup_keys:
  - parameter: PARAM-nominal-pipe-size
    role: row_key
    required: true

  - parameter: PARAM-pipe-schedule
    role: column_key
    required: false

provided_values:
  - parameter: PARAM-outside-diameter
    dimension: DIM-length

  - parameter: PARAM-nominal-wall-thickness
    dimension: DIM-length

lookup_rules:
  interpolation: false
  exact_nps_required: true
  exact_schedule_required: true

source:
  authority: AUTH-ASME-B36.10M
  table_number: "Pipe Dimensions"
  source_revision_year: 2022

data:
  storage: external_yaml
  path: standards/asme/asme_b36.10/tables/welded_seamless_pipe_dimensions.yaml

edges:
  - type: belongs_to_authority
    target: AUTH-ASME-B36.10M

  - type: provides_parameter_values_for
    target: PARAM-outside-diameter

  - type: provides_parameter_values_for
    target: PARAM-nominal-wall-thickness

metadata:
  status: active
  version: 1
---
```

---

# Example: ASTM A106 chemical composition table

```yaml
---
id: TABLE-ASTM-A106-chemical-composition
type: table

key: astm_a106_chemical_composition
name: ASTM A106 Chemical Composition Table

table_class: chemical_composition_table

authority: AUTH-ASTM-A106
edition: 2024

description: >
  Chemical composition limits for ASTM A106 material grades.

lookup_keys:
  - parameter: PARAM-material-specification
    role: material_standard
    required: true

  - parameter: PARAM-material-grade
    role: grade
    required: true

provided_values:
  - parameter: PARAM-carbon-content
    dimension: DIM-dimensionless

  - parameter: PARAM-manganese-content
    dimension: DIM-dimensionless

  - parameter: PARAM-phosphorus-content
    dimension: DIM-dimensionless

  - parameter: PARAM-sulfur-content
    dimension: DIM-dimensionless

lookup_rules:
  interpolation: false
  value_type: limit_range
  missing_grade: error

source:
  authority: AUTH-ASTM-A106
  table_number: "Chemical Requirements"
  source_revision_year: 2024

data:
  storage: external_yaml
  path: standards/astm/astm_a106/tables/chemical_composition.yaml

edges:
  - type: belongs_to_authority
    target: AUTH-ASTM-A106

  - type: provides_parameter_values_for
    target: PARAM-carbon-content

  - type: provides_parameter_values_for
    target: PARAM-manganese-content

metadata:
  status: active
  version: 1
---
```

---

# Example: ASTM A106 mechanical properties table

```yaml
---
id: TABLE-ASTM-A106-mechanical-properties
type: table

key: astm_a106_mechanical_properties
name: ASTM A106 Mechanical Properties Table

table_class: mechanical_property_table

authority: AUTH-ASTM-A106
edition: 2024

description: >
  Mechanical property requirements for ASTM A106 material grades.

lookup_keys:
  - parameter: PARAM-material-specification
    role: material_standard
    required: true

  - parameter: PARAM-material-grade
    role: grade
    required: true

provided_values:
  - parameter: PARAM-yield-strength
    dimension: DIM-pressure

  - parameter: PARAM-tensile-strength
    dimension: DIM-pressure

  - parameter: PARAM-elongation
    dimension: DIM-dimensionless

lookup_rules:
  interpolation: false
  value_type: minimum_required_property
  missing_grade: error

source:
  authority: AUTH-ASTM-A106
  table_number: "Tensile Requirements"
  source_revision_year: 2024

data:
  storage: external_yaml
  path: standards/astm/astm_a106/tables/mechanical_properties.yaml

edges:
  - type: belongs_to_authority
    target: AUTH-ASTM-A106

  - type: provides_parameter_values_for
    target: PARAM-yield-strength

  - type: provides_parameter_values_for
    target: PARAM-tensile-strength

metadata:
  status: active
  version: 1
---
```

---

# Data storage model

Tables may store data inline or externally.

## External YAML

```yaml
data:
  storage: external_yaml
  path: standards/asme/asme_b31.3/tables/material_allowable_stress.yaml
```

## Inline data

Useful only for small tables.

```yaml
data:
  storage: inline
  rows:
    - material: ASTM A106 Grade B
      temperature: 400 degF
      allowable_stress: 20000 psi
```

For production standards, prefer external structured files.

---

# Lookup rules

Lookup rules should be explicit.

```yaml
lookup_rules:
  interpolation: false
  temperature_selection: lower_applicable_value
  missing_key: error
  out_of_range: warning_or_error
```

Recommended lookup rule fields:

|Field|Purpose|
|---|---|
|`interpolation`|Whether interpolation is allowed.|
|`temperature_selection`|Exact, lower applicable, upper applicable, nearest, etc.|
|`missing_key`|Behavior when lookup key is missing.|
|`out_of_range`|Behavior when requested value exceeds table range.|
|`value_type`|Exact value, limit, minimum, maximum, range.|

---

# Table source model

Every Table should be traceable to authority.

```yaml
source:
  authority: AUTH-ASME-B31.3
  paragraph: B313-302.3
  table_number: "A-1"
  source_revision_year: 2024
```

The report should be able to say:

```text
Allowable stress was obtained from ASME B31.3 Table A-1, 2024 edition.
```

---

# Allowed relationships

Table nodes may use:

```yaml
belongs_to_authority
referenced_by_paragraph
provides_parameter_values_for
requires_parameter
constrains_parameter
used_by_lookup
supersedes
superseded_by
```

`used_by_lookup` is a reverse-only query type — do not author on tables.  
Author `reads_table` on the lookup node instead.

Example (forward authoring on lookup):

```yaml
edges:
  - type: reads_table
    target: TABLE-B313-allowable-stress
```

Example (inverse, query only):

```yaml
edges:
  - type: used_by_lookup
    target: LOOKUP-B313-material-allowable-stress
```

---

# Report behavior

A Table should appear in reports when it:

```text
provided a looked-up value
constrained an input
created a warning
defined an acceptance limit
was selected by Authority Context
```

Reports should include:

```text
authority
edition
table number
lookup keys used
selected row or basis
resulting Fact
lookup rule
warnings or range handling
```

---

# Forbidden fields

Table nodes must not contain runtime execution values.

Forbidden:

```yaml
selected_row:
runtime_lookup_result:
fact_id:
execution_id:
task_id:
user_input:
active_in_context:
```

Those belong to Facts, Execution Context, or Lookup trace.

---

# Validation rules

A Table node is invalid if:

1. `type` is not `table`.
    
2. `id` does not start with `TABLE-`.
    
3. It has no parent Authority.
    
4. It lacks a source locator.
    
5. It provides values for unknown Parameters.
    
6. It has lookup keys that are not Parameters.
    
7. It stores runtime-selected rows as immutable data.
    
8. It lacks explicit lookup rules when lookup behavior affects engineering results.
    
9. It duplicates Concept or Parameter definitions.
    
10. It is used in execution without being active in Authority Context.
    

---

# Conceptual rule

```text
Authority owns the Table.
Table stores authoritative structured data.
Lookup node defines how the Table is queried.
Fact records the selected result.
Report explains the lookup basis.
```