# Audit Contract: Workflow Rendered Text and Block Output

## Purpose

Verify that workflow initiation and node expansion produce clear, structured, user-facing rendered text in the center panel.

This contract covers rendered workflow text during:

1. workflow initiation
    
2. paragraph node expansion
    
3. equation node expansion/evaluation
    
4. user-input waiting states
    
5. workflow summary/completion output
    

This contract applies to every workflow, not only the pipe wall thickness workflow.

---

## Intended behavior

### 1. Workflow initiation output

When a workflow is initiated, the center panel shall render a workflow title block.

Each workflow node shall have a user-facing title and description.

The workflow title shall be gathered only from the workflow node.

The workflow description shall be gathered only from the workflow node.

The rendering layer shall not invent, infer, or hardcode the workflow title.

The rendering layer shall not invent, infer, or hardcode the workflow description.

The workflow title and description shall not expose raw workflow IDs or internal node IDs as primary visible text.

Expected initiation order:

```text
Title block
Workflow description block
Initial guidance block, if applicable
```

---

### 2. Paragraph node expansion output

When a paragraph node is expanded, the system shall determine whether that paragraph node has an output text field.

If the paragraph node has an output text field, that text shall be rendered in the center panel as a paragraph block.

The rendered text shall be extracted from the paragraph node output text field.

The rendering layer shall not invent or hardcode paragraph text.

The paragraph block shall include a link to the paragraph node.

Clicking the paragraph link shall open the paragraph node in the right panel tab.

The paragraph block shall include the full reference path to the paragraph node.

Example reference format:

```text
Reference: ASME B31.3 §304.1.1
```

Paragraph output shall not expose raw internal node IDs as primary visible text.

Paragraph nodes without an output text field shall not create center-panel output.

---

### 3. Equation node output

When an equation node is visited, expanded, or evaluated, an equation block shall be rendered in the center panel.

Equation node output shall follow the separate equation-rendering audit contract:

```text
audits/equation-rendering.md
```

The equation rendering audit defines the complete equation block behavior, including:

```text
raw symbolic equation
substituted equation
final evaluated result
equation parameter table
parameter source/provenance
equation deduplication
equation append-only behavior
```

The workflow rendered-text pipeline shall only ensure that equation nodes are routed into the equation block pipeline.

Equation nodes shall not be rendered as generic paragraph text.

Equation blocks shall not duplicate live preview or durable equation trace blocks.

---

### 4. Temporary user-input waiting text

When the workflow is waiting for user input, the center panel may render a temporary waiting-user-input block.

This block shall use generic user-facing temporary wording.

This block shall not extract text from the parameter node.

This temporary center-panel waiting text is separate from the input control text shown at the bottom of the central panel.

The temporary waiting text shall not display raw internal states such as:

```text
waiting_user_input
required_input
missing_parameter
PARAM-*
```

The temporary waiting text shall be removed once the input is provided.

It shall not remain as stale guidance after the parameter is resolved.

---

### 5. Block grouping

All rendered center-panel content shall be grouped into explicit display blocks.

Expected block types include:

```text
title block
workflow description block
paragraph block
equation block
input waiting block
summary block
reference block
warning block
```

Blocks shall have stable identities where they represent durable workflow history.

Temporary blocks shall be clearly identifiable as temporary and shall not be persisted as stale transcript history after resolution.

---

### 6. Node expansion behavior

When a node is expanded, rendered output shall be created only if that node has user-facing content or produces user-facing results.

Not every internal node expansion must produce center-panel text.

The renderer shall not output planner/debug information, raw JSON, raw state, raw node payloads, or internal traversal details in the center panel.

Node expansion output shall be based on node content and structured execution results, not renderer-local hardcoded text.

---

### 7. Append-only behavior

Durable workflow-rendered content shall follow the center panel transcript contract.

Previously rendered durable blocks shall not disappear when later nodes are expanded.

