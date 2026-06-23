# Desktop Application Structure

## 1. Workspace Philosophy

The application follows a workspace-first interaction model inspired by modern AI productivity applications such as Cursor.

The application is not primarily a chatbot.

The user interacts with an engineering workspace where AI assists navigation, understanding, standards interpretation, and execution of structured engineering tasks.

The primary interaction flow:

User Conversation

↓

Intent Detection

↓

Engineering Task Workspace

↓

Guided Inputs, Calculations, Results, and Reporting

The AI serves as the entry point into structured engineering workflows.

---

## 2. Main Application Layout

The application uses a three-panel workspace layout.

```text
+------------------------------------------------------------------+
|                         APPLICATION WORKSPACE                    |
+------------------------------------------------------------------+
| LEFT PANEL |              CENTER PANEL            | RIGHT PANEL  |
|------------|--------------------------------------|--------------|
| Tasks      | Active Task Workspace                | Task State   |
| Projects   | Inputs                               | AI Chat      |
| History    | Outputs                              |              |
|            | Results                              |              |
+------------------------------------------------------------------+
```

The layout should resemble modern desktop productivity applications and support resizing and panel management.

---

## 3. Left Panel

### Purpose

The left panel serves as the primary navigation area.

It provides access to:

- New task creation
- Available engineering tasks
- Recent tasks
- Previous tasks
- Project history

---

### Left Panel Sections

#### Create New Task

Allows the user to begin a new engineering workflow.

---

#### Available Tasks

The application should display engineering workflows available to the user.

Examples:

- Pipe Thickness Calculation
- Flange Selection
- Material Selection
- Tank Design
- Standards Lookup

Task ordering may later be customized using:

- user preferences
- usage frequency
- task history

---

#### Recent Tasks

Displays recently used engineering tasks.

Users should be able to resume unfinished tasks directly from this section.

---

## 4. Center Panel

### Purpose

The center panel is the primary interaction workspace.

Its behavior changes depending on whether an engineering task is active.

---

## 4.1 No Active Task

When no task is active, the center panel functions as the AI workspace.

Contents:

- AI chat interface
- Chat history
- User questions
- AI responses
- Suggested tasks

This mode allows users to:

- ask engineering questions
- search standards
- discover available workflows
- initiate tasks

---

## 4.2 Active Task

When a task becomes active, the center panel transforms into the task workspace.

Contents may include:

- Task inputs
- Parameter forms
- Calculations
- Tables
- Graphs
- Engineering equations
- Visualizations
- Outputs
- Results

The center panel becomes the primary working area for completing engineering workflows.

---

## 5. Right Panel

### Purpose

The right panel provides contextual support during active engineering workflows.

The panel remains hidden or inactive when no engineering task is active.

---

## 5.1 Active Task Mode

When a task is active, the right panel becomes visible.

It contains:

### Task State Tracker

Displays:

- Current stage
- Progress
- Completed steps
- Remaining steps
- Current task status

---

### AI Assistant

The AI assistant moves into the right panel during active tasks.

Purpose:

- Explain concepts
- Answer engineering questions
- Interpret standards
- Assist with workflow decisions
- Explain results

Separating AI interactions from the task workspace helps minimize unnecessary AI usage and keeps engineering workflows focused.

---

## 6. Panel Behavior

The workspace should support:

### Resizable Panels

Users should be able to resize:

- Left panel
- Center panel
- Right panel

similar to Cursor and VS Code.

---

### Collapsible Panels

Users should be able to:

- Collapse the left panel
- Collapse the right panel
- Focus on the center workspace

This allows users to maximize working space when needed.

---

## 7. Navigation Model

The primary navigation entity is the engineering task.

The application manages:

- Available tasks
- Active tasks
- Unfinished tasks
- Completed tasks

Projects serve as organizational containers rather than primary navigation units.

---

## 8. Task Session Model

Users work on one active task at a time.

Each task behaves as a persistent session.

A task can be:

- Created
- Started
- Paused
- Resumed
- Completed

Task state should persist between application restarts.

---

## 9. Task State Management

Task lifecycle logic is managed by the backend.

The frontend is responsible for displaying:

- Current state
- Progress information
- Required user actions
- Inputs
- Outputs

The frontend should not duplicate backend workflow logic.

---

## 10. Task Tabs

The application should support tabs.

Examples:

```text
Pipe Thickness | Flange Selection | Report
```

Tabs provide navigation between:

- Active tasks
- Reports
- Engineering views

Only one task may be actively worked on at a time.

---

## 11. AI Interaction Model

The AI assistant operates in two modes.

---

### General AI Mode

No task active.

Purpose:

- Answer engineering questions
- Explain standards
- Search engineering information
- Suggest available workflows
- Detect engineering intent

---

### Task AI Mode

Task active.

Purpose:

- Explain task concepts
- Interpret standards
- Answer workflow-specific questions
- Provide engineering guidance
- Assist with report generation

Task-specific context should be available to the AI during this mode.

---

## 12. Intent Detection Behavior

The AI may detect engineering intent from conversations.

Example:

User:

"I need to calculate pipe wall thickness according to ASME B31.3"

AI:

"I detected a Pipe Thickness Calculation task. Would you like to start a new calculation workspace?"

[Start Task]

The user should approve task creation.

The application should not silently switch modes.

---

## 13. AI-Controlled Actions

The AI may:

- Suggest workflows
- Open task creation dialogs
- Recommend next actions
- Navigate users to appropriate tasks

The AI should not execute engineering calculations independently.

The engineering workflow remains deterministic.

---

## 14. Context Handling

AI context should be managed by the application.

Potential context sources:

- Active task
- Task history
- Inputs
- Outputs
- Current state
- Relevant engineering information

The application should avoid sending unnecessary context.

Context management should be controlled centrally.

---

## 15. User Experience Principles

The interface should prioritize:

1. Minimal clicks
2. Deep engineering explanations
3. Clear workflows
4. Fast navigation
5. Professional appearance
6. Low cognitive load

---

## 16. Visual Design Philosophy

The interface should remain minimal and focused.

The application should avoid:

- Dashboard clutter
- Excessive buttons
- Information overload

Information should appear progressively based on:

- User intent
- Active task
- Workflow state

---

## 17. Error Handling

Task-related errors should primarily appear within the center workspace.

Users should immediately understand:

- What failed
- Why it failed
- What action is required

The AI assistant may optionally provide explanations when useful.

---

## 18. Workflow Scope

Initial version should not include:

- Drag-and-drop workflow builders
- Visual workflow editors
- User-created workflows
- Task dependency graphs

Engineering workflows remain predefined and controlled by the application.

---

## 19. Future Expansion

The architecture should allow future support for:

- Workflow visualization
- Dependency graphs
- Collaboration
- Cloud synchronization
- Engineering knowledge navigation
- Additional engineering disciplines

These capabilities are not required for the initial release.

---

## 20. Final Structure Definition

The application is:

> A three-panel engineering workspace where AI initiates conversations, detects engineering intent, and assists users within structured engineering workflows.

The center panel is always the primary work area.

The left panel provides navigation and task access.

The right panel provides task state visibility and contextual AI assistance during active workflows.

This structure serves as the foundation for all future UI and workflow development.