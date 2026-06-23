# AI Interaction Design

## 1. AI Philosophy

The AI assistant is a professional engineering assistant and tutor.

It is designed to help engineers:

- navigate standards
- understand engineering concepts
- discover workflows
- interpret requirements
- prepare reports
- interact with engineering knowledge

The AI is not the source of engineering truth.

Engineering truth comes from:

- standards
- deterministic calculations
- verified engineering logic
- traceable references

---

# 2. AI Role

Primary AI roles:

1. Expert engineering assistant
2. Engineering tutor
3. Standards search assistant
4. Calculation workflow assistant
5. Automation assistant
6. Engineering knowledge navigator

---

# 3. AI Responsibilities

The AI may:

- explain engineering concepts
- explain formulas
- interpret standards
- locate relevant requirements
- answer engineering questions
- guide users through workflows
- generate report explanations
- recommend related engineering actions

---

# 4. AI Restrictions

The AI must never:

- perform engineering calculations independently
- invent standards references
- create unsupported engineering conclusions
- modify calculations without approval
- silently make engineering assumptions
- replace deterministic engineering logic

---

# 5. AI Entry Experience

The application starts with AI interaction available.

The user can:

- ask engineering questions
- search standards
- request calculations
- start workflows

The AI detects user intent and guides the user toward the correct engineering task.

---

# 6. Intent Detection

The AI should detect:

- engineering questions
- calculation requests
- standard lookup requests
- report generation requests
- explanation requests
- workflow continuation
- unrelated questions

Intent detection is handled in the backend AI system.

---

# 7. Intent Processing

When the user requests engineering work:

The AI should:

1. Understand user intent
2. Ask required clarification questions
3. Evaluate possible workflows
4. Identify matching task
5. Present the planned path
6. Request user confirmation

Example:

```

Detected task:

Pipe Thickness Calculation

Steps:

1. Select standard
    
2. Define material
    
3. Enter design conditions
    
4. Calculate required thickness
    
5. Generate report
    

Start?

```

The user must approve before the task begins.

---

# 8. AI Task Creation Behavior

The AI should suggest task creation rather than silently starting workflows.

The user remains in control.

---

# 9. Task Input Handling

During active engineering tasks:

The center panel should prioritize structured inputs.

The user should not enter free-form text inside parameter collection steps.

Instead:

The system should provide:

- selectable options
- validated fields
- unit selection
- predefined choices

This minimizes:

- incorrect inputs
- ambiguous states
- unnecessary AI calls

---

# 10. AI Panel Separation

During active tasks:

The AI assistant moves to the right panel.

Purpose:

- preserve task clarity
- separate calculation workflow from conversation
- reduce unnecessary LLM calls

The center panel focuses on:

- inputs
- calculations
- outputs

The right panel focuses on:

- AI assistance
- explanations
- questions

---

# 11. Parameter Modification

Users may modify task parameters.

Parameter editing is available through:

- task state panel
- editing controls

When parameters are changed:

The system must:

1. Ask confirmation
2. Warn about calculation impact
3. Explain affected workflow states
4. Restart affected calculations when required

Example:

```

Pressure changed:

20 bar → 30 bar

This affects:

- thickness calculation
    
- stress evaluation
    

Recalculate from beginning?

```

---

# 12. Task Versioning

When significant values change, users should have the option to:

- update current task
- create a new task version

The original task should remain preserved.

This prevents loss of previous engineering states.

---

# 13. AI Context Management

AI context should be dynamically selected.

The AI may receive:

- current task
- current node
- previous opened nodes
- calculation outputs
- relevant standards information
- project context
- user interaction history

---

The application should not send unnecessary information.

Context selection should be:

Hybrid:

- automatically selected
- controlled by application logic

---

# 14. AI Memory

The AI should maintain useful context.

Memory may include:

- current task behavior
- user interaction patterns
- preferences
- previous relevant discussions

The purpose is to improve assistance quality.

---

# 15. LLM Call Optimization

Not every action requires AI.

Simple operations should be deterministic.

Examples:

No AI required:

- unit conversion
- parameter selection
- validation
- calculations
- navigation

AI required:

- intent detection
- explanations
- standards interpretation
- report generation
- recommendations
- conversation

---

# 16. AI Modes

The application should support different explanation depths.

Example:

Simple mode:

- concise explanation
- key result

Professional mode:

- detailed engineering explanation
- formulas
- assumptions
- references

---

# 17. Engineering Traceability

Inside tasks:

AI responses should show:

- standard reference
- paragraph
- table
- figure
- assumptions
- limitations

References should always be visible.

---

# 18. Free Question Handling

For general engineering questions:

The AI should verify responses against available engineering knowledge sources.

If information is incomplete:

The AI should:

1. Ask for missing information
2. Present possible interpretation paths
3. Explain differences

The AI should avoid unsupported answers.

---

# 19. AI During Tasks

During engineering workflows AI acts as:

- tutor
- co-pilot
- guide

The AI understands:

- current task stage
- current workflow node
- calculation status

---

# 20. Next Actions

The AI may suggest:

Examples:

```

Calculation complete.

Suggested next actions:

[Generate Report]  
[Review Assumptions]  
[Check Material]

```

---

# 21. Report Generation

AI assists report generation.

Preferred approach:

Template-based report generation with AI assistance.

AI may help:

- write explanations
- summarize results
- improve clarity

The engineering content remains traceable.

---

# 22. AI Interface Features

The AI interface should support:

- text selection → Ask AI
- contextual explanations
- right-click explanation
- suggested prompts
- follow-up questions

When selected text is explained:

The system should include:

- selected content
- task context
- project context
- current state

---

# 23. Final AI Definition

AI in this application is:

"A professional engineering assistant and tutor, not a source of engineering truth."

The AI improves:

- accessibility
- understanding
- navigation
- workflow efficiency

while engineering logic remains deterministic and traceable.
