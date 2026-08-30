---
name: build
description: Standard operating procedure for implementation work in this home-lab repo. Use for any non-trivial task — a new service, an architectural change, or a fix — that isn't a trivial one-line edit. Walks through Research, Decision, Planning, Implementation, and Verification phases, requiring issue docs, decision docs, and an approved plan before code changes land.
---

# Build Workflow

Standard operating procedure for agents performing implementation tasks in this repository.

Follow these phases in sequence for any non-trivial task. Skip straight to implementation only for trivial, obviously-safe one-line edits.

## Phase 1: Research & Analysis

- Explore the codebase to understand requirements.
- If a problem or bug is identified, **create an issue file** in the `issues/` directory before proceeding.
- Use the `Explore` agent for broad searches.

## Phase 2: Decision & Strategy

- For any new design choice, architectural change, or strategic pivot, **create a decision doc** in the `decisions/` directory.
- The decision doc must evaluate pros/cons and present options to the user.
- **Stop and wait for user feedback** on the decision doc. The user prefers reviewing decision docs and plans via the GitHub UI.

## Phase 3: Planning

- Once a decision is reached, update the decision doc with the final outcome, then enter `EnterPlanMode`.
- Create a detailed implementation plan in the `.claude/plans/` directory.
- Present the plan to the user for approval.

## Phase 4: Implementation

- Execute the plan.
- Ensure all changes are tested and verified.

## Phase 5: Verification & Cleanup

- Verify the implementation works as expected.
- Commit and push all changes to the repository.

## Compliance Requirements

- **Security First:** Always prioritize the security principles defined in `agent-guidelines.md` (least privilege, "Hardened Docker" strategies — capability stripping, non-root users, read-only mounts).
- **No Shortcuts:** Do not skip the `issues/` or `decisions/` steps for significant changes.
- **Atomic Commits:** Keep commits clean and descriptive.