A previous durable block may be updated in place only when the same logical block gains additional structured information.

Temporary waiting blocks may be removed or replaced after they are resolved.

---

### 8. Deduplication behavior

The same logical content shall not appear twice as separate visible blocks for the same workflow execution state.

Examples of duplicates to prevent:

```text
same workflow title rendered twice
same workflow description rendered twice
same paragraph rendered twice
same equation rendered as both preview and durable block
same waiting text remaining after answer is submitted
same summary rendered twice
```

---

## Expected block lifecycle

### Workflow start

```text
Title block
Workflow description block
Initial guidance block, if applicable
First temporary waiting-user-input block, if applicable
```

### Paragraph node expanded

```text
Paragraph block, only if paragraph has output text field
Paragraph reference node link 
References / chips, if available
```

### Equation node expanded

```text
Equation block
```

Equation block details are governed by:

```text
audits/equation-rendering.md
```

### Waiting for user input

```text
Temporary waiting-user-input block
Bottom input control prompt remains separate
```

### After user input submitted

```text
Temporary waiting-user-input block removed or resolved
Answer may be archived separately if required by transcript contract
Next node expansion output rendered
```

### Workflow completion

```text
Summary block
Final result block, if applicable
References block, if applicable
Next workflow suggestions, if applicable
```

---

## Acceptance rules

This contract is satisfied only if all of the following are true:

1. Workflow initiation renders a title block.
    
2. Workflow title is retrieved only from the workflow node.
    
3. Workflow initiation renders the workflow description block.
    
4. Workflow description is retrieved only from the workflow node.
    
5. The rendering layer does not invent or hardcode workflow title or description.
    
6. Paragraph nodes with an output text field render paragraph blocks.
    
7. Paragraph nodes without an output text field do not create unnecessary center-panel output.
    
8. Paragraph blocks include the full paragraph reference path.
    
9. Paragraph blocks are linkable and open the paragraph node in the right panel tab.
    
10. Equation nodes render as equation blocks governed by `audits/equation-rendering.md`.
    
11. Equation blocks include the equation parameter table as defined in the equation-rendering audit.
    
12. Waiting for input renders only a generic temporary waiting-user-input block.
    
13. Temporary waiting-user-input text is not extracted from the parameter node.
    
14. Temporary waiting-user-input text in the center panel is separate from the bottom input prompt.
    
15. Temporary waiting-user-input text does not remain stale after input is submitted.
    
16. Rendered text does not expose raw internal IDs as primary visible text.
    
17. Rendered text does not expose raw JSON or planner state.
    
18. Durable blocks remain visible after later node expansions.
    
19. Duplicate title, description, paragraph, equation, waiting, or summary blocks are not rendered.
    
20. Blocks have clear display roles/types.
    

---

## Backend audit questions

Check whether the backend creates structured display blocks from workflow execution state.

Potential risk areas:

```text
workflow node loading
paragraph node expansion
equation output generation
api/output_blocks.py
api/serializers.py
flow_guidance builders
execution trace generation
display block normalization
```

Audit questions:

1. Does every workflow node have a user-facing title?
    
2. Does every workflow node have a user-facing description?
    
3. Is the workflow title taken only from the workflow node?
    
4. Is the workflow description taken only from the workflow node?
    
5. Can the rendering layer invent or hardcode workflow titles/descriptions anywhere?
    
6. Which paragraph node field is the output text field?
    
7. Are paragraph blocks emitted only when the paragraph has an output text field?
    
8. Does the paragraph block include the full paragraph reference path?
    
9. Does the paragraph block include link metadata for opening the paragraph node in the right panel?
    
10. Are equation blocks emitted through the equation-rendering pipeline?
    
11. Is generic temporary waiting-user-input text emitted when waiting for input?
    
12. Is temporary waiting text independent from parameter node text?
    
13. Is the temporary waiting text distinct from the bottom input prompt?
    
