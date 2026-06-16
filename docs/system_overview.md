# System Overview

## Purpose

This document provides a high-level overview of the engineering assistant system.

The system transforms engineering standards into a searchable, executable knowledge graph.

The objective is to allow users to ask engineering questions naturally while maintaining:

- engineering traceability
- calculation transparency
- standard compliance
- reproducible results
- report generation


---

# 1. System Vision


Traditional engineering software follows predefined workflows.


This system uses a graph-based approach.


A user request becomes an engineering intent.

The intent activates a graph of required standards paragraphs.


The system discovers:

- applicable requirements
- required calculations
- dependencies
- decisions
- missing information


Then executes only what is required.


---

# 2. Example User Interaction


User:
```text
Verify the integrity of this pipe

Material:  
ASTM A106 Grade B

Temperature:  
400 F

Pressure:  
500 psi
```



The system identifies:

```text
Intent:

pipe_integrity_verification
```

The graph resolver finds:

```
Integrity Verification Root

|

+-- Material Stress

|

+-- Wall Thickness

|

+-- Pressure Rating

|

+-- Flexibility Requirement

|

+-- Pressure Test
```



---

# 3. Discovery Before Execution


The system never starts calculations immediately.


First it builds the complete execution graph.


Example:
```text
Step 1:

Find integrity_check/root.md

Step 2:

Read dependencies

Step 3:

Expand dependencies recursively

Step 4:

Build DAG

Step 5:

Identify missing information
```

The user can see:
```text
Discovered Analysis:

✓ Material allowable stress

✓ Wall thickness

✓ Pressure rating

✓ Flexibility

✓ Hydrotest

Missing:

Pipe outside diameter

Corrosion allowance
```



---

# 4. User Input Collection


Inputs are collected only after graph discovery.


The system knows:

- all required inputs
- which node requires them
- why they are required


Example:

```text
Required by:

ASME B31.3 §304.1.1

Input:

Outside Diameter

Reason:

Required for pressure thickness calculation
```



---

# 5. Conditional Engineering Logic


Engineering standards contain many conditions.


Example:


ASME B31.3:

```text
If calculated thickness is less than D/6

use thin wall equation

Otherwise:

use thick wall equation
```



The system records:

```text
Condition:

t < D/6

Result:

TRUE

Decision:

Proceed to §304.1.1
```




This decision becomes part of the final report.


---

# 6. Calculation Execution


After all information is available:


The execution engine runs the graph.


Example:

```text
Material Node

↓

Allowable Stress Output

↓

Wall Thickness Calculation

↓

Ordered Thickness

↓

Pressure Test Calculation
```



Each node produces:


- outputs
- warnings
- trace information


---

# 7. Dependency Passing


Outputs automatically flow between nodes.


Example:


Wall thickness calculation:


Produces:

```text
T_ordered = 2.34 mm
```

Pressure test node receives:

```
Source:

B313-304.1.1

Input:

T_ordered
```

No user re-entry is required.  
  
  
---  
  
# 8. Engineering Trace Model  
  
  
Every calculation creates a trace.  
  
  
Example:

```
Node:

B313-304.1.1

Purpose:

Calculate required wall thickness

Dependency:

Requires allowable stress

Input:

Pressure = 6 bar

Formula:

t = PD / 2(SEW+PY)

Output:

t = 2.34 mm
```



---

# 9. Report Generation  
  
  
The report system separates engineering truth from human presentation.  
  
  
The engineering engine creates a structured report model.  
  
The AI transforms this model into a readable engineering document.  
  
  
The AI does not perform any engineering interpretation.  
  
  
Flow:  
```
Execution Trace  
  
↓  
  
Report Data Model  
  
↓  
  
Report Template  
  
↓  
  
AI Presentation Layer  
  
↓  
  
PDF Report  
  
```
  

  
---  
  
# Report Data Model  
  
  
The report data model contains:  
  
  
- selected nodes  
- graph traversal path  
- dependency relationships  
- conditions evaluated  
- decisions made  
- formulas used  
- input values  
- calculation outputs  
- warnings  
- references  
  
  
Example:
```
Node:

B313-304.1.1

Reason:

Required because integrity verification requires pressure thickness calculation.

Condition:

Thin wall criteria evaluated.

Decision:

Continue with thin wall calculation.

Formula:

t = PD / 2(SEW+PY)

Result:

Required thickness = 0.065 in
```

---  
  
