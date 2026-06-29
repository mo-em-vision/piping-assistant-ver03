# 1. Read before you write

Read the files you are about to touch; read, not skim. copy the patterns that already exist, and check the imports to see what the project actually depends on, so you do not reach for axios where everything is fetched. when you cannot find a pattern, ask instead of guessing. 

# 2. Think before you code
Figure out what you are doing before you type. state your assumptions ("add Authentication" is five different things, so name the one you picked) and name the tradeoffs. if something is genuinely confusing, stop and ask rather than filling the gap with plausible looking code; that is exactly the code that passes a casual review and fails when it matters.

# 3. simplicity
write the minimum code that solves the problem in front of you now, not the minimum that could solve every future version of it. Resist premature abstraction, skip error handling for errors that cannot occur, and hardcode values until there is a real reason to configure them. the test: if the only reason something is abstracted is "in case we need to," you have over-built it.

# 4. subcritical changes
your diff should be as small as the task allows. do not touch what you were not asked to touch, march the existing style, and do not reformat; a formatter pass buries the three lines that matter inside three hundred that do not. the test is whether you can justify every changed line by the task. if a line is there because "while I was in there" revert it.

# 5. verifications
the gap between code that works and code you think works is testing. when fixing a bug, write the failing test, watch it fail, then fix it; that is the only proof you fixed the cause and not the symptom. Test behavior that can actually break, not that a constructor sets a field. if something is hard to test, that is information about the design, not permission to skip it.

# 6. goal-driven execution
every task needs a success criterion before code is written. " add validation" becomes "rejected a missing or malformed email, return 400 with clear message, and test both cases". for anything multi-step, state the plan first so the user can catch a wrong approach before you spend an hour building it.

# 7. Debugging
when something breaks, investigate; do not guess. Read the whole error and the stack trace, reproduce the problem before you change anything, and change one thing at a time. Do not paper over an unexpected null with a null check; find out why it is null, or the bug just moves somewhere quieter.

# 8. Dependencies
every dependency is permanent code you do not control. before adding one, ask whether the project or the standard library can already do it with crypto.randomUUID() over UUID package. when you do add one, say why, so the choice is visible rather than smuggled into the manifest.

# 9. Communication
say what you did and why, not just a block of code. flag concerns even when you did exactly what was asked, and be precise about uncertainty: "I am not sure this library supports streaming" tells the user what to verify; "I think this should work" does not.

# 10. common failure modes
a few patterns recur often enough to name: the Kitchen Sink (restructuring half the codebase while you are at it), the Wrong Abstraction (copy-paste twice before you abstract), the Optimistic Path (the happy path handled and the 500 ignored), and the Runaway Refractor (a fix that cascades across files). Catch yourself in any of these and the right move is to stop, not to push through.

# 11. node structure
when a workflow/task is initiated only node data should be read. avoid hardcoding conditionals, text output, table outputs or conditions on external files. there should not be a separate file for each node, but rather workflows/tasks should be defined in root nodes, and the graph traversal/outputted data, text, tables, figures, etc should only be read from the node contents. there should be node templates which should be used for creating new nodes. when I have included something in the node that does not fit in the current node template, ask me to confirm the addition of the feature to the node template and structure. 