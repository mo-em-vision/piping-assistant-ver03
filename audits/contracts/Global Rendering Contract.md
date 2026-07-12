# Global Rendering Contract

## Purpose

Define the non-negotiable rendering rules for all workflow output shown to the user.

This contract applies to all center-panel rendered output, including:

1. workflow initiation output
    
2. paragraph output
    
3. equation output
    
4. input waiting output
    
5. summary output
    
6. report/transcript output
    
7. future table/lookup output
    

All specific rendering audits shall follow this global contract.

---

## Core principles

### 1. All visible output shall be structured blocks

The center panel shall render structured display blocks.

The rendering layer shall not output loose, untyped text as primary workflow output.

Allowed block categories include:

```text
title block
workflow description block
paragraph block
equation block
input waiting block
summary block
reference block
warning block
future table / lookup block
```

Each block shall have an explicit display role/type.

---

### 2. Durable output shall be append-only

Durable workflow history shall not disappear when later workflow steps occur.

Previously rendered durable blocks shall remain visible after:

```text
node expansion
user input submission
equation evaluation
lookup resolution
workflow completion
task reload
```

A durable block may be updated in place only when the same logical block gains additional information.

Examples:

```text
equation block gains substitution
equation block gains final result
paragraph block gains reference metadata
summary block gains final status
```

A durable block shall not be replaced by a separate duplicate block.

---

### 3. Temporary output shall not become stale history

Temporary blocks may be shown while the workflow is waiting or resolving.

Examples:

```text
temporary input waiting block
temporary preview block
temporary progress block
```

Temporary blocks shall be clearly identifiable as temporary.

Temporary blocks shall be removed, replaced, or resolved when their condition is no longer true.

Temporary waiting blocks shall not remain visible after the related input has been submitted.

Temporary preview blocks shall not duplicate durable evaluated blocks.

---

### 4. Stable block identity is required

Every durable block shall have a stable logical identity.

The same logical content shall use the same stable block identity across updates.

Examples:

```text
workflow title -> one stable title block
workflow description -> one stable description block
paragraph node output -> one stable paragraph block per paragraph node
equation node output -> one stable equation block per equation node / equation execution context
summary -> one stable summary block
```

The system shall not create a new visible block when an existing logical block should be updated.

---

### 5. No duplicate visible content

The same logical content shall not appear twice in the center panel.

Duplicate patterns to prevent:

```text
same workflow title twice
same workflow description twice
same paragraph text twice
same equation rendered as both preview and durable trace
same temporary waiting text after input is resolved
same summary twice
same result shown through two competing pipelines
```

Deduplication shall be based on stable block identity and logical content, not only string comparison.

---

### 6. Rendering layer shall not invent engineering content

The rendering layer shall not invent, infer, or hardcode engineering content.

This includes:

```text
workflow titles
workflow descriptions
paragraph text
equation labels
equation descriptions
parameter names
parameter descriptions
standard references
lookup/table references
engineering conclusions
```

Engineering content shall come from canonical structured sources such as:

```text
workflow nodes
paragraph nodes
equation nodes
parameter nodes
lookup/table nodes
execution trace
validated calculation results
```

The frontend may format and arrange content, but it shall not create engineering meaning.

---

### 7. Backend owns structured data; frontend renders it

The backend shall provide structured display data.

The frontend shall render the structured data without reconstructing engineering logic.

The frontend may handle:

```text
layout
ordering
styling
expansion/collapse behavior
click behavior
KaTeX rendering
link rendering
deduplication safety
```

The frontend shall not independently determine:

```text
which engineering equation applies
which paragraph is required
which parameter source is authoritative
which standard reference applies
which engineering conclusion is valid
```

---

### 8. Raw internal data shall not be primary visible text

Rendered workflow output shall not expose raw internal implementation details as primary visible text.

Forbidden as primary user-facing output:

```text
raw node IDs
raw workflow IDs
raw PARAM-* IDs
raw planner state
raw JSON
raw serialized task state
waiting_user_input
required_input
missing_parameter
internal display roles
debug-only keys
```

Internal IDs may exist in hidden metadata or developer/debug panels, but not as primary center-panel text.

---

### 9. Debug output shall be separated from user output

Planner state, task state, traversal state, and raw JSON belong only in developer/debug views.

They shall not leak into the center panel.

Developer/debug views shall also prefer human-readable summaries over raw JSON unless raw JSON is explicitly requested.

---

### 10. References shall be structured and linkable where possible

References to standards, paragraphs, equations, and future lookup tables shall be represented as structured reference metadata.

Where possible, rendered references shall be linkable **inline within the citing sentence** — not as detached chip controls or a separate generic link beside duplicated citation text.

Reference examples:

```text
ASME B31.3 304.1.1
ASME B31.3 Eq. 3a
ASME B31.3 Table A-1
```

Example composition:

```text
Resolved from ASME B31.3 Table A-1
```

Only `ASME B31.3 Table A-1` shall be clickable; the prefix `Resolved from` shall remain plain text.

Clicking a reference shall open the relevant node or source in the appropriate panel where supported.

References shall not be rendered only as raw internal IDs.

References shall use full standard-path labels where resolvable. Generic `"Standard reference"` is allowed only when the target cannot be resolved.

