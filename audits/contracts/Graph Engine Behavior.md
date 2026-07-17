# Audit Contract: Graph Engine Behavior

## Purpose

Verify that the graph engine expands workflow nodes correctly, deterministically, and with enough structured traversal history to reproduce the workflow later in developer tools and graph visualizers.

This contract covers:

1. workflow root discovery
    
2. node expansion
    
3. branch selection
    
4. parameter collection
    
5. equation dependency ordering
    
6. queued/excluded traversal state
    
7. traversal replay
    
8. traversal performance
    
9. output handoff to the rendering pipeline
    

This contract applies to every workflow, not only the pipe wall thickness workflow.

---

## Relationship to other contracts

The graph engine shall not directly control final visual rendering.

It shall provide structured traversal and execution state that downstream rendering contracts consume.

Related contracts:

```text
audits/contracts/Global Rendering Contract.md
audits/contracts/Workflow Rendered Text and Block Output.md
audits/contracts/Equation Rendering.md
```

The graph engine is responsible for deciding:

```text
current node
visited nodes
queued nodes
queue reasons
excluded nodes
exclusion reasons
completed nodes
traversal path
execution events
```

The rendering pipeline is responsible for converting structured graph/execution state into user-facing blocks.

---

## Source file boundary

Workflow definitions live under:

```text
workflows/{machine-key}.yaml
```

The graph engine audit shall not require edits to files under `workflows/` unless the audit proves that the current workflow source data is missing required metadata.

Generic graph engine behavior shall not be fixed by hardcoding workflow-specific logic.

---

## Intended behavior

### 1. Workflow root discovery

When a workflow is initiated, the graph engine shall identify the correct workflow root.

Root discovery shall be deterministic.

If the user explicitly selects a workflow, the engine shall not discover unrelated workflows.

If a workflow slug or ID is unknown, the engine shall not silently return all workflows as valid candidates.

Raw workflow IDs may be used internally, but user-facing workflow title and description shall come from the workflow node, as defined in:

```text
audits/contracts/Workflow Rendered Text and Block Output.md
```

---

### 2. Node expansion

When a node is expanded, the graph engine shall evaluate only relevant outgoing edges.

The engine shall not expand unrelated branches.

The engine shall record why each next node was selected, queued, or excluded.

Node expansion state shall be structured enough to support developer inspection without raw JSON tables.

Expected node states:

```text
current
visited_this_step
visited_total
queued
excluded
completed
```

The engine shall not maintain a separate blocked-node category unless there is a proven technical reason.

Waiting, blocked, or dependency-delayed nodes shall be represented as queued nodes with explicit queue reasons.

---

### 3. Traversal queue model

The graph engine shall use a unified queued-node model.

A queued node is any node selected for future processing but not currently expanded.

Queued nodes shall include an explicit queue reason.

Allowed queue reasons include:

```text
ready_for_expansion
waiting_for_user_input
waiting_for_upstream_equation
waiting_for_lookup_result
waiting_for_dependency
branch_condition_pending
```

A queued node shall include enough metadata to explain:

```text
why it is queued
what dependency or event is required
what will allow it to proceed
```

Examples:

```text
Node eq-2a -> queued -> waiting_for_upstream_equation
Node PARAM-corrosion_allowance -> queued -> waiting_for_user_input
Node 304.1.2-a -> queued -> ready_for_expansion
```

Waiting-for-input shall be represented as a queue reason, not as a separate top-level node state.

---

### 4. Excluded node model

Excluded nodes shall remain separate from queued nodes.

An excluded node is not pending future expansion under the current resolved workflow state.

Excluded nodes shall include an explicit exclusion reason.

Allowed exclusion reasons include:

```text
branch_condition_not_satisfied
workflow_scope_mismatch
not_applicable
dependency_not_applicable
superseded_by_selected_branch
```

Examples:

```text
external pressure branch -> excluded -> branch_condition_not_satisfied
unrelated workflow node -> excluded -> workflow_scope_mismatch
```

An excluded node shall not be marked as visited.

An excluded node shall not be queued unless the workflow state later changes and makes that node applicable.

---

### 5. Branch selection

Branch selection shall be based on explicit conditions, resolved parameters, and node/edge metadata.

The graph engine shall not guess branches without evidence.

If a required branch condition is unresolved, the engine shall request the required input instead of expanding all possible branches.

For example, in the pipe wall thickness workflow:

```text
pressure loading type = internal pressure
```

shall select the internal pressure branch and exclude the external pressure branch.

The excluded branch shall remain visible in developer/debug state as excluded, not visited.

---

### 6. Parameter dependency handling

When a node requires a parameter that is not yet resolved, the graph engine shall pause expansion and queue the relevant pending item with a reason.

