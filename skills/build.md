# Agent Workflow: The "Build" Skill

This document defines the standard operating procedure for agents performing implementation tasks.

## The "Build" Workflow

Agents should follow these steps in sequence for any non-trivial task:

1.  **Phase 1: Research & Analysis**
    - Explore the codebase to understand requirements.
    - If a problem or bug is identified, **create an issue file** in the `issues/` directory before proceeding.
    - Use the `Explore` agent for broad searches.

2.  **Phase 2: Decision & Strategy**
    - For any new design choice, architectural change, or strategic pivot, **create a decision doc** in the `decisions/` directory.
    - The decision doc must evaluate pros/cons and present options to the user.
    - **Stop and wait for user feedback** on the decision doc.

3.  **Phase 3: Planning**
    - Once a decision is reached, enter `EnterPlanMode`.
    - Create a detailed implementation plan in the `.claude/plans/` directory.
    - Present the plan to the user for approval.

4.  **Phase 4: Implementation**
    - Execute the plan.
    - Ensure all changes are tested and verified.

5.  **Phase 5: Verification & Cleanup**
    - Verify the implementation works as expected.
    - Commit and push all changes to the repository.

## Compliance Requirements

- **Security First:** Always prioritize the security principles defined in `agent-guidelines.md`.
- **No Shortcuts:** Do not skip the `issues/` or `decisions/` steps for significant changes.
- **Atomic Commits:** Keep commits clean and descriptive.