14. Are block roles/types explicit and stable?
    
15. Are block IDs stable enough to prevent duplicates?
    
16. Can raw node IDs, raw planner state, or raw JSON leak into rendered output?
    

---

## Frontend audit questions

Check whether the frontend renders structured blocks correctly and does not flatten everything into generic text.

Potential risk areas:

```text
center panel transcript builder
workflow history rendering
block merge/dedup logic
TitleOutput component
WorkflowDescriptionOutput component
ParagraphOutput component
EquationOutput component
SummaryOutput component
input prompt rendering
temporary block handling
right panel node opening behavior
reference chip rendering
```

Audit questions:

1. Does the frontend distinguish title, workflow description, paragraph, equation, input waiting, and summary blocks?
    
2. Does the frontend render workflow title and description from backend-provided workflow-node data?
    
3. Does the frontend avoid fallback hardcoded workflow titles/descriptions?
    
4. Does paragraph output show the full reference path?
    
5. Does clicking the paragraph reference open the paragraph node in the right panel tab?
    
6. Does the frontend route equation blocks to the equation-rendering component?
    
7. Does the frontend preserve durable blocks after later node expansions?
    
8. Does the frontend remove or replace temporary waiting blocks after resolution?
    
9. Does the frontend avoid rendering duplicate blocks with the same logical identity?
    
10. Does the frontend prevent raw JSON/state from appearing in the center panel?
    
11. Does the frontend avoid showing raw internal IDs as primary visible text?
    
12. Does the bottom input prompt remain separate from center-panel temporary waiting text?
    

---

## Required tests to locate or create

### Backend tests

Required coverage:

```text
Workflow started -> title block emitted from workflow node
Workflow started -> description block emitted from workflow node
Workflow title/description -> no renderer hardcoded fallback used
Paragraph node with output text field -> paragraph block emitted
Paragraph node without output text field -> no unnecessary output block
Paragraph block -> includes full reference path
Paragraph block -> includes link target for right panel node opening
Equation node expanded -> equation block emitted through equation-rendering pipeline
Waiting for input -> generic temporary waiting-user-input block emitted
Waiting for input -> temporary text not extracted from parameter node
Input submitted -> temporary waiting-user-input block does not remain stale
No raw internal IDs in rendered text
No raw JSON/planner state in rendered text
No duplicate block IDs for title/description/paragraph/equation/summary
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
Center panel renders title block
Center panel renders workflow description block
Center panel renders paragraph block when output text exists
Center panel does not render paragraph block when output text is absent
Paragraph block renders full reference path
Paragraph block click opens paragraph node in right panel tab
Center panel renders equation block using EquationOutput
Equation block follows audits/equation-rendering.md behavior
Center panel renders temporary waiting-user-input block separately from bottom input prompt
Center panel removes or updates stale temporary waiting block after input
Center panel preserves previous durable blocks after node expansion
Center panel does not duplicate same logical block
Center panel does not render raw JSON
Center panel does not render raw internal IDs as primary text
```

Suggested test locations:

```text
desktopApp/dev/desktop_ui/tests/
```

---

## Evidence required during audit

For each audited workflow, capture:

```text
1. Workflow name
2. Workflow node ID
3. Workflow node title field
4. Workflow node description field
5. Rendered title text
6. Rendered workflow description text
7. Expanded paragraph node IDs
8. Paragraph output text field, if present
9. Paragraph text rendered, if any
10. Paragraph reference path rendered
11. Paragraph link target / right panel opening behavior
12. Equation blocks rendered
13. Temporary waiting-user-input text rendered
14. Whether bottom input prompt is separate
15. Whether stale waiting text disappears after input
16. Screenshot or rendered output text
17. Tests proving the behavior
```

---

## Known workflow to audit first

### Pipe wall thickness workflow

Expected behavior:

1. Workflow starts.
    
2. User-friendly workflow title is rendered from the workflow node.
    
