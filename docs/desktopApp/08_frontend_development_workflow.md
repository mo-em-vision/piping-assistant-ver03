

# Frontend Development Workflow

## 1. Purpose

This document defines development rules for the desktop application frontend.

The goal:

- maintain architecture quality
- allow AI-assisted development
- prevent uncontrolled code growth
- keep frontend aligned with backend design

---

# 2. Development Philosophy

The project follows a balanced approach.

Priorities:

1. Maintainable architecture
2. Fast iteration
3. Clear separation of concerns
4. Reliable integration

The application should evolve through complete functional slices.

---

# 3. Feature Development Strategy

Features should be developed vertically.

Example:

Task creation feature:

```

UI  
↓  
API connection  
↓  
State handling  
↓  
Backend communication  
↓  
Testing  
↓  
Documentation

```

Avoid creating disconnected UI first and connecting later.

---

# 4. Cursor Development Rules

Before modifying code, Cursor should:

1. Review relevant documentation
2. Inspect existing implementation
3. Identify existing patterns
4. Propose a plan for major changes

---

# 5. Architectural Changes

Cursor should not:

- restructure folders without reason
- introduce new patterns unnecessarily
- duplicate backend logic
- create temporary hacks

For major architectural changes:

Explain:

- reason
- affected files
- alternatives

---

# 6. Component Design Rules

Components should follow single responsibility.

Preferred:

```

Component

handles one UI responsibility

```

Avoid:

```

Component

fetches data  
calculates logic  
handles validation  
renders UI

```

---

# 7. Component Organization

Use feature-based organization.

Example:

```

features/

tasks/  
chat/  
reports/  
projects/

components/

shared UI components

```

---

# 8. API Communication

Components should not directly call backend APIs.

Use:

```

React Component

↓

State Store

↓

API Service Layer

↓

Backend

```

---

# 9. Service Layer

Backend communication should be separated.

Example:

```

services/

taskService  
chatService  
reportService  
projectService

```

Responsibilities:

- API calls
- response handling
- error processing

---

# 10. State Management

Use a global state manager.

Recommended:

Zustand

Used for:

- active task
- UI state
- panel state
- theme
- cached session information

Backend remains the source of engineering truth.

---

# 11. State Updates

Preferred flow:

```

User action

↓

Frontend command

↓

Backend validation

↓

Backend update

↓

Frontend refresh

```

Frontend should not assume success before backend confirmation.

---

# 12. Error Handling

All backend interactions should support:

- loading state
- error state
- retry possibility

Errors should be converted into user-friendly messages.

---

# 13. Cursor Planning Mode

Large changes should begin with planning.

Example:

Request:

"Add report viewer"

Cursor should first produce:

- affected components
- required files
- data flow
- testing requirements

Then implement.

---

# 14. Existing Functionality Preservation

Cursor should preserve existing functionality.

Changes should avoid breaking:

- task workflow
- backend communication
- existing components

---

# 15. Mock Backend Strategy

During UI development:

Mock data is allowed.

Purpose:

- develop UI before backend completion
- test rendering

Mock data must:

- follow backend schema
- be clearly marked

Example:

```

mock/  
taskState.mock.json

```

---

# 16. Mock Data Rules

Every mock implementation should include:

```

MOCK_DATA=true

```

or equivalent indication.

Purpose:

Prevent accidental production use.

---

# 17. Testing Strategy

Testing includes:

- component tests
- interaction tests
- integration tests

---

# 18. Test Priorities

Critical workflows:

Example:

```

Create task

↓

Input parameters

↓

Receive output

↓

Generate report

```

should always have tests.

---

# 19. Backend Testing

Tests should support:

- mock backend
- real backend

depending on development stage.

---

# 20. Dependency Management

Cursor should not install dependencies freely.

New dependencies require:

- justification
- explanation
- confirmation

---

# 21. UI Libraries

Use libraries when they improve:

- reliability
- accessibility
- consistency

Avoid unnecessary dependencies.

---

# 22. Styling

Recommended:

Tailwind CSS

Reasons:

- fast iteration
- AI-friendly
- consistent design system
- easy maintenance

---

# 23. Documentation Rules

Major components should include documentation.

Required documentation:

- architecture docs
- setup instructions
- component descriptions
- API descriptions

---

# 24. Documentation Updates

After major changes:

Update related documentation.

Documentation must match implementation.

---

# 25. Git Workflow

Use feature branches.

Example:

```

feature/task-workspace

feature/chat-panel

feature/report-viewer

```

---

# 26. Commit Style

Commits should describe:

- what changed
- why it changed

Example:

Good:

```

Add task workspace renderer for backend output visualization

```

---

# 27. Development Order

Initial build order:

1. Application shell
2. Panel system
3. Backend connection
4. Task rendering
5. AI chat
6. Engineering visualization

---

# 28. MVP Strategy

Build one complete workflow.

Example:

```

Create Task

↓

Receive Backend State

↓

Render Inputs

↓

Render Outputs

↓

Generate Report

```

Then expand.

---

# 29. Developer Mode

A developer mode should exist.

Purpose:

- debugging
- inspecting API responses
- checking state changes

---

# 30. Error Visibility

Normal users see:

- friendly messages

Developers can enable:

- technical details

---

# 31. AI Coding Restrictions

Cursor should avoid:

- architecture changes without review
- unnecessary dependencies
- duplicated logic
- incomplete temporary solutions

---

# 32. Feature Completion Requirements

A feature is complete when it has:

- implementation
- tests
- documentation update

---

# Final Principle

AI assists development.

Architecture decisions remain controlled.

The codebase should become easier to extend over time, not harder.
