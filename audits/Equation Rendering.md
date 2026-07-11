# Audit Contract: Equation Rendering

## Purpose

Verify that equation nodes are rendered consistently, progressively, and with clear parameter provenance during workflow execution.

This contract applies to every workflow that evaluates engineering equations, not only the pipe wall thickness workflow.

---

## Intended behavior

### 1. Raw equation rendering

When an equation node is visited, the raw symbolic equation shall be rendered in the center panel.

The raw equation shall appear before all related parameter values are available.

The rendered equation shall be human-readable and formatted using KaTeX/LaTeX where applicable.

The equation display shall not expose internal node IDs as the primary visible text.

---

### 2. Progressive equation rendering

When an equation node is first visited and not all parameters are available, the display shall show:

```text
Raw symbolic equation
Unresolved parameter/request state, if applicable
```

The unresolved state shall use user-friendly wording.

Raw internal values such as `waiting_user_input` shall not be displayed.

---

### 3. Solved equation rendering

Once all required parameters for the equation are available, the equation display shall update to show:

```text
Raw symbolic equation
Substituted equation
Final evaluated result
Parameter table
References / chips, if available
```

The parameter table shall move beneath the final evaluated result once the equation is solved.

The raw symbolic equation shall remain visible after substitution and evaluation.

The substituted equation shall show actual values inserted into the equation.

The final result shall be shown clearly, including units where applicable.

---

## Parameter table rendering

When the equation is solved, the related parameter table shall be rendered beneath the final evaluated result.

The table shall use parameter metadata from parameter nodes only.

Parameter names, symbols, labels, and descriptions shall not be invented or hardcoded in the rendering layer.

The table shall include:

|Column|Requirement|
|---|---|
|Parameter|Parameter name or symbol retrieved from the relevant parameter node|
|Description|Description field retrieved from the relevant parameter node|
|Value|Current resolved value or evaluated value|
|Unit|Engineering unit, if applicable|
|Source|User input, lookup table, default, or equation reference/provenance|

### Source column rules

If the value was entered by the user, the Source column shall indicate user input.

If the value was looked up from a table, the Source column shall state the table name and make the table reference linkable where possible.

Example:

```text
Derived from ASME B31.3 Table A-1
```

If the parameter value is defined or calculated in another equation, the Source column shall state the equation reference and make the equation reference linkable where possible.

Example:

```text
Defined in ASME B31.3 Eq. 3a
```

Unresolved values shall not remain in the final solved parameter table.

Raw internal states such as `waiting_user_input` shall not be displayed.

---

## Dependency behavior

If an equation depends on a parameter calculated by another equation node, the upstream equation shall be evaluated first.

The dependent equation shall not be evaluated until the upstream equation result is available.

After the upstream equation is evaluated, the dependent equation parameter table shall show:

```text
Resolved value
Unit
Source equation reference
```

The source equation reference shall be shown in the Source column.

The dependent equation must not permanently show unresolved placeholders after the upstream equation has been evaluated.

---

## Append-only behavior

Equation rendering shall follow the center panel transcript contract.

Previously rendered equations shall not disappear when later nodes are visited.

A previously rendered equation may be updated in place to add substitution, evaluation, result, or provenance.

A previously rendered equation shall not be replaced by a separate duplicate block.

---

## Deduplication behavior

The same equation shall not appear twice as separate visible blocks for the same workflow execution state.

Live preview blocks and durable evaluated equation blocks must not render duplicate visible equations.

If the same equation block is updated, it shall use the same stable block identity.

---

## Acceptance rules

The equation rendering contract is satisfied only if all of the following are true:

1. Visiting an equation node renders the raw symbolic equation.
    
2. Before the equation is solved, unresolved parameter/request state is shown using user-friendly wording.
    
3. Once parameters are available, substitution appears beneath the raw equation.
    
4. Final evaluated result appears beneath the substituted equation.
    
5. Parameter table appears beneath the final evaluated result after the equation is solved.
    
6. Parameter names are retrieved from parameter nodes only.
    
7. Parameter descriptions are retrieved from parameter nodes only.
    
8. Lookup-derived values show the linked lookup table in the Source column where possible.
    
9. Equation-derived values show the linked source equation in the Source column where possible.
    
10. Equations depending on other equations wait for the upstream equation result.
    
11. No solved equation displays `waiting_user_input`, raw internal IDs, or unresolved placeholders.
    
12. Earlier equations remain visible after later equations are visited.
    
13. The same equation is not duplicated in the center panel.
    

---

## Expected rendering order

### Before equation is solved

```text
Equation title / friendly label
Raw symbolic equation
Current unresolved state / next required parameter prompt
References / chips, if available
```

### After equation is solved

```text
Equation title / friendly label
Raw symbolic equation
Substituted equation
Final evaluated result
Parameter table
References / chips, if available
```

---

## Known risk areas to audit

### Backend

Check whether equation display data is produced from one canonical source.

