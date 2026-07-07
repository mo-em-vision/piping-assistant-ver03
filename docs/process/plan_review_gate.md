# Plan Review Gate

## Purpose

Every Cursor feature plan must include a built-in **Architecture Consistency Review** section and a **Plan Review Gate** section before implementation begins.

The reviews give a non-technical project owner, CEO, or product manager a plain-English check on whether a plan is:

- **Aligned** with Ver03 architecture (`docs/rules.md`)
- **Free of doc/architecture conflicts**
- **Safe** to build
- **Testable** with clear acceptance criteria
- **Ready** for implementation

Both sections live **inside Cursor's plan output** — not in a separate script, not in an external tool, not hidden in a side file.

**Cursor rule:** [`.cursor/rules/plan-review-gate.mdc`](../../.cursor/rules/plan-review-gate.mdc)  
**Planning workflow:** [`.cursor/rules/feature-planning.mdc`](../../.cursor/rules/feature-planning.mdc)

---

## When it applies

| Situation | Both sections required? |
| --- | --- |
| New feature plan | Yes |
| Large refactor plan | Yes |
| Plan mode / "do not implement yet" | Yes — in the same response |
| Single-line bug fix with obvious scope | Optional but recommended |
| User explicitly asks to skip planning | Only if user overrides; default is required for non-trivial work |

---

## Workflow

```
Feature request
      ↓
Cursor writes plan (scope, files, tests, acceptance criteria)
      ↓
Architecture Consistency Review (inside the plan)
      ↓
Plan Review Gate (inside the plan)
      ↓
┌─────────────┬──────────────┬─────────────┐
│  APPROVED   │    REVISE    │   BLOCKED   │
└─────────────┴──────────────┴─────────────┘
      ↓              ↓              ↓
 Implement      Revise plan    Resolve decisions
                                 with stakeholder
```

**Implementation is not allowed** when the Architecture Consistency Review is not **CLEAR**, or when the Plan Review Gate status is **REVISE** or **BLOCKED**.

---

## Architecture Consistency Review

Required **before** the Plan Review Gate. Full template: [`.cursor/rules/plan-review-gate.mdc`](../../.cursor/rules/plan-review-gate.mdc). Source rule: [`docs/rules.md`](../rules.md) §23.

### Status definitions

| Status | Meaning |
| --- | --- |
| **CLEAR** | No architectural conflicts detected |
| **NEEDS_DOC_UPDATE** | Docs are inconsistent but intended architecture is obvious |
| **NEEDS_DECISION** | Two sources of truth conflict with no clear winner |
| **BLOCKED** | Implementation would violate `docs/rules.md` |

If status is not **CLEAR**, the Plan Review Gate must be **REVISE** or **BLOCKED**, not **APPROVED**.

### Required fields

| Field | Meaning |
| --- | --- |
| Existing source files checked | Which docs/rules/code areas were checked |
| Possible conflicts found | Plain-English list of architectural inconsistencies |
| Conflicting source of truth | Which file/section wins (`docs/rules.md` by default) |
| Proposed resolution | What should be changed |
| User impact | Why this matters to the product owner |
| Risk if ignored | What failure would happen later |
| Required doc/rule/test updates | What must be edited before implementation |
| Status | CLEAR / NEEDS_DOC_UPDATE / NEEDS_DECISION / BLOCKED |

### Compliance checklist

Answer all ten questions in [`.cursor/rules/plan-review-gate.mdc`](../../.cursor/rules/plan-review-gate.mdc). Any violation → Plan Review Gate must not be **APPROVED**.

---

## Plan Review Gate status definitions

### APPROVED

- Architecture Consistency Review status is **CLEAR** (or required doc updates are included in the plan)
- Scope is clear and appropriately sized
- Architecture boundaries are respected
- Tests are defined (general + workflow + regression + user-visible)
- Allowed and forbidden file changes are listed
- Acceptance criteria are in plain English
- No unresolved product/architecture decisions

**Implementation Permission:** "Implementation allowed."

### REVISE

- Missing tests, unclear boundaries, wrong layer for the fix, or scope too broad
- Plan can be corrected without a fundamental product decision

**Implementation Permission:** "Implementation not allowed until the plan is revised."

### BLOCKED

- Plan is too vague, too large to review, or violates core architecture
- Required product or architecture decision is missing and cannot be inferred from docs

**Implementation Permission:** "Implementation blocked until the missing decision is resolved."

---

## Required sections

