
# Frontend API Integration

## 1. Purpose

This document defines communication between the desktop application frontend and backend.

The backend is the source of truth.

The frontend:

- displays backend state
- collects user interaction
- sends commands
- renders responses

The frontend does not perform engineering calculations.

---

# 2. Communication Architecture

Flow:

Frontend

↓

API Service Layer

↓

Backend

↓

Response

↓

Frontend Renderer


Responsibilities:

Backend:

- calculations
- task state
- AI calls
- standards lookup
- validation


Frontend:

- visualization
- user interaction
- rendering

---

# 3. API Communication Style

The application uses:

- REST API for standard operations
- streaming communication where beneficial

REST examples:

- project loading
- task retrieval
- parameter submission
- report requests


Streaming examples:

- AI response generation
- long-running operations
- progress updates

---

# 4. Backend Client Layer

Frontend API calls must not exist inside components.

Incorrect:

```javascript
Component
  |
  fetch()
````

Correct:

```text
Component

↓

Service Layer

↓

Backend
```

---

# 5. API Service Structure

Example:

```
services/

api/

backendClient.ts

projectApi.ts

taskApi.ts

chatApi.ts

reportApi.ts
```

---

# 6. Backend Client

The backend client handles:

- backend URL
    
- authentication later
    
- request formatting
    
- error handling
    
- logging
    
- retries
    

---

# 7. Development Connection

Initial mode:

```
Desktop App

↓

localhost backend
```

Later:

```
Desktop App

↓

Cloud backend
```

The API layer must hide this difference.

---

# 8. Backend Startup

Preferred future behavior:

Application starts:

↓

Check backend connection

↓

If available:

connect

↓

If unavailable:

show offline state

↓

retry connection

---

# 9. Task Loading

When opening a task:

Frontend requests task state.

Backend decides the returned scope.

Possible response:

- current node
    
- parameters
    
- outputs
    
- references
    
- progress
    

---

# 10. Task Updates

Parameter updates follow:

User input

↓

Frontend sends change

↓

Backend validates

↓

Backend updates state

↓

Frontend refreshes

---

# 11. Partial vs Full Updates

The system supports:

Local updates:

Example:

unit display change

Full updates:

Example:

pressure changed

If a change affects calculations:

Frontend must:

- warn user
    
- request confirmation
    
- restart affected calculations if required
    

---

# 12. Task State Cache

Frontend may maintain short-term cache.

Purpose:

- faster UI
    
- prevent unnecessary reloads
    

Backend remains authoritative.

---

# 13. AI Chat Integration

When inside a task:

Every AI message includes:

- project context
    
- task state
    
- current node
    
- previous relevant nodes
    
- parameters
    
- outputs
    
- references
    

---

# 14. AI Context Responsibility

Backend creates final AI context.

Frontend only provides:

- current session information
    
- user message
    
- visible state
    

---

# 15. AI Message Flow

Example:

User:

"Why is this thickness required?"

Frontend sends:

```
message

+

task state

+

node information
```

Backend handles AI processing.

---

# 16. Parameter Submission

Frontend receives parameter definitions.

Example:

```json
{
"name":"pressure",
"type":"number",
"units":[
"bar",
"psi"
],
"default":"bar"
}
```

Frontend creates input UI.

---

# 17. User Input

User enters only project-specific values.

Example:

```
Pressure = 8
```

Frontend submits:

```json
{
parameter:"pressure",
value:8,
unit:"bar"
}
```

---

# 18. Input Validation

Validation exists on both sides.

Frontend:

- restrict invalid characters
    
- restrict unavailable options
    

Backend:

- engineering validation
    
- final authority
    

---

# 19. Live Database Search

Features such as material search use autocomplete.

Example:

User:

```
A10
```

Frontend:

```
search(material="A10")
```

Backend:

returns available materials.

This is not necessarily streaming.

---

# 20. Output Format

Backend sends structured output.

Example:

```json
{
"type":"equation",
"content":"PD/(2SE-P)"
}
```

Frontend renders.

---

# 21. Output Renderers

Frontend contains:

```
EquationRenderer

TableRenderer

GraphRenderer

ReferenceRenderer
```

---

# 22. Output Ordering

Backend controls engineering order.

Frontend preserves it.

---

# 23. Error Handling

Errors contain:

- error code
    
- message
    
- affected parameter
    
- affected task
    
- recovery suggestion
    
- AI explanation
    

---

# 24. Error Display

Normal user:

simple explanation

Developer:

technical details

---

# 25. Authentication Future

MVP:

local usage

Future:

cloud authentication

API layer must support:

- tokens
    
- users
    
- permissions
    
- organizations
    

---

# 26. Security

Frontend protects:

- API keys
    
- credentials
    
- local files
    

Sensitive engineering data stays local initially.

---

# 27. API Contracts

Recommended future addition:

OpenAPI schema.

Purpose:

- frontend/backend consistency
    
- automatic documentation
    
- safer AI development
    

---

# Final Principle

The frontend is a controlled interface.

The backend owns engineering truth.