This rule applies to center-panel output, right-panel standards prose, and chat assistant messages.

---

### 11. Output ordering shall be deterministic

Rendering order shall be deterministic for the same workflow state.

The same input state shall produce the same ordered output blocks.

Ordering shall not depend on unstable object iteration, incidental traversal order, or frontend merge side effects.

Each specific audit may define its own block order.

---

### 12. Workflow reload shall preserve durable history

Reloading or refreshing the task state shall not duplicate durable blocks.

Reloading or refreshing the task state shall not remove durable blocks.

Reloading or refreshing shall preserve the same visible workflow history for the same execution state.

---

### 13. Report output shall use the same durable source where possible

Report preview and final report generation shall use the same durable structured workflow output where possible.

The report layer shall not recreate a separate ad-hoc version of workflow history that can diverge from the center panel.

If report-specific formatting is required, it shall transform the same structured blocks rather than inventing separate content.

---

## Required block metadata

Each durable block should provide enough metadata to support:

```text
stable identity
display role/type
rendering order
source node ID, where applicable
source workflow ID, where applicable
source equation ID, where applicable
source paragraph ID, where applicable
temporary vs durable status
reference metadata, where applicable
```

Minimum expected fields:

```text
block_id
display_role
content/type payload
source/provenance metadata
is_temporary or equivalent lifecycle marker
```

Exact field names may vary, but the meaning must be represented.

---

## Acceptance rules

This global contract is satisfied only if all of the following are true:

1. Center-panel output is rendered as structured blocks.
    
2. Durable blocks remain visible after later workflow steps.
    
3. Durable blocks use stable logical identity.
    
4. Temporary blocks do not remain stale after resolution.
    
5. Same logical content is not duplicated.
    
6. Rendering layer does not invent engineering content.
    
7. Backend provides structured engineering display data.
    
8. Frontend renders structured data without reconstructing engineering logic.
    
9. Raw internal IDs, raw JSON, and internal states are not primary visible text.
    
10. Debug output is separated from user-facing workflow output.
    
11. References are structured and linkable where possible.
    
12. Output ordering is deterministic.
    
13. Reloading task state does not duplicate or remove durable history.
    
14. Report output does not diverge from center-panel durable workflow output.
    

---

## Required tests to locate or create

### Backend tests

Required backend coverage:

```text
Display output blocks have explicit display roles
Durable blocks have stable block IDs
Same logical block updates in place instead of duplicating
Temporary waiting block is removed/resolved after input submission
Raw internal IDs are not primary display text
Raw waiting_user_input does not appear in user-facing output
Workflow reload does not duplicate durable blocks
Workflow reload does not remove durable blocks
Structured references are emitted where applicable
```

Suggested locations:

```text
tests/api/
tests/workflow/
tests/mvp/
```

---

### Frontend tests

Required frontend coverage:

```text
Center panel renders blocks by display role/type
Center panel preserves durable blocks after later updates
Center panel updates same block instead of appending duplicate
Center panel removes/resolves temporary waiting block
Center panel does not render raw JSON
Center panel does not render raw internal IDs as primary text
Center panel keeps output order deterministic
Reference click opens linked node/source where supported
```

Suggested locations:

```text
desktopApp/dev/desktop_ui/tests/
```

---

## Evidence required during audit

For each specific rendering audit, capture:

```text
1. Workflow tested
2. Step/state tested
3. Blocks emitted by backend
4. Blocks rendered by frontend
5. Block IDs
6. Display roles/types
7. Temporary vs durable status
8. Source/provenance metadata
9. Rendered visible text
10. Duplicates found, if any
11. Raw internal text leaked, if any
12. Tests proving behavior
```

---

## Known risk areas

Shared areas likely to affect multiple rendering contracts:

```text
api/output_blocks.py
api/serializers.py
flow_guidance builders
execution trace generation
display block normalization
center panel transcript builder
block merge/dedup logic
EquationOutput component
ParagraphOutput component
Workflow history rendering
task state serialization
report generation
```

Any change to these areas shall be treated as high-risk and shall require nearby regression tests.

---

## Implementation rules for Cursor

Cursor shall not implement changes directly from this global contract.

Cursor shall first audit a specific contract and identify:

```text
violations
files involved
missing tests
smallest safe fix areas
shared files affected
regression tests required
```

Only after the audit is reviewed should Cursor implement changes.

Cursor shall not modify:

```text
rules files
audit files
node files
documentation files
workflow source files
standard source files
```

unless explicitly instructed or unless it proves the contract cannot be satisfied without doing so.

---

## Standard Cursor implementation prompt

```text
Implement only the smallest changes required to satisfy the reviewed audit.

Scope:
- Use the specific contract as the implementation target.
- Respect audits/contracts/global-rendering-contract.md.
- Do not change unrelated behavior.
- Do not edit node/workflow/standard source files unless explicitly approved.
- Do not invent engineering content in the rendering layer.

Before editing:
1. Identify the failing tests or missing tests.
2. Add focused failing tests where practical.
3. State which shared files will be touched and why.

After editing:
1. List files changed.
2. Explain why each file changed.
3. List tests added or updated.
4. Run focused tests.
5. Run nearby regression tests.
6. Report remaining risks.
7. Report any files touched outside scope.
```