The engine shall not continue evaluating downstream nodes that depend on unresolved parameters.

The unresolved parameter state shall be structured.

Raw internal states such as the following shall not leak into user-facing output:

```text
waiting_user_input
required_input
missing_parameter
PARAM-*
```

The bottom input prompt (composer `current_ask` / `active_prompt`) is a rendering concern governed by:

```text
docs/desktopApp/center_panel_output_contract.md
audits/contracts/Workflow Rendered Text and Block Output.md
```

Graph queue reasons such as `waiting_for_user_input` are **engine state** — not center-panel scroll block types. Raw internal states shall not leak into user-facing output.

---

### 7. Equation dependency ordering

If an equation requires a value produced by another equation, the upstream equation shall be evaluated first.

The dependent equation shall remain queued until the upstream result is available.

The queued dependent equation shall include a reason such as:

```text
waiting_for_upstream_equation
```

After the upstream equation is evaluated, the dependent equation shall receive the resolved value with provenance.

Required behavior:

```text
1. Detect that Equation A depends on Equation B.
2. Queue or evaluate Equation B first.
3. Store Equation B result.
4. Resume Equation A.
5. Mark the dependent parameter value as derived from Equation B.
```

Equation rendering details are governed by:

```text
audits/contracts/Equation Rendering.md
```

---

### 8. Visited, queued, excluded, and completed state

The graph engine shall maintain clear traversal state.

Definitions:

```text
current = node currently being processed or displayed
visited_this_step = nodes expanded in the current operation
visited_total = nodes expanded since workflow start
queued = nodes selected for future expansion, with queue reasons
excluded = nodes deliberately not taken due to branch/scope/applicability logic
completed = nodes fully processed with no remaining pending dependency
```

The engine shall not mark a node as visited merely because it was discovered, considered, queued, or excluded.

A queued node shall include a queue reason.

An excluded node shall include an exclusion reason.

---

### 9. Traversal replay / graph visualizer support

The graph engine shall preserve a structured traversal path during workflow execution.

The traversal path shall be reproducible later in graph visualizers and developer inspection tools.

The traversal path shall be append-only for the workflow execution.

The traversal path shall not be reconstructed only from final visited/queued/excluded state.

The graph visualizer shall be able to replay the workflow by reading the traversal path step by step.

The traversal path shall capture, at minimum:

```text
step number
operation type
current node before step
expanded node
edges considered
edges taken
edge condition results
visited nodes in this step
queued nodes after the step
queue reasons
excluded nodes after the step
exclusion reasons
user input event, if applicable
equation evaluation event, if applicable
lookup event, if applicable
parameter resolution event, if applicable
timestamp or sequence order
```

The traversal path is developer/debug data.

It shall not be rendered as primary center-panel user output.

---

### 10. Deterministic traversal

For the same workflow state and same inputs, the graph engine shall produce the same traversal result.

Traversal shall not depend on unstable dictionary ordering, incidental file loading order, or nondeterministic queue behavior.

If multiple nodes are valid next candidates, the engine shall use a stable priority rule.

That priority rule shall be documented or discoverable from code.

The traversal path replay shall also be deterministic for the same saved execution trace.

---

### 11. No hardcoded workflow-specific behavior in generic engine code

Generic graph engine code shall not hardcode pipe wall thickness behavior.

Workflow-specific logic shall live in:

```text
workflow source data
node metadata
edge metadata
rule definitions
explicitly scoped workflow adapters
```

Forbidden in generic graph engine code:

```text
hardcoded pipe wall node IDs
hardcoded ASME paragraph IDs
hardcoded equation IDs
hardcoded pressure branch names
hardcoded parameter values
```

If workflow-specific behavior is temporarily required, it shall be isolated and clearly named as workflow-specific.

---

### 12. Output handoff to rendering pipeline

The graph engine shall provide structured node execution/traversal data to the rendering pipeline.

It shall not generate final user-facing prose except where explicitly part of a structured output contract.

The graph engine output shall support downstream rendering of:

```text
workflow_intro
paragraph blocks
equation blocks
summary blocks
references
```

Downstream rendering owns composer `current_ask` for active parameter asks — not center-panel scroll waiting blocks (see `docs/desktopApp/center_panel_output_contract.md`).

The graph engine shall not cause duplicate rendering by emitting the same logical output through multiple competing paths.

---

### 13. Performance behavior

A simple branch traversal or parameter request shall not trigger expensive full planning, full serialization, or unnecessary projection work unless required.

Developer/debug projections shall not dominate normal workflow execution time.

The audit shall identify whether these operations run during normal task execution:

```text
refresh_task_planning
engineering_plan_projection
task_state serialization
developer inspector projections
full graph serialization
full node table serialization
```

