# Backend UI Contract

## 1. Purpose

This document defines the communication boundary between the desktop application and the backend engine.

The desktop application is a thin client.

Its responsibilities:

- visualize backend state
- collect user interaction
- display calculations
- display engineering information
- send user actions

The desktop application should not contain:

- engineering logic
- calculation rules
- standards interpretation
- task workflow logic

The backend remains the source of truth.

---

# 2. Architecture Overview

Initial architecture:

```

Desktop Application  
(React + Desktop Wrapper)

```
      |
      |
      ↓
```

Backend Engine  
(Task Manager + Graph + Calculations + AI)

```
      |
      |
      ↓
```

Engineering Knowledge Base  
Standards / Materials / Rules

```

---

# 3. Deployment Strategy

## Initial Development

The backend runs locally.

The desktop application connects to the local backend.

Purpose:

- rapid development
- debugging
- testing
- MVP creation

---

## Future Deployment

The architecture should support:

Cloud backend deployment.

Future structure:

```

Desktop Application

```
    |
    |
```

Cloud API

```
    |
```

Backend Services

```

---

# 4. Communication Model

Initial communication:

REST API.

Reason:

- simple development
- easy debugging
- clear request/response model

Future enhancement:

WebSocket support for:

- streaming AI responses
- calculation progress
- long-running operations

---

# 5. Backend Response Philosophy

Backend should provide ready-to-display objects.

Example:

```

Task state:

{  
task,  
current_node,  
progress,  
inputs,  
outputs,  
references  
}

```

The frontend should not reconstruct engineering meaning.

---

# 6. Workflow Ownership

Backend controls:

- task state
- node progression
- assumptions
- calculations
- validation
- engineering rules

Frontend controls:

- layout
- visualization
- interaction
- component rendering

## Graph-driven workflow paths (no hardcoded steps)

Workflow **paths**, **branches**, and **which parameters to ask** are resolved by backend graph expansion — not by hardcoded lists in Python, TypeScript, or API constants.

| Concern | Source of truth |
| --- | --- |
| Active execution subgraph | `expand_workflow()` — node `assumptions`, edge `when`, `applicability.applies_when` |
| Parameters to collect | `required_user_inputs()` on active parameter nodes |
| Path decision (e.g. internal vs external pressure) | `engine/graph/path_decision.resolve_path_decision()` from expanded nodes + task facts |
| Timeline / composer order | `task.outputs.graph_input_order`, `collection_field_order` (set during planning refresh) |
| Step labels | `task.outputs.graph_step_titles` from parameter node metadata |
| Phase ordering only | `workflows/<id>/runtime.yaml` `navigation.phases` (does not inject branch-specific fields) |

After each confirmed user input, the backend replans (`refresh_task_planning`) so ruled-out branches and their parameters drop from `phase_missing`, goals, and timeline.

**Do not** add workflow-specific parameter lists to `api/workflow_timeline.py`, `engine/planner/`, or the desktop client. Author gates and branches on knowledge nodes and workflow runtime sidecars instead.

Project rule: `docs/rules.md` §13 and `.cursor/rules/graph-expansion.mdc`.

---

# 7. Dynamic UI Strategy

The backend provides structured information.

The frontend maps information to UI components.

Example:

Backend:

```

Input:

name:  
pressure

type:  
number

unit:  
bar

```

Frontend renders:

```

Pressure

[ 100 ] [bar ▼]

```

---

# 8. Input System

Backend provides:

- parameter names
- types
- units
- options
- validation requirements

Frontend provides reusable components.

Components include:

- number input
- unit selector
- dropdown
- material selector
- table input

---

# 9. Unit Handling

Users may select units in the frontend.

The backend performs:

- unit normalization
- conversion
- engineering calculations

The frontend displays:

- selected unit
- converted values where appropriate

---

# 10. Task Progress Visualization

The frontend displays task progress as a timeline.

Example:

```

✓ Material : A106

✓ Pressure : 8 bar

→ Thickness : Waiting input

○ Generate Report

```

The backend remains responsible for the actual task state.

---

# 11. Engineering Graph Visibility

The internal backend graph is not directly exposed.

Users see:

- simplified workflow
- task progress
- current stage

The internal graph remains an implementation detail.

---

# 12. Validation Errors

Backend validation failures should return:

- error message
- affected parameter
- explanation

Frontend displays:

- user-friendly error

AI may provide additional explanation.

---

# 13. Calculation Visualization

Backend provides:

- calculation results
- formulas
- variables
- references

Frontend renders:

- equations
- calculation steps
- result cards

---

# 14. Formula Display

Backend sends formula representation.

Frontend displays formulas beautifully.

Example:

```

Required thickness:

t = P × D / (2S × E)

Result:

12.4 mm

```

Users can expand:

- variables
- values
- assumptions
- references

---

# 15. Interactive Formula Explanation

Users can interact with formulas.

Selecting a formula may reveal:

- variables
- meanings
- values used
- standard references

---

# 16. Report Generation

Report generation is performed by the backend.

Frontend:

- sends request
- displays progress
- previews result

Users may choose:

- preview inside application
- export file

---

# 17. AI Context

The backend prepares AI context.

The desktop application does not build engineering context.

AI receives:

- current task
- task state
- current node
- previous nodes
- calculation outputs

---

# 18. Text Selection AI

Frontend supports:

Select text

↓

Ask AI in Side Chat

↓

Send:

- selected text
- current task state
- relevant context

to backend AI service.

---

# 19. Local Storage

Desktop application stores locally:

- user preferences
- theme selection
- recent projects
- task sessions

Future synchronization:

Local data → Cloud sync

---

# 20. Error Handling

Backend errors should be transformed into user-friendly messages.

Users should see:

- what happened
- what action is needed

Technical details remain hidden.

---

# 21. Debug Mode

A developer debug mode may exist later.

Normal users should not see backend details.

---

# 22. Client Architecture

Initial architecture:

Thin client.

The desktop application focuses on:

- rendering
- interaction
- visualization

Backend owns intelligence.

---

# 23. Future Platform Support

The frontend architecture should allow future:

- web application
- mobile application

The desktop application should avoid unnecessary platform-specific logic.

---

# Final Principle

The desktop application is a visual engineering workspace.

The backend is the engineering intelligence layer.

The frontend should display backend truth, not recreate it.



