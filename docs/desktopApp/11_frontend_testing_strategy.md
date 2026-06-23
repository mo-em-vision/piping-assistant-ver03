

# Frontend Testing Strategy

## 1. Purpose

This document defines testing rules for the desktop application frontend.

The objective is:

- ensure reliable user workflows
- prevent architecture degradation
- verify backend/frontend integration
- detect AI-generated implementation mistakes

Passing tests alone does not guarantee correct engineering behavior.

Critical workflows require manual verification.

---

# 2. Testing Philosophy

Testing priorities:

1. User workflow reliability
2. Correct backend interaction
3. UI correctness
4. Maintainable code

The application is tested from the user's perspective.

---

# 3. Testing Layers

The application uses:

- unit tests
- component tests
- integration tests
- end-to-end tests

---

# 4. Testing Priority

Most important:

End-to-end testing

Reason:

The application is a state-driven engineering workflow.

Example:

```

User request

↓

Task creation

↓

State detection

↓

Input collection

↓

Backend calculation

↓

Output rendering

↓

Report generation

```

---

# 5. Unit Tests

Unit tests verify isolated logic.

Examples:

- utility functions
- formatters
- converters
- state helpers

---

# 6. Component Tests

Component tests verify UI behavior.

Examples:

- buttons
- dialogs
- inputs
- cards
- selectors

---

# 7. Engineering Component Tests

Engineering visual components require testing.

Examples:

- FormulaViewer
- TableViewer
- GraphViewer
- ReferenceViewer

Tests verify:

- rendering
- interaction
- error handling
- loading state
- accessibility

---

# 8. Integration Tests

Integration tests verify communication between:

- components
- stores
- services
- backend interfaces

---

# 9. Task Workflow Tests

Every major engineering task should have workflow tests.

Example:

```

Create task

↓

Receive task state

↓

Insert parameters

↓

Run calculation

↓

Display output

↓

Generate report

```

---

# 10. State Testing

Tests should verify backend-driven state transitions.

Example:

```

waiting_input

↓

calculating

↓

completed

```

The frontend should correctly render each state.

---

# 11. Backend Testing

Testing should support:

- mock backend
- real backend

Real backend tests are preferred when available.

---

# 12. Mock Backend Strategy

Mock data is required during UI development.

Purpose:

- develop before backend completion
- reproduce scenarios

Mock data must follow backend schemas.

---

# 13. Mock Data Requirements

Mock scenarios should include:

Successful:

```

valid task  
valid calculation

```

Failure:

```

missing input  
invalid value  
backend error

```

---

# 14. AI Chat Testing

AI chat must be tested.

Testing includes:

- message rendering
- context attachment
- task context passing
- errors
- streaming responses

---

# 15. LLM Testing Policy

Automated tests should not depend on live LLM calls.

Preferred:

- mocked AI responses
- manual verification

---

# 16. Input Testing

Inputs must test:

- allowed values
- invalid values
- unit selection
- unit display
- backend validation

---

# 17. Input Safety Rule

Frontend must not bypass backend validation.

Flow:

```

User input

↓

Frontend filtering

↓

Backend validation

↓

State update

```

---

# 18. Output Rendering Tests

Each output type requires tests.

Examples:

- equations
- tables
- graphs
- references
- warnings

---

# 19. Visual Testing

Screenshot comparison is not required initially.

Reason:

The application focuses on engineering correctness.

---

# 20. End-to-End Tests

The application should include complete user simulations.

Example:

```

Open application

↓

Create project

↓

Create task

↓

Complete workflow

↓

Export report

```

---

# 21. Test Frequency

E2E tests should run:

- during important development milestones
- before releases

---

# 22. Test Data

Engineering test cases should be stored separately.

Example:

```

testData/

pipeThicknessCases.json

materialCases.json

```

---

# 23. Expected Results

Test cases should include expected outputs.

Example:

```

Input

↓

Expected state

↓

Expected output

```

---

# 24. Debug Information

Failed tests should capture:

- failed action
- backend response
- task state
- frontend state
- logs

---

# 25. Debug Preservation

Failed tests should preserve enough information to reproduce issues.

---

# 26. Cursor Testing Rules

Cursor should:

- consider existing tests
- add tests when implementing features
- avoid deleting tests without explanation

---

# 27. Feature Completion

A feature is complete when:

- implemented
- tested
- documented

---

# 28. CI/CD Preparation

Testing should be compatible with future automation.

Future:

- automated checks
- release validation

---

# 29. Developer Principle

Never assume:

"tests pass = application works"

Critical workflows require:

- real execution
- manual inspection
- engineering validation

---

# 30. Final Principle

The test system protects the user workflow, not just the code.