Every Plan Review Gate must include these headings in order:

1. **Status** — APPROVED / REVISE / BLOCKED
2. **Plain-English Summary** — 3–6 bullets
3. **Business/User Impact**
4. **Architecture Alignment**
5. **Main Risks**
6. **Missing Decisions**
7. **Test Coverage Required** (four groups)
8. **Documentation / Rules Updates Required**
9. **Out of Scope**
10. **Implementation Permission** — exactly one allowed sentence

Full template and example: [`.cursor/rules/plan-review-gate.mdc`](../../.cursor/rules/plan-review-gate.mdc).

---

## Architecture alignment checklist

Reviewers (human or Cursor) should verify the plan against existing docs — **do not invent new architecture**.

| Question | Source |
| --- | --- |
| Does engineering truth stay in the backend/graph? | [`docs/core/3. component_responsibilities.md`](../core/3.%20component_responsibilities.md) |
| Are workflow paths graph-driven, not hardcoded? | [`docs/rules.md`](../rules.md) §13 |
| Are prompts split between Planner (what) and Messaging (how)? | [`docs/rules.md`](../rules.md) §12 |
| Is traversal narration in the Flow Guidance Layer? | [`docs/rules.md`](../rules.md) §21 |
| Is the frontend thin (display + input only)? | [`docs/desktopApp/06_component_architecture.md`](../desktopApp/06_component_architecture.md) |
| Are transcript blocks append-only? | [`docs/rules.md`](../rules.md) §21 |

### Layer boundaries (summary)

| Layer | Decides | Does not decide |
| --- | --- | --- |
| Planner | What is needed next | Prompt wording, screen layout, calculations |
| Graph Engine | Active path from nodes/edges | Execution, UI copy |
| Execution | Deterministic runs | Workflow selection |
| Validation | Compliance | Calculations |
| Report | Output formatting | Engineering values |
| Flow Guidance | Traversal narration | Engineering truth |
| Messaging | Deterministic ask copy | Navigation |
| CLI / Desktop | Render blocks, collect input | Engineering rules |

---

## Status assignment rules

| Condition | Status |
| --- | --- |
| Architecture Consistency Review not **CLEAR** | REVISE or BLOCKED |
| Tests missing from plan | REVISE |
| Architecture boundaries unclear | REVISE |
| Plan touches unrelated layers | REVISE or BLOCKED |
| UI/output fix via Planner, Graph, Execution, or nodes (unjustified) | REVISE |
| General feature tested only on one workflow | REVISE |
| Hardcoding `pipe_wall_thickness_design` in general code | REVISE |
| Guidance/prompts in wrong layer | REVISE |
| Scope too broad without split steps | REVISE or BLOCKED |
| Missing product decision | BLOCKED |

---

## Relationship to other process docs

| Doc | Role |
| --- | --- |
| [`docs/Feature creation prompt template.md`](../Feature%20creation%20prompt%20template.md) | Feature contract and test-first steps; Plan Review Gate added before implementation |
| [`docs/core/12. Cursor Build Sequence (SAFE STEP-BY-STEP PLAN).md`](../core/12.%20Cursor%20Build%20Sequence%20(SAFE%20STEP-BY-STEP%20PLAN).md) | Historical build sequence; global "follow /docs" prefix |
| [`docs/desktopApp/13_frontend_development_workflow_with_cursor.md`](../desktopApp/13_frontend_development_workflow_with_cursor.md) | Cursor development workflow |
| [`docs/rules.md`](../rules.md) §6, §22, §23 | Goal-driven execution; Plan Review Gate; Architecture Consistency Review |

---

## Example (REVISE)

See full example in [`.cursor/rules/plan-review-gate.mdc`](../../.cursor/rules/plan-review-gate.mdc#example-plan-review-gate).

**Scenario:** A plan tries to keep previous equations visible by changing Planner logic.

**Verdict:** REVISE — display history belongs in the presentation/transcript layer, not the Planner.

---

## For human reviewers

When reading a Cursor plan:

1. Scroll to **Architecture Consistency Review** first — check **Status**.
2. If not **CLEAR**, send the plan back before checking the gate.
3. Scroll to **Plan Review Gate** — check **Status** and **Implementation Permission**.
4. If not APPROVED, do not approve implementation — send the plan back for revision.
5. Use **Business/User Impact** and **Main Risks** for stakeholder communication.
6. Use **Missing Decisions** as the agenda for the next planning conversation.
