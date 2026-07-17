# Frontend Data Models

## 1. Purpose

This document defines the data structures used by the desktop application frontend.

The frontend is a visualization and interaction layer.

The backend remains the source of truth for:

- engineering data
- task state
- calculations
- standards
- AI context

The frontend should not recreate engineering models.

---

# 2. Data Flow Principle

The application follows:

```

Backend State  
|  
v  
Frontend Adapter / View Model  
|  
v  
UI Components  
|  
v  
User Interaction  
|  
v  
Backend Command

````

---

# 3. Backend Models vs Frontend View Models

The frontend receives backend objects.

However, UI-specific transformations are allowed.

Purpose:

- improve rendering
- avoid coupling components directly
- keep UI consistent

Example:

Backend:

```json
{
"node":"material_selection",
"value":"A106"
}
````

Frontend View Model:

```json
{
"title":"Material",
"displayValue":"A106",
"icon":"material"
}
```

---

# 4. Local Storage Strategy

The frontend uses caching only.

Stored locally:

- user preferences
    
- theme
    
- recent projects
    
- task session state
    
- UI layout
    

Engineering truth remains in backend.

---

# 5. Project Model

Project represents a user workspace.

Frontend displays:

- project name
    
- project identifier
    
- tasks
    
- recent activity
    

The backend provides the project data.

---

## Project Relationship

A project can contain:

- multiple tasks
    
- saved sessions
    

Example:

```
Project

 ├── Pipe Thickness Task
 ├── Flange Selection Task
 └── Report Generation Task
```

---

# 6. Task Model

Task represents an engineering workflow instance.

Frontend displays:

- task name
    
- task status
    
- current step
    
- progress
    
- created time
    
- updated time
    

Backend controls task state.

---

## Task Sessions

The application supports:

- one active task
    
- multiple saved unfinished tasks
    

Example:

```
Active:

Pipe Wall Thickness Design


Saved:

Tank Design
Flange Selection
```

---

# 7. Task State

Frontend receives task lifecycle status from the backend API. The frontend does not compute `TaskStatus`.

This section documents **`TaskStatus` only** — the task lifecycle enum on `Task` ([`models/task.py`](../../models/task.py)). It is **not** the same as:

- workflow orchestration macro-states in [`docs/core/5. workflow_design.md`](../core/5.%20workflow_design.md) (for example `GRAPH_DISCOVERED`, `INPUT_COLLECTION`);
- `progress.timeline[].status` step markers (`done` | `active` | `pending` on [`ProgressStepDto`](../../desktopApp/src/types/backend/api.ts));
- planner queue reasons or `awaiting_user_input` provenance metadata;
- validation or execution-result statuses on individual nodes.

`Task.status` is a projection of `execution_context.status` via [`context_status_to_task_status`](../../models/execution_context.py). Internal `ExecutionContextStatus` values (for example `executing`, `ready`, `blocked`) collapse into the `TaskStatus` members below before API serialization.

## TaskStatus map (current implementation)

Serialized on the API as snake_case strings on:

- `GET /api/v1/tasks/{id}/state` → `TaskStateDto.status` ([`api/serializers.py`](../../api/serializers.py) `task_state`, `task.status.value`);
- task list / recent-task summaries → `TaskSummaryDto.status` ([`task_summary`](../../api/serializers.py)).

| Backend enum (`TaskStatus`) | API wire value | Meaning (runtime) | Active-task UI label ([`taskStateManager.ts`](../../desktopApp/src/store/taskStateManager.ts) `statusLabel`) | Workspace list label ([`mapBackendStatus`](../../desktopApp/src/types/backend/api.ts) → [`TaskStatus`](../../desktopApp/src/types/frontend/workspace.ts)) |
| --- | --- | --- | --- | --- |
| `ACTIVE` | `active` | Task exists and is not waiting on input, paused, completed, or invalidated. Default for new tasks. | Active | `in_progress` |
| `AWAITING_INPUT` | `awaiting_input` | Task is blocked on user input (parameter, gate, or post-execution definition input). | Awaiting input | `in_progress` |
| `IN_PROGRESS` | `in_progress` | Task is in an in-flight execution context state (for example `ExecutionContextStatus.EXECUTING` maps here). | `in progress` (title-cased from wire) | `in_progress` |
| `PAUSED` | `paused` | Task was explicitly paused ([`TaskStateManager.pause_task`](../../engine/state/state_manager.py)). | Paused | `in_progress` (default branch) |
| `COMPLETED` | `completed` | Workflow execution finished successfully. | Completed | `completed` |
| `INVALIDATED` | `invalidated` | Execution or validation failed; API may attach `errors` (for example `calculation_failed`). | Invalidated | `in_progress` (default branch) |