# AI Presentation Layer  
  
  
The AI receives the completed report information.  
  
  
The AI improves:  
  
  
- document structure  
- wording  
- explanations  
- readability  
  
  
The AI preserves:  
  
  
- all engineering values  
- formulas  
- warnings  
- decisions  
- references  
  
  
The AI is not allowed to rewrite engineering results.  
  
  ```
  Engineering Verification Report

1. Objective
2. Applicable Standards
3. Dependency Graph Traversal
4. Engineering Decisions
5. Calculations
6. Results
7. Warnings and Notes
8. Final Assessment
9. Traceability Appendix
  ```

---  
  
## Example  
  
  
### Pipe Integrity Verification  
  
  
#### 1. Scope and Objective  
  
  
The requested analysis was to verify whether the piping component satisfies  
the applicable ASME B31.3 pressure design requirements.  
  
  
The system evaluated the following areas:  
  
- required wall thickness  
- material allowable stress  
- pressure test requirements  
  
  
---  
  
#### 2. Analysis Path and Decisions  
  
  
The analysis started from:  
  
  
ASME B31.3 Integrity Verification Root  
  
  
The following dependency chain was identified:

```
Integrity Verification

↓

Material Stress Evaluation

↓

Wall Thickness Calculation

↓

Pressure Test Requirement
```

---  
  
#### 3. Engineering Decision Trace  
  
  
The wall thickness calculation required evaluation of the criteria in  
ASME B31.3 §304.1.1.  
  
  
The standard requires determining whether the thin-wall equation is applicable.  
  
  
Condition evaluated:
```
t < D/6
```
Result:  
  
  
TRUE  
  
  
Decision:  
  
  
The thin-wall pressure design equation was used.  
  
  
---  
  
#### 4. Calculation Results  
  
  
Inputs used:  
  
  
| Parameter | Value |  
|---|---|  
| Design Pressure | 500 psi |  
| Material | ASTM A106 Grade B |  
| Temperature | 400°F |  
  
  
Reference:  
  
  
ASME B31.3 §304.1.1  
  
  
Formula:

```
t = PD / 2(SEW+PY)
```

Calculated minimum thickness:  
  
  
0.065 in  
  
  
Required ordered thickness:  
  
  
0.109 in  
  
  
---  
  
#### 5. Warnings and Notes  
  
  
The following engineering notes were identified:  
  
  
- Standard mill tolerance allowance was applied.  
- Selected pipe thickness should be verified against the applicable product standard.  
  
  
---  
  
#### 6. Final Assessment  
  
  
The evaluated thickness satisfies the minimum pressure design requirement.  
  
  
Status:  
  
  
PASS  
  
  
---  
  
#### 7. Traceability Appendix  
  
  
Contains:  
  
  
- all executed nodes  
- dependency chain  
- formulas  
- input sources  
- standard references  
- decision history
---

# 11. Report Storage


Generated reports are stored per session.


Example:

```
sessions/

12345/

reports/

integrity_report.pdf
```



Reports can be regenerated from stored state.


---

# 12. Conversation Memory


Each chat session maintains:


- conversation history
- task state
- graph state
- calculations
- reports


Example:

```
session/

conversation.json

events.json

task_state.json

report_history/
```



A future message can continue the same engineering task.


---

# 13. Multi Standard Support


The architecture supports multiple engineering standards.


Example:

```
standards/

asme_b31.3/

api_570/

api_650/

bpvc_section_viii/
```

Each standard contains:

```
index.md

nodes/

tables/

figures/

templates/

roots/

reports/
```



---

# 14. Node Knowledge Model


Every standard paragraph becomes a node.


A node contains:


- paragraph identity
- standard text
- applicability
- dependencies
- formulas
- decisions
- outputs
- report instructions


The node is the smallest engineering knowledge unit.


---

# 15. AI Response Layer


The AI receives:


- user question
- current state
- graph status
- calculation results
- report data


The AI creates:


- explanations
- answers
- summaries
- follow-up questions


The AI does not modify engineering logic.


---

# 16. Future Expansion


The same architecture can support:


- piping design
- pressure vessels
- tanks
- inspection
- fitness-for-service
- mechanical calculations


New standards are added by creating new node graphs.


---

# Final System Concept


The system is:


A standards-based engineering knowledge graph with:

- AI interaction
- dependency traversal
- calculation execution
- traceable reporting


Every engineering conclusion can be traced back to:

standard paragraph → decision → formula → output → report
