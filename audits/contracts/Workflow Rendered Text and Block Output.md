# Audit Contract: Workflow Rendered Text and Block Output

## Purpose

Verify that workflow initiation and node expansion produce clear, structured, user-facing rendered text in the center panel.

This contract covers rendered workflow text during:

1. workflow initiation
    
2. paragraph node expansion
    
3. equation node expansion/evaluation
    
4. composer active ask (not a center-panel scroll block)
    
5. workflow summary/completion output
    

This contract applies to every workflow, not only the pipe wall thickness workflow.

---

## Intended behavior

### 1. Workflow initiation output

When a workflow is initiated, the center panel shall render **one durable `workflow_intro` block** (`display_role: workflow_intro`, stable id `workflow-intro-{workflow_id}`).

Content comes from workflow runtime `texts` (title + description composed in the backend projection). Do not emit separate title and description scroll blocks.

The rendering layer shall not invent, infer, or hardcode workflow title or description.

Workflow introduction shall not expose raw workflow IDs or internal node IDs as primary visible text.

Expected initiation order:

```text
workflow_intro block
Initial guidance block, if applicable
```

Authority: `docs/desktopApp/center_panel_output_contract.md` §Lifecycle table, §Stable block_id rules.

**Implementation drift (Phase 2B):** some API paths/tests still use separate `title` display role — migration decision deferred.

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
audits/contracts/Equation Rendering.md
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

### 4. User-input waiting (composer-owned)

When the workflow is waiting for user input, the **composer** owns the active ask via `task_state.current_ask` (short prompt) and full messaging via `build_parameter_input_prompt()` / `active_prompt`.

The center-panel **scroll area shall not** render a separate generic waiting-user-input block.

After submission, durable Q/A may archive as `ask_archive` / `answer_archive` in `transcript_blocks` (transcript storage only — excluded from center-panel scroll).

Raw internal states such as `waiting_user_input`, `required_input`, `missing_parameter`, and raw `PARAM-*` ids shall not appear as primary user-facing text.

Authority: `docs/rules.md` §25; `docs/desktopApp/center_panel_output_contract.md` §Surfaces.

**Implementation drift (Phase 2B):** `api/output_blocks._input_waiting_blocks()` may still emit volatile `display_role: input_waiting` — not a permanent contract requirement.

---

### 5. Block grouping

All rendered center-panel content shall be grouped into explicit display blocks.

Expected block types include:

```text
workflow_intro block
paragraph block
equation block
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

Durable workflow-rendered content shall follow the center panel transcript contract and `docs/rules.md` §25.

**Append-only identity:** new durable blocks receive new `block_id`s; an existing durable block with the same `block_id` may update in place when it gains structured information. Prior durable blocks are never removed or duplicated on reload.

Previously rendered durable blocks shall not disappear when later nodes are expanded.

A previous durable block may be updated in place only when the same logical block gains additional structured information.

---

### 8. Deduplication behavior

The same logical content shall not appear twice as separate visible blocks for the same workflow execution state.

Examples of duplicates to prevent:

```text
same workflow_intro twice
same paragraph rendered twice
same equation rendered as both preview and durable block
composer ask duplicated as scroll waiting copy
same summary rendered twice
```

---

## Expected block lifecycle

### Workflow start

```text
workflow_intro block
Initial guidance block, if applicable
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
audits/contracts/Equation Rendering.md
```

### Waiting for user input

```text
Composer current_ask / active_prompt (not a scroll waiting block)
```

### After user input submitted

```text
Composer clears active ask
Optional ask_archive / answer_archive in transcript (not scroll)
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

1. Workflow initiation renders one durable `workflow_intro` block.
    
2. Workflow introduction content is retrieved only from workflow node runtime `texts`.
    
3. The rendering layer does not invent or hardcode workflow title or description.
    
4. Paragraph nodes with an output text field render paragraph blocks.
    
5. Paragraph nodes without an output text field do not create unnecessary center-panel output.
    
6. Paragraph blocks include the full paragraph reference path.
    
7. Paragraph blocks are linkable and open the paragraph node in the right panel tab.
    
8. Equation nodes render as equation blocks governed by `audits/contracts/Equation Rendering.md`.
    
9. Equation blocks follow `equation_display_trace` progressive layout per equation-rendering contract.
    
10. Waiting for input: composer owns `current_ask` — no generic center-panel waiting-user-input block.
    
11. Prompt copy is not extracted from parameter nodes into scroll waiting blocks.
    
12. Composer ask is separate from scroll narration blocks.
    
13. After input is submitted, composer does not show stale ask for resolved parameter.
    
14. Rendered text does not expose raw internal IDs as primary visible text.
    
15. Rendered text does not expose raw JSON or planner state.
    
16. Durable blocks remain visible after later node expansions.
    
17. Duplicate workflow_intro, paragraph, equation, or summary blocks are not rendered.
    
18. Blocks have clear display roles/types.
    

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
    
11. Is `current_ask` emitted when awaiting input (composer path)?
    
12. Is prompt copy sourced from messaging/PARAM (not scroll waiting blocks)?
    
13. Is the composer ask distinct from scroll narration blocks?
    
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

1. Does the frontend distinguish workflow_intro, paragraph, equation, and summary blocks?
    
2. Does the frontend render workflow title and description from backend-provided workflow-node data?
    
3. Does the frontend avoid fallback hardcoded workflow titles/descriptions?
    
4. Does paragraph output show the full reference path?
    
5. Does clicking the paragraph reference open the paragraph node in the right panel tab?
    
