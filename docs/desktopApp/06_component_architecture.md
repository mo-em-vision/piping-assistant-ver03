
# Component Architecture

## 1. Purpose

This document defines the frontend component architecture for the desktop application.

The desktop application is a thin client.

It is responsible for:

- rendering backend data
- providing user interaction
- managing UI state
- displaying engineering content

It is not responsible for:

- engineering calculations
- task logic
- standards interpretation
- workflow decisions

---

# 2. Architecture Style

The application uses a hybrid feature-based architecture.

The structure combines:

- feature modules
- reusable UI components
- shared utilities

Recommended structure:

```

desktopApp/

src/

├── features/  
│  
│ ├── tasks/  
│ ├── chat/  
│ ├── projects/  
│ ├── reports/  
│  
├── components/  
│  
│ ├── layout/  
│ ├── inputs/  
│ ├── visualization/  
│ ├── dialogs/  
│  
├── store/  
│  
├── services/  
│  
└── utils/

```

---

# 3. State Management

A global state manager should be used.

Recommended:

Zustand

Purpose:

Manage:

- active project
- active task
- panel state
- theme
- UI preferences
- cached session information

Backend state remains controlled by backend.

Frontend state controls presentation.

---

# 4. Application Shell

Main structure:

```

WorkspaceLayout

├── LeftPanel  
│  
├── CenterWorkspace  
│  
└── RightPanel

```

Each panel is independent and can be modified separately.

Panels communicate through shared application state.

---

# 5. Layout Behavior

Default:

```

Left Panel | Center Panel

```

When task becomes active:

```

Left Panel | Center Task Workspace | Right Panel

```

Right panel remains hidden when no task exists.

---

# 6. Left Panel

Purpose:

Navigation and task selection.

Structure:

```

LeftPanel

├── New Task Button  
│  
├── Available Tasks  
│  
├── Recent Tasks  
│  
└── Search

```

---

# 7. Recent Tasks

Recent tasks display:

Only:

- task name

No:

- status
- progress
- metadata

The goal is minimal UI.

---

# 8. Task List Style

The task list follows Cursor-like design.

Characteristics:

- compact list
- clean spacing
- minimal information
- hover actions

---

# 9. Task Search

Search is located at the bottom of the left panel.

Supports:

- finding previous tasks
- filtering task history

---

# 10. Center Workspace

The center panel has two modes.

## Mode 1

AI Conversation

When no task exists.

---

## Mode 2

Task Workspace

When a task exists.

---

# 11. Task Workspace Structure

```

CenterWorkspace

├── OutputRenderer  
│  
└── InputArea

```

---

# 12. Output Renderer

The backend sends raw structured output.

Frontend renders:

- text
- formulas
- tables
- graphs
- diagrams
- references
- results

The renderer should support engineering visualization.

---

# 13. Input Area

The bottom input area changes behavior.

Normal mode:

AI chat input

Task mode:

Structured input interface

Examples:

- number entry
- unit selection
- option selection

Free-form text should not be allowed during parameter collection.

---

# 14. Input Interaction

When user input is required:

The chat area transforms.

Example:

```

Select material:

[ A106 ▼ ]

[Continue]

```

This reduces invalid states.

---

# 15. Completed Inputs

Completed parameters collapse.

Example:

```

✓ Material  
A106

✓ Pressure  
8 bar

→ Temperature  
Waiting input

```

---

# 16. Right Panel

Visible only during active tasks.

Structure:

```

RightPanel

├── TaskTimeline  
│  
└── TaskAIChat

```

---

# 17. Task Timeline

Displays:

- completed steps
- current step
- future steps

Example:

```

✓ Material : A106

✓ Pressure : 8 bar

→ Thickness

○ Report

```

---

# 18. Timeline Interaction

Users do not navigate backwards through workflow steps.

The timeline is primarily informational.

Parameter values are shown directly.

---

# 19. Task AI Chat

Each task has its own conversation history.

History is grouped by task.

AI receives:

- current task
- current state
- relevant context

---

# 20. AI Message Components

AI messages support:

- streaming
- markdown
- equations
- tables
- references
- expandable explanations
- copy
- follow-up questions

---

# 21. AI Actions

Messages can include actions:

Example:

```

Explanation

[Explain More]

[Show Reference]

[Use in Task]

```

---

# 22. Engineering Components

Reusable components:

- EquationViewer
- ReferenceViewer
- MaterialSelector
- UnitInput
- EngineeringTable
- CalculationViewer
- DiagramViewer
- GraphViewer
- ReportViewer

---

# 23. Equation Viewer

Supports:

Display:

- formulas
- variables
- values

Hover:

Shows variable explanation.

Right click:

Ask AI.

---

# 24. Reference Viewer

References appear as interactive elements.

Example:

```

ASME B31.3

Paragraph:  
304.1.2

Requirement:  
...

```

Hover shows original text.

---

# 25. Dialog System

Modal dialogs are used for:

- dangerous actions
- confirmations
- creation flows

Normal workflow remains inside workspace.

---

# 26. Question and Option Popups

Questions requiring user decisions appear above the input area.

Similar to Cursor interaction.

Example:

```

Choose calculation type:

( ) Design thickness

( ) Minimum thickness

```

Output remains in workspace.

---

# 27. Notifications

Use minimal notifications.

Recommended:

Toast messages.

Examples:

- Calculation completed
- Report generated
- Task saved

Avoid intrusive UI.

---

# 28. Testing Strategy

All components should have tests.

Testing focus:

- UI behavior
- backend data rendering
- state transitions

---

# 29. Development Strategy

Development follows vertical slices.

Example:

Feature:

Task creation

Includes:

- UI
- backend connection
- state handling
- tests

Then next feature.

---

# 30. MVP Components

Initial MVP should include:

- application shell
- left navigation
- AI chat
- task workspace
- input rendering
- calculation visualization
- report preview/export

---

# Final Principle

The frontend is a flexible engineering workspace.

The backend owns intelligence.

The frontend owns experience.
```

Next recommended file:

`07_frontend_data_models.md`

This is important before coding because Cursor needs to know **what objects exist in the frontend**:

- Task
    
- Project
    
- Node
    
- Input
    
- Output
    
- Formula
    
- Reference
    
- Chat message
    
- Report
    

Otherwise it will invent inconsistent structures.