**Workspace list note:** `TaskSummary.status` uses the frontend-only union `'available' | 'in_progress' | 'completed'`. The value `available` is **not** a backend `TaskStatus` wire value; `mapBackendStatus` maps unknown or non-terminal backend statuses (including `paused` and `invalidated`) to `in_progress`.

**Inspector / debug projection (optional):** When `task_state` is built with `projection_mode="full"`, `canonical.task.status` uses a separate vocabulary (`running`, `idle`, `failed`, …) from [`_canonical_status`](../../engine/state/task_state_canonical.py). Prefer top-level `status` for desktop UI; use `canonical.task.status` only in developer inspection views.

Example API payload fragment:

```json
{
  "status": "awaiting_input",
  "progress": {
    "timeline": [
      { "id": "pressure", "title": "Pressure", "status": "active" }
    ]
  }
}
```

The top-level `status` is `TaskStatus`. Each timeline entry’s `status` is step progress only (`done` | `active` | `pending`), not task lifecycle.

---

# 8. Node / Step Representation

The backend graph remains internal.

The frontend receives visualization information.

Example:

```
Material

Pressure

Thickness

Report
```

The user sees workflow steps.

The internal engineering graph is hidden.

---

# 9. Step Display Data

Each visible step may include:

- title
    
- status
    
- current value
    
- input state
    
- output state
    
- references
    

Example:

````
Material

A106
``` id="d5mg9x"

---

# 10. Parameter Model

Parameters are received from backend.

The frontend renders them.

Supported input types:

- number
- text
- dropdown
- multi-select
- checkbox
- material selector
- unit selector

---

# 11. Parameter Object

A parameter may contain:

````

{  
name,  
label,  
type,  
value,  
unit,  
options,  
default,  
validation,  
reference  
}

```

The backend provides:

- allowed values
- units
- defaults
- validation rules

---

# 12. Parameter Updates

User changes do not directly update application truth.

Flow:

```

User change

↓

Frontend sends command

↓

Backend validates

↓

Backend updates state

↓

Frontend refreshes

````

---

# 13. Material Selector

Material selection supports:

- search
- filtering
- database lookup

The frontend displays available materials.

The backend provides:

- material options
- properties
- references

---

# 14. Output Model

The frontend supports rendering:

- text
- equations
- tables
- graphs
- diagrams
- warnings
- references
- calculations
- reports

---

# 15. Output Wrapper

Outputs use a common structure.

Example:

```json
{
"type":"equation",
"content":"P*D/(2S)"
}
````

The renderer decides visualization.

---

# 16. Output Ordering

The backend controls logical ordering.

The frontend preserves the order received.

---

# 17. Equation Model

Backend provides:

- formula
    
- variables
    
- values
    
- references
    

Example:

```
t = PD/(2SE-P)
```

---

# 18. Formula Interaction

The frontend supports:

- equation rendering
    
- variable hover explanation
    
- parameter explanation popup
    

Right click:

"Ask AI"

sends context to AI assistant.

---

# 19. Reference Model

Reference objects contain:

- standard name
    
- paragraph
    
- table
    
- figure
    
- original text
    
- explanation
    
- location
    

---

# 20. Reference Display

References appear as expandable cards.

Hover:

shows original text.

Future:

full document viewer.

---

# 21. Chat Message Model

Chat messages contain:

- sender
    
- timestamp
    
- text
    
- references
    
- task association
    
- node association
    
- actions
    

---

# 22. Chat Storage

Chat history is stored by backend.

Frontend displays retrieved history.

Task conversations remain grouped by task.

---

# 23. UI State Model

Frontend maintains:

- theme
    
- panel sizes
    
- active panel
    
- selected task
    
- filters
    
- open dialogs
    

---

# 24. Error Model

Backend errors should include:

- error code
    
- message
    
- affected component
    
- recovery suggestion
    

Frontend converts errors into user-friendly messages.

---

# 25. File Handling

The backend manages engineering files.

The frontend handles:

- file selection
    
- upload requests
    
- download requests
    

---

# 26. Type System

The frontend uses:

TypeScript interfaces.

Reason:

- strong type safety
    
- easier Cursor development
    
- fewer UI inconsistencies
    

---

# 27. Validation

Frontend models should have validation.

Purpose:

- prevent UI mistakes
    
- detect API changes
    
- improve development reliability
    

---

# Final Principle

The frontend does not own engineering intelligence.

It visualizes backend state and provides a controlled user interface.