Potential risk areas:

```text
api/output_blocks.py
api/serializers.py
presentation / flow_guidance builders
execution trace generation
equation result serialization
parameter resolution / provenance logic
lookup-table resolution logic
parameter node metadata loading
```

Audit questions:

1. Is raw equation text available immediately when the equation node is visited?
    
2. Is unresolved parameter state represented using user-facing display data?
    
3. Is substitution generated from evaluated values, not manually hardcoded?
    
4. Is final result generated from the same evaluated equation trace?
    
5. Is parameter node metadata available to the equation renderer?
    
6. Are parameter names and descriptions retrieved from parameter nodes only?
    
7. Is lookup-table provenance represented in structured data?
    
8. Is equation-derived provenance represented in structured data?
    
9. Are lookup table references linkable?
    
10. Are source equation references linkable?
    
11. Is block identity stable across unresolved → resolved → evaluated states?
    
12. Are preview and durable equation traces deduplicated?
    

---

### Frontend

Check whether equation blocks are rendered progressively without duplication or disappearance.

Potential risk areas:

```text
EquationOutput component
center panel transcript builder
display output merge logic
parameter table component
KaTeX rendering component
workflow history rendering
reference chip rendering
```

Audit questions:

1. Does the frontend render raw equation immediately when the equation node is visited?
    
2. Does the frontend render substitution and result only when values are available?
    
3. Does the frontend place the parameter table beneath the final result when solved?
    
4. Does the frontend preserve previous equation blocks?
    
5. Does it update an existing block instead of appending a duplicate?
    
6. Does it hide raw internal values from the user?
    
7. Does it show lookup-table provenance in the Source column?
    
8. Does it show equation-derived provenance in the Source column?
    
9. Does it make table and equation references linkable where possible?
    

---

## Relevant tests to locate or create

### Backend tests

Required coverage:

```text
Equation node visited -> raw equation block emitted
Equation unresolved -> user-friendly unresolved state emitted
Equation parameters resolved -> substitution emitted
Equation parameters resolved -> final result emitted
Equation solved -> parameter table emitted after final result
Parameter table -> names retrieved from parameter nodes
Parameter table -> descriptions retrieved from parameter nodes
Lookup-derived parameter -> source table provenance emitted
Equation-derived parameter -> source equation provenance emitted
Dependent equation -> upstream equation evaluated first
No raw waiting_user_input in final evaluated equation block
No duplicate equation blocks for same equation_id
```

Suggested test locations:

```text
tests/api/
tests/workflow/
tests/graph/
tests/mvp/
```

---

### Frontend tests

Required coverage:

```text
EquationOutput renders symbolic equation
EquationOutput renders substitution after values resolve
EquationOutput renders final result
EquationOutput renders parameter table beneath final result
EquationOutput renders parameter description from parameter node metadata
EquationOutput renders lookup-table provenance in Source column
EquationOutput renders equation-derived provenance in Source column
EquationOutput renders linkable table/equation references where available
Center panel keeps previous equations visible
Center panel does not duplicate same equation block
Center panel does not render raw internal IDs as primary text
Center panel does not render waiting_user_input
```

Suggested test locations:

```text
tests/presentation/equation/
```

---

## Evidence required during audit

For each checked workflow, capture:

```text
1. Workflow name
2. Equation node ID
3. Raw equation rendered
4. Substitution rendered
5. Final result rendered
6. Parameter table rendered beneath final result
7. Parameter names retrieved from parameter nodes
8. Parameter descriptions retrieved from parameter nodes
9. Lookup-derived parameters, if any
10. Equation-derived parameters, if any
11. Source/provenance shown for each derived parameter
12. Linkability of table/equation references
13. Screenshot or rendered output text
14. Test file proving the behavior
```

---

## Current status

Status: Not yet audited.

Known user requirement:

The pipe wall thickness workflow must show equation substitution and evaluation for all evaluated equations, including equations such as `t` and `t_m`.

Known failure patterns to check:

```text
previous equations disappearing
same equation rendered twice
only some equations showing substitution
parameter table shown in the wrong position after equation is solved
dependent parameter showing waiting_user_input after evaluation
raw internal IDs shown in visible output
preview equation duplicating durable equation trace
parameter names hardcoded in rendering layer
parameter descriptions missing or hardcoded
lookup source not shown or not linkable
equation-derived source not shown or not linkable
```

---

## Open decisions

The following details are not yet fixed and should be decided before implementation changes:

1. Exact wording for user-input source values.
    
2. Exact wording for unresolved parameter states before the equation is solved.
    
3. Exact wording for lookup-derived values, such as `Derived from ASME B31.3 Table A-1`.
    
4. Exact wording for equation-derived values, such as `Defined in ASME B31.3 Eq. 3a`.
    
5. Whether equation references use equation labels, node titles, or reference chips.
    
6. Whether substitution is generated backend-side, frontend-side, or from a shared structured equation trace.
    
