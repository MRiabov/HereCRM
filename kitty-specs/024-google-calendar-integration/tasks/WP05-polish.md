---
work_package_id: WP05
title: Polish & Documentation
lane: planned
dependencies: []
subtasks: [T018, T019]
---

# WP05 - Polish & Documentation

## Objective

Finalize the user experience and internal documentation.

## Context

Code is working, but we need to tell the user what happened and update our manuals.

## Subtasks

### T018: User Feedback

**Purpose**: Confirm successful connection.
**Steps**:

1. In `auth_callback`:
   - After successful DB update of credentials:
   - Identify the user (if possible via running session/socket).
   - Send system message (via `NotificationService` or similar): "✔ Google Calendar connected! Your assigned jobs will now appear on your calendar."
   - If that's too complex (http context vs websocket context), just ensure the HTML response page says it clearly.

### T019: Update Manual

**Purpose**: Documentation.
**Steps**:

1. Edit `src/assets/manual.md`.
2. Add section "Google Calendar Integration".
   - "How to Connect": Link to `/auth/google/login` (or tell them to ask bot).
   - "What Syncs": Jobs assigned to you.
   - "Troubleshooting": "If jobs don't appear, ask admin to reconnect."

## Validation

- [ ] Connect account -> See nice message.
- [ ] Read `manual.md` -> Section exists.

## Risks

- None really. Low complexity.
