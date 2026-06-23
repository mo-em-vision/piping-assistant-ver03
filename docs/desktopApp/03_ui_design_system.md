# UI Design System

## 1. Design Vision

The application should look like a modern AI productivity application while behaving like an engineering knowledge platform.

Design inspiration:

- Cursor
- ChatGPT
- modern desktop productivity tools

The interface should combine:

- minimal and beautiful UI
- engineering clarity
- structured workflows
- AI-assisted interaction

The primary design statement:

"The application should look like Cursor but behave like an engineering knowledge platform assistant."

---

# 2. Visual Identity

## Design Style

Selected style:

Modern AI application

The interface should prioritize:

1. Clean and minimal UI
2. Beautiful appearance
3. Engineering information density
4. Speed of interaction
5. Accessibility
6. Customization

The design should avoid:

- excessive visual elements
- dashboard clutter
- unnecessary decoration

---

# 3. Theme System

The application supports:

- Light mode
- Dark mode

Default:

Light mode

The user can switch themes using a dedicated toggle.

---

## Light Theme Direction

Primary appearance:

- white background
- shades of grey
- subtle contrast
- minimal accent colors

Accent colors should be used sparingly.

Example:

Light blue accents for:

- important actions
- selected states
- AI-related elements

---

## Dark Theme Direction

Dark mode should maintain the same design philosophy:

- minimal contrast
- comfortable reading
- professional appearance

The theme should not become visually aggressive.

---

# 4. Layout Style

The application should follow a Cursor-like workspace layout.

Panels should feel integrated into a single workspace rather than separate dashboard cards.

Main structure:
```
Left Navigation | Main Workspace | Context Panel
```

The layout should support:

- resizing
- collapsing
- focus mode

---

# 5. Spacing and Density

The UI uses a balanced spacing approach.

Goals:

- enough whitespace for readability
- enough density for engineering workflows

The application should avoid:

- excessive empty space
- overly compact interfaces

---

# 6. Components

The UI should use reusable components.

Examples:

## Buttons

Style:

- icon + minimal text

Examples:

- Create Task
- Generate Report
- Ask AI

Buttons should avoid unnecessary descriptions.

---

## Cards

Used for:

- results
- summaries
- task status
- engineering information

Cards should remain simple.

---

# 7. Typography

Font style:

Modern clean typography.

Goals:

- easy reading
- professional appearance
- technical clarity

The interface should support:

- different text sizes
- accessible reading

---

# 8. Equation Rendering

Engineering formulas should have dedicated visualization.

The application should support mathematical rendering.

Preferred behavior:

Display equations clearly using tools such as KaTeX.

Example:
```
t = PR / (SE - P)
```
Equations should appear as part of engineering explanations and calculation results.  
  
---  
  
# 9. Input Design  
  
Inputs should follow compact engineering style.  
  
Example:
```
Pressure

[ 100 ] [bar ▼]
```


The interface should prioritize:

- quick entry
- clarity
- unit awareness

---

## Parameter Information

Inputs should provide:

- description
- units
- allowed range
- assumptions
- references

when available.

---

## Validation Behavior

Validation should occur after user attempts calculation.

The system should avoid excessive interruption while typing.

---

## Engineering Hints

Inputs may provide contextual assistance.

Example:
```
Pressure

Recommended range:  
10-200 bar

Reference:  
ASME B31.3
```

---

# 10. Results Display

Results should use a hybrid approach.

Default:

Simple result cards.

Example:
```
Required Thickness

12.4 mm
```

The user can expand details.

---

Expanded results should show:

- formula
- inputs
- assumptions
- references
- calculation details

---

# 11. Calculation Transparency

Every engineering result should support traceability.

Example:
```
Result:  
12.4 mm

Formula:  
...

Reference:  
ASME B31.3 Section ...
```

Users should be able to inspect:  
  
- formulas  
- assumptions  
- calculation logic  
- standard references  
  
---  
  
# 12. Expandable Engineering Details  
  
Complex information should be progressively revealed.  
  
Example:
```
Result  
|

- Formula  
    |
- Inputs  
    |
- Reference  
    |
- Calculation Steps
```


The default view should remain simple.

---

# 13. Tables

Tables should use a modern engineering style.

Preferred:

Modern tables + information cards.

Tables should support:

- searching
- filtering
- sorting

---

# 14. Visualization

The application should support:

- charts
- pressure/temperature plots
- engineering diagrams
- drawings
- progress graphs

---

## Graph Behavior

Preferred:

Interactive when possible.

Features may include:

- zoom
- hover information
- value inspection

If interaction is unnecessary:

Use simple static visualization.

---

# 15. AI Assistant Interface

The AI interface should have two styles.

---

## General AI Mode

When no task is active:

The AI interface can resemble ChatGPT.

Purpose:

- engineering questions
- discovery
- task initiation

---

## Task AI Mode

When inside a task:

The AI behaves as an engineering assistant.

Responses should support structured blocks:

Example:
```
Explanation

Formula

Reference

Suggested action
```


---

# 16. Context-Aware AI Interaction

Users should be able to select text and request AI assistance.

Example:

User highlights:

"allowable stress"

Action:

"Ask AI"

The system sends:

- selected text
- active task
- project context
- relevant state

to the AI assistant.

The AI should explain concepts using the current engineering context.

---

# 17. AI Message Actions

Task messages should support:

- text selection
- copy
- further explanation
- context-aware questioning

Future support:

- export
- save to report

---

# 18. Controls

Controls should use:

- icons
- minimal text

Inspired by:

- Cursor
- ChatGPT

Important actions should remain obvious.

---

# 19. Confirmation Behavior

Confirmation is required only for dangerous actions.

Examples:

Require confirmation:

- deleting tasks
- deleting projects
- destructive operations

Do not require confirmation:

- normal navigation
- opening panels
- viewing information

---

# 20. Keyboard and Mouse Interaction

The application should support keyboard usage.

The application should also remain fully usable with a mouse.

---

# 21. User Modes

Initial version:

Single interface for all users.

The application should not create separate beginner/expert modes.

The same interface should support different user experience levels.

---

# 22. Final UI Principle

The application should:

- feel like Cursor
- provide engineering intelligence
- minimize clicks
- reveal complexity only when needed
- keep engineering information traceable

The UI is a bridge between engineers and standards-driven workflows.