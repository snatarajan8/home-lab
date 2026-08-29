# Agent Guidelines

These guidelines apply to all AI agents performing work within this repository.

## Core Principles

When performing any task, agents must prioritize the following:

1.  **Security:** Implement the principle of least privilege. Use "Hardened Docker" strategies (capability stripping, non-root users, read-only mounts) whenever deploying services.
2.  **Simplicity:** Favor standard, well-supported tools and configurations over complex, custom-built solutions.
3.  **Robustness:** Design for failure. Ensure services have appropriate restart policies, resource limits, and error handling.

## Workflow Requirements

Before implementing any significant change or new feature, agents **must** follow this protocol:

1.  **Document Issues:** For every new problem, bug, or technical hurdle encountered, create a detailed analysis file in the `issues/` directory. This file should include evidence, technical observations, and a root cause analysis.
2.  **Document Decisions:** For every new architectural choice, design pattern, or strategic pivot, create a documentation file in the `decisions/` directory. This file must capture the context, the alternatives considered, and the rationale for the chosen path.
3.  **Plan implementation:** For non-trivial tasks, create an implementation plan (using `EnterPlanMode`) and obtain user approval before making changes to the codebase.