6. Does the frontend route equation blocks to the equation-rendering component?
    
7. Does the frontend preserve durable blocks after later node expansions?
    
8. Does the composer render current_ask without duplicating scroll waiting copy?
    
9. Does the frontend avoid rendering duplicate blocks with the same logical identity?
    
10. Does the frontend prevent raw JSON/state from appearing in the center panel?
    
11. Does the frontend avoid showing raw internal IDs as primary visible text?
    
12. Does the composer own the active ask (not the scroll area)?
    

---

## Required tests to locate or create

### Backend tests

Required coverage:

```text
Workflow started -> workflow_intro block emitted from workflow runtime texts
Workflow intro -> no renderer hardcoded fallback used
Paragraph node with output text field -> paragraph block emitted
Paragraph node without output text field -> no unnecessary output block
Paragraph block -> includes full reference path
Paragraph block -> includes link target for right panel node opening
Equation node expanded -> equation block emitted through equation-rendering pipeline
Awaiting input -> current_ask populated (composer); no scroll waiting block required
No raw internal IDs in rendered text
No raw JSON/planner state in rendered text
No duplicate block IDs for workflow_intro/paragraph/equation/summary
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
Center panel renders workflow_intro block
Center panel renders paragraph block when output text exists
Center panel does not render paragraph block when output text is absent
Paragraph block renders full reference path
Paragraph block click opens paragraph node in right panel tab
Center panel renders equation block using EquationOutput
Equation block follows audits/contracts/Equation Rendering.md behavior
Composer renders current_ask for awaiting input (scroll does not require waiting block)
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
3. Workflow runtime texts used for workflow_intro
4. Rendered workflow_intro text
5. Expanded paragraph node IDs
6. Paragraph output text field, if present
7. Paragraph text rendered, if any
8. Paragraph reference path rendered
9. Paragraph link target / right panel opening behavior
10. Equation blocks rendered
11. Composer current_ask when awaiting input
12. Whether composer ask clears after input
13. Screenshot or rendered output text
14. Tests proving the behavior
```

---

## Known workflow to audit first

### Pipe wall thickness workflow

Expected behavior:

1. Workflow starts.
    
2. User-friendly workflow introduction is rendered as one `workflow_intro` block from workflow runtime texts.
    
3. Paragraph nodes render only if they contain an output text field.
    
5. Paragraph blocks include the full paragraph reference path, such as:
    

```text
Reference: ASME B31.3 304.1.1
```

6. Paragraph references are linkable and open the paragraph node in the right panel tab.
    
7. Equation nodes render as equation blocks governed by:
    

```text
audits/contracts/Equation Rendering.md
```

8. When waiting for user input, composer owns `current_ask` (no scroll waiting block required).
    
9. Composer ask is separate from scroll narration.
    
10. Stale composer ask clears after user input.
    
11. Previous durable blocks remain visible.
    

---

## Known failure patterns to check

```text
workflow_intro missing
workflow_intro shown as raw workflow ID
workflow introduction hardcoded in rendering layer
duplicate title/description blocks instead of workflow_intro
paragraph text not rendered when output text field exists
paragraph text rendered from wrong field
paragraph reference path missing
paragraph reference path not linkable
paragraph click does not open node in right panel tab
too many internal paragraph nodes rendered as noise
equation rendered as generic text instead of equation block
equation block bypasses equation-rendering audit behavior
scroll waiting block required when composer has current_ask
composer ask duplicated in scroll waiting block
stale composer ask after input submitted
raw node IDs visible as primary text
raw JSON or planner state visible in center panel
previous durable text disappears after node expansion
same workflow_intro/paragraph/equation/summary rendered twice
```

---

## Open decisions

The following details should be confirmed before implementation changes:

1. Exact workflow runtime `texts` fields composed into `workflow_intro`.
    
2. Exact paragraph node field used as the output text field.
    
3. Exact paragraph reference path format.
    
4. Exact paragraph link payload required to open the node in the right panel tab.
    
5. Exact list of allowed block types/display roles (see `docs/desktopApp/center_panel_output_contract.md`).
    
6. Whether paragraph references/chips are required immediately or in a later phase.

**Closed (Phase 2A):**

- **Workflow introduction:** single durable `workflow_intro` block — not separate title/description scroll blocks.
- **User-input waiting:** composer `current_ask` only — no generic center-panel waiting-user-input block contract.
- **Waiting lifecycle:** composer clears active ask on submit; optional `ask_archive`/`answer_archive` in transcript only.
    


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
1. Render one durable workflow_intro block when workflow starts.
2. Retrieve workflow introduction only from workflow runtime texts.
3. Do not invent or hardcode workflow title or description in the rendering layer.
4. Render paragraph block when expanded paragraph node has an output text field.
5. Render full paragraph reference path in paragraph blocks.
6. Make paragraph blocks linkable so they open the paragraph node in the right panel tab.
7. Render equation nodes as equation blocks governed by audits/contracts/Equation Rendering.md.
8. Ensure equation blocks follow equation_display_trace layout per equation-rendering contract.
9. When awaiting input, populate composer current_ask — do not require center-panel waiting scroll block.
10. Preserve previous durable blocks after later node expansions.
11. Prevent duplicate visible blocks.
12. Do not expose raw internal IDs, raw JSON, or planner/debug state as primary center-panel text.
13. Use explicit block roles/types.

Before editing:
- Identify the failing tests or missing tests.

After editing:
- List files changed.
- Explain why each file changed.
- List tests added or updated.
- Run focused tests.
- Report remaining risks.
```