3. Workflow description is extracted from the workflow node and rendered.
    
4. Paragraph nodes render only if they contain an output text field.
    
5. Paragraph blocks include the full paragraph reference path, such as:
    

```text
Reference: ASME B31.3 304.1.1
```

6. Paragraph references are linkable and open the paragraph node in the right panel tab.
    
7. Equation nodes render as equation blocks governed by:
    

```text
audits/equation-rendering.md
```

8. When waiting for user input, a generic temporary waiting-user-input block is rendered.
    
9. Bottom input prompt remains separate from the center-panel waiting text.
    
10. Stale temporary waiting text is removed or updated after user input.
    
11. Previous durable blocks remain visible.
    

---

## Known failure patterns to check

```text
workflow title missing
workflow title shown as raw workflow ID
workflow title hardcoded in rendering layer
workflow description missing
workflow description hardcoded in rendering layer
workflow description not sourced from workflow node
paragraph text not rendered when output text field exists
paragraph text rendered from wrong field
paragraph reference path missing
paragraph reference path not linkable
paragraph click does not open node in right panel tab
too many internal paragraph nodes rendered as noise
equation rendered as generic text instead of equation block
equation block bypasses equation-rendering audit behavior
temporary waiting text extracted from parameter node
temporary waiting text duplicated with bottom input prompt
temporary waiting text remains after input is submitted
raw node IDs visible as primary text
raw JSON or planner state visible in center panel
previous durable text disappears after node expansion
same title/description/paragraph/equation/summary rendered twice
```

---

## Open decisions

The following details should be confirmed before implementation changes:

1. Exact workflow node field used for user-facing workflow title.
    
2. Exact workflow node field used for workflow description.
    
3. Exact paragraph node field used as the output text field.
    
4. Exact paragraph reference path format.
    
5. Exact paragraph link payload required to open the node in the right panel tab.
    
6. Exact generic wording for temporary waiting-user-input blocks.
    
7. Exact lifecycle rule for temporary waiting blocks: remove completely, mark resolved, or archive.
    
8. Exact list of allowed block types/display roles.
    
9. Whether workflow description is durable transcript history or only session introduction.
    
10. Whether paragraph references/chips are required immediately or in a later phase.
    


---

## Cursor implementation prompt

Use this only after the audit is reviewed:

```text
Implement only the smallest changes required to satisfy audits/workflow-rendered-text.md.

Scope:
- Workflow rendered text and center-panel block output only.
- Do not modify unrelated workflows.
- Do not edit node/workflow source data unless you first prove the rendering contract cannot be satisfied without doing so.
- Do not change global app behavior outside center-panel rendered workflow output.

Required behavior:
1. Render workflow title block when workflow starts.
2. Retrieve workflow title only from workflow node data.
3. Render workflow description from workflow node data.
4. Do not invent or hardcode workflow title or description in the rendering layer.
5. Render paragraph block when expanded paragraph node has an output text field.
6. Render full paragraph reference path in paragraph blocks.
7. Make paragraph blocks linkable so they open the paragraph node in the right panel tab.
8. Render equation nodes as equation blocks governed by audits/equation-rendering.md.
9. Ensure equation block includes the equation parameter table defined in audits/equation-rendering.md.
10. Render a generic temporary center-panel waiting-user-input block when waiting for user input.
11. Do not extract temporary waiting text from parameter nodes.
12. Keep temporary center-panel waiting text separate from the bottom input prompt.
13. Remove, replace, or resolve temporary waiting text after input is submitted.
14. Preserve previous durable blocks after later node expansions.
15. Prevent duplicate visible blocks.
16. Do not expose raw internal IDs, raw JSON, or planner/debug state as primary center-panel text.
17. Use explicit block roles/types.

Before editing:
- Identify the failing tests or missing tests.

After editing:
- List files changed.
- Explain why each file changed.
- List tests added or updated.
- Run focused tests.
- Report remaining risks.
```