If they are dev-only, they should be lazy, cached, or computed only when the relevant debug tab is opened.

---

## Acceptance rules

This contract is satisfied only if all of the following are true:

1. Workflow root discovery selects the intended workflow deterministically.
    
2. Unknown workflow slug/ID does not return all workflows as valid matches.
    
3. Node expansion follows explicit edge/node conditions.
    
4. Irrelevant branches are excluded, not visited.
    
5. Missing required parameters pause expansion and create queued state with queue reason.
    
6. Waiting-for-input is represented as a queue reason, not a separate top-level node state.
    
7. Downstream nodes depending on unresolved parameters are not evaluated prematurely.
    
8. Upstream equations are evaluated before dependent equations.
    
9. Dependent equation parameters receive resolved value provenance.
    
10. Traversal state distinguishes current, visited, queued, excluded, and completed nodes.
    
11. Queued nodes include queue reasons.
    
12. Excluded nodes include exclusion reasons.
    
13. Traversal path is preserved step by step for replay in graph visualizers.
    
14. Traversal is deterministic for the same state and inputs.
    
15. Generic graph engine code does not hardcode workflow-specific behavior.
    
16. Graph engine output hands off structured state to the rendering pipeline.
    
17. Graph engine does not cause duplicate display output.
    
18. Normal execution avoids unnecessary expensive dev/debug projections.
    
19. Raw traversal state, raw JSON, and internal IDs do not leak into center-panel user output.
    

---

## Backend audit questions

Potential risk areas:

```text
graph engine
micro graph engine
workflow discovery
root discovery
node expansion
edge evaluation
condition evaluation
parameter registry
parameter resolution
equation execution
execution trace
traversal trace
planner refresh
task state serialization
developer inspector projections
workflows/
```

Audit questions:

1. Which graph engine implementation is currently active?
    
2. Is any legacy engine path still used?
    
3. How is workflow root discovery performed?
    
4. What happens when a workflow slug/ID is unknown?
    
5. How are workflow files under `workflows/{machine-key}.yaml` loaded?
    
6. How are outgoing edges selected during node expansion?
    
7. How are branch conditions evaluated?
    
8. How are unresolved parameters detected?
    
9. How is waiting-for-input represented as queued state?
    
10. What queue reasons currently exist?
    
11. Are blocked/waiting nodes already separate in code, and if so, can they safely be represented as queued nodes with reasons?
    
12. How are excluded nodes represented?
    
13. What exclusion reasons currently exist?
    
14. How are equation dependencies detected?
    
15. How are upstream equations queued before dependent equations?
    
16. How is equation result provenance stored?
    
17. How are current, visited, queued, excluded, and completed nodes represented?
    
18. Are queued/excluded reasons stored explicitly?
    
19. Is traversal order deterministic?
    
20. Is a step-by-step traversal path stored?
    
21. Can the traversal path be replayed by a graph visualizer?
    
22. Is traversal path append-only?
    
23. Is any workflow-specific behavior hardcoded in generic graph engine code?
    
24. Which parts of task state serialization are required for normal execution?
    
25. Which parts are only required for developer/debug views?
    
26. Can graph engine state cause duplicate display blocks downstream?
    
27. Can raw traversal/debug state leak into center-panel output?
    

---

## Frontend audit questions

The frontend does not own graph traversal logic, but it displays graph/debug state.

Potential risk areas:

```text
planner/debugger tab
task state tab
workflow status panel
developer inspector
center panel block rendering
right panel node opening
graph visualizer
```

Audit questions:

1. Does the frontend treat graph engine state as structured data?
    
2. Does it avoid rendering raw graph JSON in normal user-facing output?
    
3. Does the planner/debugger tab show current, visited, queued, excluded, and completed nodes clearly?
    
4. Does the debugger show queue reasons?
    
5. Does the debugger show exclusion reasons?
    
6. Does clicking a node open the node content in the right panel tab?
    
7. Does the center panel avoid showing traversal/debug state as workflow output?
    
8. Are dev/debug projections loaded only when needed?
    
9. Can the frontend consume the step-by-step traversal path?
    
10. Can a graph visualizer replay the traversal path from stored execution data?
    

---

## Required tests to locate or create

### Backend tests

Required coverage:

