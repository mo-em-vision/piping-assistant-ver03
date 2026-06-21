# Desktop Application Vision

## 1. Product Identity

### Project Name

Temporary project name:

[Future Product Name]

The application name should not be restricted to a single engineering discipline because the long-term vision includes multiple engineering domains such as piping, pressure vessels, tanks, flanges, and other standards-driven design activities.

The name should represent an AI-assisted engineering platform rather than only a piping-focused tool.

---

## 2. Product Mission

The application is an AI-assisted engineering workspace designed to help engineers:

- ask engineering questions
- search and interpret engineering standards
- perform standards-based calculations
- understand engineering concepts
- generate professional engineering reports

The application combines artificial intelligence with structured engineering workflows to reduce the time engineers spend searching through standards, interpreting requirements, and manually preparing calculations and reports.

---

## 3. User Problem

Engineering standards such as ASME, API, and ASTM contain large amounts of technical information distributed across complex documents.

Engineers commonly face challenges including:

- spending excessive time searching through standards texts, tables, figures
- finding relevant paragraphs and requirements
- interpreting standards for specific engineering scenarios
- connecting formulas, tables, assumptions, and requirements
- manually preparing calculation reports
- maintaining traceability between engineering decisions and standards

The application aims to make engineering knowledge easier to access while preserving engineering accuracy and transparency.

---

## 4. Target Users

### Primary Users

The initial target users are mechanical engineers working with standards such as:

- ASME standards
- API standards
- ASTM material standards

Example application areas:

- process piping design
- flange selection
- pressure vessel related calculations
- tank design
- refinery engineering applications

The platform should remain flexible enough to expand into additional engineering disciplines.

---

### User Experience Level

The application should support mixed experience levels:

- junior engineers
- experienced engineers
- engineering specialists

The system should assist users without requiring programming knowledge or the ability to manually create engineering formulas.

---

## 5. Core User Experience

The application follows a workspace-based approach inspired by modern AI development environments.

The user begins with an AI interaction or an existing project.

The general workflow:

1. User opens application
2. User can:
   - start a conversation with AI
   - create a new project
   - open a previous project
3. AI detects engineering intent
4. When an engineering task is identified, the application opens a structured task workspace
5. The user completes the engineering workflow through guided inputs
6. Calculations are performed through deterministic engineering logic
7. Results are displayed with explanations and references
8. Professional engineering reports can be generated

---

## 6. Application Interaction Philosophy

The application is not primarily a chatbot.

The AI conversation is an entry point into structured engineering workflows.

The application should behave similarly to an AI-powered engineering IDE:

- conversation starts the interaction
- structured workspace performs the engineering task
- AI remains available as a contextual assistant

When a task is active:

The center workspace should focus on:

- task inputs
- calculation progress
- results
- engineering information

The AI assistant should move into a dedicated panel where it can:

- answer questions
- explain concepts
- provide guidance
- assist the user during the workflow

---

## 7. AI Assistant Philosophy

The AI assistant acts as:

- engineering tutor
- standards interpreter
- workflow assistant
- report generation assistant

The AI should help engineers understand and navigate engineering knowledge.

---

### AI Responsibilities

The AI may:

- explain engineering concepts
- explain formulas
- explain parameters
- explain tables and requirements
- interpret standards
- suggest next steps
- assist during engineering workflows
- generate engineering reports
- recommend related actions after task completion

---

### AI Limitations

The AI should not:

- replace deterministic engineering calculations
- invent engineering values
- provide unsupported engineering recommendations
- hide calculation logic
- provide answers without references

The application must avoid becoming an unreliable chatbot.

---

## 8. Engineering Trust Model

Engineering reliability and traceability are core principles.

Every engineering output should be traceable.

The application should maintain links between:

- assumptions
- formulas
- calculations
- tables
- requirements
- final results

Each relevant engineering statement should reference the related standard source whenever possible.

Example:

Result:

Required thickness:
X mm

Should include:

Reference:
Relevant standard

Paragraph:
Applicable section

Calculation:
Formula and inputs used

The purpose is not to replace engineers checking standards, but to help engineers quickly locate and understand the applicable requirements.

---

## 9. Calculation and Standards Philosophy

The application follows a deterministic calculation approach.

Engineering logic should be based on:

- documented formulas
- engineering rules
- standards requirements
- verified lookup data

The AI should provide the interface and explanation layer.

The calculation engine remains the source of truth.

The application should favor:

- modular systems
- transparent logic
- explicit assumptions
- explainable results

over:

- hidden AI-generated behavior
- uncontrolled automation
- black-box decisions

---

## 10. Reporting Vision

The application should generate professional engineering reports.

Reports should include:

- project information
- task description
- user inputs
- assumptions
- applicable standards
- formulas
- calculation steps
- intermediate results
- final results
- engineering notes
- references

Reports should be suitable for engineering review and documentation purposes.

---

## 11. Long-Term Product Direction

The long-term goal is to create an industry-standard engineering platform where AI assists engineers in the same way modern AI coding tools assist programmers.

Future capabilities may include:

- multiple engineering disciplines
- company engineering databases
- cloud synchronization
- collaboration features
- mobile access

The platform should become a central engineering workspace rather than a collection of independent calculation tools.

---

## 12. Success Criteria

Initial success:

The application can:

- detect user intent
- guide a user through one complete engineering workflow
- execute a standards-based calculation
- generate a traceable engineering report

Long-term success:

The application becomes useful enough that engineering teams adopt it as part of their daily design process.

A practical milestone is having multiple engineers use the platform to assist their engineering activities.

---

## 13. Product Boundaries

The application should never become:

- an unreferenced AI answer generator
- a replacement for engineering judgment
- a black-box calculation system

All engineering outputs must prioritize:

1. Accuracy
2. Transparency
3. Ease of use
4. Speed
5. Clean user experience

---

## 14. Development Principles

The application should be developed with the following principles:

1. Build deterministic engineering foundations first.
2. Keep AI as an assistance layer.
3. Avoid unnecessary AI calls.
4. Use structured workflows instead of free-form interpretation where possible.
5. Make every engineering decision traceable.
6. Prefer simple, modular architecture.
7. Avoid excessive complexity caused by AI-generated code.
8. Ensure the system remains understandable and maintainable by humans.
