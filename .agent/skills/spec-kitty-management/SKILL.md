---
name: spec-kitty-management
description: Master the spec-kitty workflow for implementing features through work packages.
---

# Spec-kitty Management Skill

This skill documents the optimized workflow for using `spec-kitty` to implement features in a structured, work-package-based approach.

## Prerequisites

**Virtual Environment**: `spec-kitty` requires the project's virtual environment to be active.

```bash
# From the repository root
source .venv/bin/activate
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
