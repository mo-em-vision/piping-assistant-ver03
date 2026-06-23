
# Desktop App Folder Structure

## 1. Purpose

This document defines the frontend project organization.

Goals:

- keep code maintainable
- support AI-assisted development
- prevent duplicated logic
- allow future expansion

The structure should support:

- multiple engineering disciplines
- multiple calculation workflows
- future web version
- future extensions

---

# 2. High-Level Architecture

The desktop application uses:

- Electron wrapper
- React frontend
- shared application layer

Structure:

```

desktopApp/

electron/

src/

package.json

```id="9fdz8l"

---

# 3. Root Structure

Recommended:

```

desktopApp/

├── electron/  
│  
├── src/  
│  
├── public/  
│  
├── assets/  
│  
├── tests/  
│  
├── docs/  
│  
├── package.json  
│  
└── configuration files

```

---

# 4. Electron Layer

Electron is separated from React.

Structure:

```

electron/

├── main.ts  
├── preload.ts  
└── services/

```

Responsibilities:

- application window
- filesystem access
- native dialogs
- local storage access
- backend startup

---

# 5. React Source Structure

```

src/

├── projects/  
├── components/  
├── services/  
├── store/  
├── hooks/  
├── types/  
├── utils/  
└── config/

```

---

# 6. Project-Centric Organization

Projects are the main application domain.

Structure:

```

projects/

project/

└── tasks/

```id="f43r3s"

---

# 7. Task Structure

Each task contains its own workspace.

Example:

```

projects/

PipeDesignProject/

└── tasks/

```
  ThicknessCalculation/

      ├── chat/
      ├── reports/
      ├── visualizations/
      ├── outputs/
      ├── components/
      ├── hooks/
      └── types/
```

```

---

# 8. Project Responsibilities

Project layer handles:

- project selection
- project history
- project settings
- task organization

---

# 9. Task Responsibilities

Task layer handles:

- active workflow display
- task state visualization
- task outputs
- task-specific interactions

Backend remains responsible for task logic.

---

# 10. Chat Structure

Each task has its own chat.

Example:

```

task/

chat/

├── ChatPanel.tsx  
├── MessageRenderer.tsx  
├── ChatInput.tsx  
└── chatService.ts

```

Responsibilities:

- display conversation
- handle user interaction
- render AI responses

---

# 11. Visualization Structure

Engineering visualization components:

```

visualizations/

├── EquationViewer  
├── GraphViewer  
├── TableViewer  
├── DiagramViewer  
└── ReferenceViewer

```

---

# 12. Report Structure

```

reports/

├── ReportViewer.tsx  
├── ExportControls.tsx  
└── reportService.ts

```

---

# 13. Shared Components

Reusable components:

```

components/

ui/

├── Button  
├── Modal  
├── Input  
├── Card  
├── Dropdown

engineering/

├── FormulaViewer  
├── ReferenceCard  
├── UnitInput

```id="s8x9gu"

Shared components should not contain business logic.

---

# 14. Design System

A shared UI system exists.

Purpose:

- consistent appearance
- reusable components
- faster development

---

# 15. Backend Services

API communication is centralized.

Structure:

```

services/

api/

├── backendClient.ts  
├── taskApi.ts  
├── chatApi.ts  
├── reportApi.ts  
└── projectApi.ts

```

---

# 16. State Management

Use multiple stores.

Structure:

```

store/

├── uiStore.ts  
├── projectStore.ts  
├── taskStore.ts  
├── chatStore.ts  
└── connectionStore.ts

```

---

# 17. Global State Responsibilities

Stores manage:

- active project
- active task
- panel layout
- theme
- UI preferences
- backend connection

---

# 18. Hooks

Hooks abstract reusable behavior.

Structure:

```

hooks/

useProject.ts  
useTask.ts  
useBackend.ts  
useTheme.ts

```

Feature-specific hooks may exist inside features.

---

# 19. Type System

Use TypeScript.

Types are separated:

```

types/

├── backend/  
├── frontend/  
└── common/

```

---

# 20. Backend Types

Backend types represent:

- API responses
- task states
- inputs
- outputs

---

# 21. Frontend Types

Frontend types represent:

- view models
- UI state
- component props

---

# 22. Configuration

Environment configuration:

```

config/

├── development  
├── production  
└── constants

```

Environment variables include:

- backend URL
- development flags
- feature flags

---

# 23. Assets

Static assets:

```

assets/

├── icons  
├── images  
└── fonts

```

---

# 24. Tests

Tests are separated.

Structure:

```

tests/

├── projects/  
├── tasks/  
├── components/  
└── integration/

```

Tests mirror application structure.

---

# 25. Naming Convention

Use consistent naming.

Components:

```

PascalCase

TaskViewer.tsx  
FormulaCard.tsx

```

Files should follow existing project conventions.

---

# 26. Dependency Rules

New dependencies require:

- justification
- review
- compatibility check

Avoid unnecessary packages.

---

# 27. Future Expansion

Structure supports:

- more disciplines
- more calculations
- more visualization types

---

# 28. Future Extensions

Plugin architecture is not required initially.

However, structure should avoid preventing future extensions.

---

# Final Principle

The folder structure should follow the user's workflow:

Project → Task → Engineering Work → Output.

The code should mirror the product.
```

Next recommended document:

`10_frontend_api_integration.md`

This will define how Cursor connects React to your existing backend:

- API calls
    
- request flow
    
- authentication later
    
- streaming AI
    
- error handling
    
- mock mode
    

This is probably the last major architecture document before coding starts.