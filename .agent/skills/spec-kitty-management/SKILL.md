---
name: spec-kitty-management
description: Master the spec-kitty workflow for implementing features through work packages.
---

# Spec-kitty Management Skill

This skill documents the optimized workflow for using `spec-kitty` to implement features in a structured, work-package-based approach.

## Finding and Activating `spec-kitty`

`spec-kitty` is typically installed within the project's virtual environment. If it's not immediately visible in your path, follow these steps:

### 1. The "Golden Rule" (Same Shell Session)

Agents often get "command not found" because they source the venv in one command and try to run `spec-kitty` in another. **You must do both in the same command string.**

```bash
# CORRECT
source .venv/bin/activate && spec-kitty agent tasks move-task WPXX --to doing

# INCORRECT (Path changes won't persist across tool calls)
source .venv/bin/activate
spec-kitty ...
```

### 2. Manual Invocation

If the binary is still not found, it is likely registered under the `spec-kitty-cli` package. Try invoking it directly through Python:

```bash
source .venv/bin/activate && python -m spec_kitty_cli agent ...
```

### 3. Verification

Verify it's active by checking the version:

```bash
source .venv/bin/activate && spec-kitty --version
```

## Task Lifecycle

Always move tasks through the correct lanes to maintain consistency and keep the team (and automation) updated.

### 1. Starting a Work Package (Moving to `doing`)

When you select a WP to implement, move it to the `doing` lane. This captures your shell PID and creates a git commit.

```bash
spec-kitty agent tasks move-task <WPID> --to doing --note "Started implementation" --agent "your-name"
```

*Example:* `spec-kitty agent tasks move-task WP03 --to doing --note "Starting pipeline logic" --agent "antigravity"`

### 2. Implementation Guide

The WP file contains the most critical information for implementation. Find it at:
`kitty-specs/<feature-name>/tasks/<WPID>-<slug>.md`

**Scrutinize the following sections:**

- **Objective**: High-level goal.
- **Subtasks**: Granular list of IDs (e.g., T001, T002).
- **Review Feedback**: If `review_status: has_feedback` is in the frontmatter, ALWAYS read this first.

### 3. Completing a Work Package (Moving to `for_review`)

Once subtasks are complete and verified (tests passing):

```bash
spec-kitty agent tasks move-task <WPID> --to for_review --note "Implementation complete and verified"
```

## Directory Structure

- `kitty-specs/`: Contains all feature specifications.
- `tasks.md`: The central task list for a feature.
- `tasks/`: Individual prompt files for each Work Package.

## Best Practices

- **Read supporting docs first**: Consult `spec.md` and `plan.md` in the feature directory before writing code.
- **Commit as you go**: Make small, logical commits for each subtask or major milestone within a WP.
- **Verification is mandatory**: Never move to `for_review` without running relevant tests or manual verification scripts.
- **Handle Linting**: Check for lint errors frequently. Use `spec-kitty` to validate readiness if a pre-review check command is available.
- **Check Task Status**: If you are unsure what to do next, run `spec-kitty agent tasks list` (or similar) to see the current state of the feature.
- **Work Package Objective**: Each WP file has a `## Objective` section. This is your primary source of truth for "What am I building?".
