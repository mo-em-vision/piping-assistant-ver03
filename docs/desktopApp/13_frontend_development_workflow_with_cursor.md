
# Frontend Development Workflow With Cursor

## 1. Purpose

This document defines how AI-assisted development should be performed.

The goal:

- maximize Cursor productivity
- maintain architecture consistency
- avoid uncontrolled changes
- keep the application maintainable

Cursor acts as an autonomous developer inside defined boundaries.

---

# 2. Cursor Responsibilities

Cursor should:

- understand the application architecture
- implement features
- debug issues
- improve code quality
- create tests
- maintain consistency

Cursor should not:

- ignore architecture rules
- move backend logic into frontend
- invent undocumented behavior

---

# 3. Documentation First Rule

Before implementing significant changes:

Cursor must read:

- desktop app vision
- architecture documentation
- relevant feature documentation

Documentation defines intended behavior.

---

# 4. Architecture Change Policy

Cursor may optimize:

- code organization
- implementation details
- component structure

Cursor must ask before changing:

- system architecture
- backend/frontend boundaries
- state management approach
- API contracts

---

# 5. Development Workflow

Preferred workflow:

```

Understand requirement

↓

Read documentation

↓

Inspect existing code

↓

Create implementation plan

↓

Modify code

↓

Test

↓

Explain changes

```

---

# 6. Feature Development

New features should be developed using:

```

Architecture

↓

Data flow

↓

Backend connection

↓

UI implementation

↓

Testing

```

---

# 7. Planning Before Large Changes

For large modifications Cursor should provide:

- files affected
- implementation approach
- expected behavior
- possible risks
- **Plan Review Gate** — mandatory section inside the plan (`docs/process/plan_review_gate.md`)

The Plan Review Gate is written for non-technical reviewers (project owner, CEO, product manager). Cursor ends with **READY_FOR_REVIEW**, **REVISE**, or **BLOCKED**. Only the project owner may set **APPROVED**.

**Do not implement** until the consistency review is **CLEAR**, the project owner sets **APPROVED**, and you give an explicit implementation instruction.

See `.cursor/rules/plan-review-gate.mdc` and `.cursor/rules/feature-planning.mdc`.

---

# 8. Code Modification Rules

Before editing:

Cursor should inspect:

- related files
- existing components
- services
- state management

Avoid:

- unnecessary refactoring
- renaming unrelated files
- deleting existing tests
- adding unnecessary dependencies

---

# 9. Refactoring Rules

If existing code is poor:

Cursor should fix it.

However:

Large refactors require explanation.

---

# 10. Backend Boundary

Frontend responsibilities:

- display data
- collect user input
- communicate with backend

Frontend must not contain:

- engineering formulas
- standards interpretation
- calculation logic

---

# 11. Missing Backend Functionality

If functionality belongs in backend:

Cursor should recommend:

- backend endpoint
- data structure change
- API modification

rather than duplicating logic.

---

# 12. Mock Data

Mock data is allowed for:

- UI development
- visualization testing

Mock data should not replace real engineering logic.

---

# 13. UI Development Rules

Cursor should prioritize:

- visual quality
- usability
- consistency

The application should maintain:

- clean layout
- minimal design
- engineering-focused UX

---

# 14. Ambiguous UI Decisions

When documentation is unclear:

Cursor should ask.

Do not guess important product behavior.

---

# 15. Dependencies

New packages should be minimized.

Before adding:

Cursor should consider:

- existing libraries
- maintenance
- long-term impact

---

# 16. Testing Workflow

After changes:

Cursor may explain changes.

Tests should be created for new features.

Test changes require approval.

---

# 17. Debugging Workflow

When errors occur:

Cursor should first inspect:

- error message
- data flow
- state
- backend response

Do not blindly modify code.

---

# 18. Debug Explanations

Fix explanations should include:

- root cause
- changed files
- expected behavior
- possible side effects

---

# 19. Git Workflow

Cursor may create commits.

Before committing:

ask user confirmation.

---

# 20. Branching

Branch strategy is flexible.

Cursor should not enforce a workflow without user decision.

---

# 21. Checkpoints

Before large changes:

recommend a checkpoint.

Example:

commit or backup.

---

# 22. Documentation Maintenance

When architecture changes:

documentation must be updated.

Updates can be performed by:

- Cursor
- user request

---

# 23. Code Quality

Priority:

Maintainable production-quality code.

Not only "working code".

---

# 24. Comments

Comments should exist for:

- complex logic
- non-obvious decisions

Avoid unnecessary comments.

---

# 25. AI Uncertainty Rule

When uncertain:

Cursor must ask.

Do not invent behavior.

---

# 26. Completion Verification

Cursor must verify:

"Does this actually work?"

before claiming completion.

---

# 27. User Skill Consideration

Since the user is not a professional programmer:

Cursor should:

- explain important concepts
- avoid unnecessary complexity
- provide clear summaries

---

# 28. Change Summaries

After modifications, Cursor should provide:

- what changed
- why
- affected files

---

# 29. Long-Term Compatibility

The workflow should support:

- more AI agents
- multiple developers
- professional software practices

---

# Final Principle

Cursor is an autonomous implementation partner.

The architecture documents define the boundaries.
