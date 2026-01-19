---
work_package_id: WP01
subtasks:
  - T001
  - T002
  - T003
  - T004
  - T005
  - T006
lane: planned
history:
  - date: 2026-01-19
    action: created
---

# WP01 - Data Model Refactor & Identity

## Objective

Refactor the `User` model to use an Integer ID as the Primary Key instead of `phone_number`. Add support for `email` field. Ensure data consistency for existing users.

## Context

Currently, the system uses `phone_number` as the primary key. This limits us to SMS/WhatsApp users. We need to support Email-only users, so we must switch to a surrogate key (`id`).

## Subtasks

### T001: Create migration to add `id` and `email`

- Create a new migration file (e.g., `alembic` or SQL script depending on the project mechanism).
- Add `id` as `INTEGER PRIMARY KEY AUTOINCREMENT`.
- Add `email` as `VARCHAR(255) UNIQUE`.
- **Note**: SQLite migration for PK change requires table recreation (copy-migrate-drop-rename).

### T002: Migrate existing records

- Ensure all existing users get a generated `id`.
- Preserve `phone_number` data.

### T003: Update ConversationState

- Update table schema: replace `phone_number` FK with `user_id` FK.
- Migrate data: map existing `phone_number` in `ConversationState` to the new `user_id`.

### T004: Update Messages

- Update table schema: add `user_id` FK.
- Decide if `from_identity`/`to_identity` strings remain or if we key off `user_id`.
- Migrate data: link messages to `user_id`.

### T005: Update Codebase References

- Search for usages of `user.phone_number` as identity.
- Refactor to use `user.id` for lookups, session management, and relationships.

### T006: Verify Data Integrity

- Test that an existing user (from WhatsApp) is correctly retrievable by ID.
- Test that their history is preserved.

## Definition of Done

- `users` table has `id` PK and `email` column.
- `Message` and `ConversationState` link to `users.id`.
- Application boots without schema errors.
- Existing functionality (WhatsApp chat) works with the new schema.
