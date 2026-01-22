---
work_package_id: WP07
title: Documentation & Final Polish
lane: planned
dependencies: []
subtasks:
- T029
- T030
- T031
---

## Objective

Finalize the feature by ensuring users have documentation (which powers the RAG assistant) and all system messages are consistent. Perform a final verification pass.

## Context

The feature is coded, but if the "Product Assistant" doesn't know about it, users won't discover it. We need to update the manuals.

## Detailed Guidance

### Subtask T029: Update src/assets/manual.md with QuickBooks integration guides

**Purpose**: Update the RAG source.
**Files**: `src/assets/manual.md`
**Instructions**:

1. Add section "QuickBooks Integration".
2. Explain:
    - How to connect.
    - What is synced (one-way, entities).
    - Sync frequency (HOURLY).
    - How to view status/errors.
    - Common issues (validation errors).

### Subtask T030: Update src/assets/messages.yaml with all new response templates

**Purpose**: Centralize user-facing strings.
**Files**: `src/assets/messages.yaml`
**Instructions**:

1. Review code from WP06.
2. Move hardcoded strings to `messages.yaml` (if pattern is followed).
3. Ensure tone is consistent (Professional, helpful).

### Subtask T031: Perform final end-to-end verification and checklist run

**Purpose**: Human/Agent validation.
**Files**: `COMMIT_ReadMe.md` (or similar output)
**Instructions**:

1. Run all tests: `pytest tests/`.
2. Check for lint errors.
3. Verify no strict dependencies were violated.
4. Write a brief "Release Notes" summary in the PR description or task comment.

## Definition of Done

- Manual is updated.
- Codebase is clean.
- All tests pass.

## Verification

- Check `src/assets/manual.md`.
- Run full test suite.
