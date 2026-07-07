# 1. first step
Strictly follow /docs. Do NOT invent new architecture. Do NOT rename components. If something is missing, stub it.  
  
I want to implement this feature:  
  
[FEATURE NAME]  
  
Feature contract:  
[PASTE CONTRACT]  
  
Affected layers:  
[LIST LAYERS]  
  
Rules:  
1. Do not implement yet.  
2. First inspect the current code and identify the exact modules involved.  
3. Produce a test plan with:  
- unit tests  
- component contract tests  
- integration tests  
- regression-risk tests  
4. For each test, state:  
- file path  
- test name  
- given/when/then behavior  
- why this test is necessary  
5. End the plan with an **Architecture Consistency Review** then a **Plan Review Gate** (`docs/process/plan_review_gate.md`, `.cursor/rules/plan-review-gate.mdc`, `docs/rules.md` §22–§23). Write both for a non-technical reviewer. Consistency review must be **CLEAR** and gate status **APPROVED** before step 3 (implementation).  
6. Do not modify production code in this step.

# 2. Feature contract template
Feature:  
[Name of the feature]  
  
Purpose:  
[Why this feature exists]  
  
User-visible behavior:  
[What the user should see or experience]  
  
Owned components:  
[List files/modules that are allowed to change]  
  
Inputs:  
[What the feature receives]  
  
Outputs:  
[What the feature must return/display/store]  
  
State changes:  
[What task/session/graph/execution state should change]  
  
Must do:  
1.  
2.  
3.  
  
Must not do:  
4.  
5.  
6.  
  
Acceptance tests:  
7.  
8.  
9.  
  
Failure cases:  
10.  
11.  
12.  
  
Out of scope:  
13.  
14.  
15.  
  
Definition of done:  
- Tests added  
- Tests pass  
- Manual scenario verified  
- No unrelated architecture changed  
- No layer boundary violated
# 3. after reviewing the tests
Strictly follow /docs. Do NOT invent new architecture. Do NOT rename components. If something is missing, stub it.  
  
The Architecture Consistency Review must be **CLEAR** and the Plan Review Gate status **APPROVED** before this step. If either fails, stop and revise the plan.  
  
Now implement only the minimum production code required to pass the approved tests.  
  
Rules:  
1. Do not change unrelated files.  
2. Do not change public interfaces unless the tests require it.  
3. Do not hardcode the test cases.  
4. Preserve layer boundaries:  
- Planner does not calculate.  
- Graph does not execute.  
- Validation does not calculate.  
- Execution does not select workflow.  
- Report does not modify values.  
- AI does not define engineering truth.  
5. After implementation, report:  
- files changed  
- tests run  
- failures fixed  
- remaining limitations