```text
Known workflow slug -> correct workflow root selected
Unknown workflow slug -> does not return all workflows
Workflow files are loaded from workflows/
Node expansion -> only applicable branch selected
Inapplicable branch -> marked excluded, not visited
Missing parameter -> node queued with waiting_for_user_input reason
Resolved parameter -> expansion resumes
Dependent equation -> upstream equation queued/evaluated first
Dependent equation waiting -> queued with waiting_for_upstream_equation reason
Upstream equation result -> dependent parameter receives provenance
Visited nodes -> only actually expanded nodes marked visited
Queued nodes -> include queue reason
Excluded nodes -> include exclusion reason
Same state/input -> same traversal order
Traversal path -> records step-by-step expansion events
Traversal path -> includes edges considered/taken and condition results
Traversal path -> includes user input and equation evaluation events
Traversal path -> can be replayed from stored execution trace
Generic graph engine -> no hardcoded pipe-wall-specific node IDs
Normal execution -> does not compute unnecessary dev/debug projections
Graph engine output -> does not create duplicate display blocks
```

Suggested locations:

```text
tests/graph/
tests/workflow/
tests/planner/
tests/mvp/
tests/api/
```

---

### Frontend tests

Required coverage:

```text
Planner/debugger tab shows current node
Planner/debugger tab shows visited nodes
Planner/debugger tab shows queued nodes
Planner/debugger tab shows excluded nodes
Planner/debugger tab shows completed nodes
Queued node row shows queue reason
Excluded node row shows exclusion reason
Node click opens node content in right panel tab
Task state tab does not render raw JSON inside table rows
Center panel does not render raw traversal/debug state
Graph visualizer can consume traversal path data
Dev/debug projections are lazy or isolated where applicable
```

Suggested locations:

```text
desktopApp/dev/desktop_ui/tests/
```

---

## Evidence required during audit

For each audited workflow step, capture:

```text
1. Workflow name
2. Workflow root selected
3. Current node
4. Input state before expansion
5. Nodes visited in this step
6. Nodes visited since workflow start
7. Nodes queued
8. Queue reasons
9. Nodes excluded
10. Exclusion reasons
11. Nodes completed
12. Parameters requested
13. Equations evaluated
14. Equation dependencies resolved
15. Traversal path event for the step
16. Edges considered and taken
17. Edge condition results
18. User input events, if any
19. Execution time per major operation
20. Display blocks emitted downstream
21. Tests proving behavior
```

---

## Known workflow to audit first

### Pipe wall thickness workflow

Expected traversal behavior to verify:

```text
1. Pipe wall thickness workflow is selected as the root.
2. Workflow source is loaded from workflows/pipe-wall-thickness.yaml.
3. Initial relevant ASME paragraph/workflow nodes are expanded in deterministic order.
4. Pressure loading type is requested before pressure-specific branch expansion.
5. Internal pressure input selects the internal pressure branch.
6. External pressure branch is excluded, not visited.
7. Equation dependencies are respected.
8. If equation t depends on t_m or another equation result, the upstream equation is evaluated first.
9. Dependent equation waits in queued state with waiting_for_upstream_equation reason.
10. Dependent equation parameter receives source/provenance from upstream equation.
11. Missing user parameters pause traversal through queued state with waiting_for_user_input reason.
12. Resolved user parameters resume traversal.
13. Previous traversal state remains inspectable in the debugger.
14. Traversal path is stored step by step and can be replayed.
```

---

## Known failure patterns to check

```text
unknown workflow slug returns all workflows
wrong workflow root selected
workflow folder path assumed incorrectly
node marked visited when only discovered
both branch paths expanded
wrong branch expanded after user input
waiting/blocked state duplicated separately from queued state without clear need
queued node has no reason
excluded node has no reason
dependent equation evaluated before upstream equation
dependent equation not queued while waiting for upstream equation
equation provenance not stored after upstream evaluation
waiting-for-input state leaks into center panel
raw task state JSON rendered in tables
previous equation re-entered after next node expansion
same equation emitted through multiple paths
traversal path missing
traversal path reconstructed only from final state
graph visualizer cannot replay workflow execution
simple branch traversal takes several seconds
developer projections run during normal execution
generic engine contains pipe-wall-specific hardcoding
```

---

## Open decisions

The following details should be confirmed before implementation changes:

1. Exact active graph engine class/module.
    
2. Whether legacy graph engine paths are still allowed.
    
3. Canonical state names for current, visited, queued, excluded, and completed.
    
4. Canonical queue reason enum.
    
5. Canonical exclusion reason enum.
    
6. Whether any existing blocked state should remain internally or be normalized into queued state.
    
7. Canonical source of branch priority/order.
    
8. Canonical representation of equation dependencies.
    
9. Canonical representation of equation result provenance.
    
10. Canonical traversal path event schema.
    
11. Whether traversal path is stored in task state, execution trace, or separate debug trace.
    
12. Whether traversal path should persist across reload.
    
13. Whether dev/debug projections should be lazy-loaded by tab selection.
    
14. Performance threshold for acceptable node expansion time.
    
