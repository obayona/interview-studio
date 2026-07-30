You completed phase 5
Now proceed with phase 6.

Context:
- Specifications in @AGENT.md (functional source of truth)
- Implementation plan in @PLAN.md (mandatory execution order)
- System Current State @MAP.md
- You have to follow the implementation plan strictly, not re-planning.

Conflict Hierarchy:
1. @AGENT.md (what to build)
2. @PLAN.md (how to build)
3. @MAP.md (system current state)

Execution rules:
- First query @MAP.md before start tasks.
- Perform tasks in the exact order.
- Don't enter in plan mode, unless it is stricly necessary
- Only ask for technical blockers.

Mandatory SDD Rules:
- After each relevant change, update @MAP.md with:
- changes made
- new modules / routes / entities
- technical decisions made
- impact on the system

Consistency check:
- Don't invent status in @MAP.md
- If there is a discrepancy between code and map, the code has priority and the map must be corrected.

Scope:
- Keep changes within the current phase.
- Do not modify functionalities outside the scope of the phase we are developing, except direct dependency.

Expected output:
- Mark each sub-task as completed.
- At the end of the phase: 
- summarizes what was implemented 
- completely synchronizes MAP.md with the real state of the system 
- mark the phase as completed (on the map, in the tasks and in the implementation plan)
