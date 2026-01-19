# Data Model Changes

## User Model Refactor

- **PK**: Change from `phone_number` (String) to `id` (Integer/Auto-increment).
- **New Fields**:
  - `email` (String, nullable, unique)
  - `phone_number` (String, nullable, unique) - *Existing, but effectively changing semantic usage.*
  - `channel_preferences` (JSON) - To store preferred channel if multiple exist? (Maybe YAGNI for now).

## Schema Updates

### Users Table

```sql
ALTER TABLE users ADD COLUMN id INTEGER PRIMARY KEY AUTOINCREMENT;
-- Migration will need to handle migrating existing PKs to the new ID structure
-- and keeping phone_number as a standard unique column.
ALTER TABLE users ADD COLUMN email VARCHAR(255) UNIQUE;
```

### Conversation State

- Needs to link to `user_id` instead of `phone_number`.

### Messages

- Needs migration to refer to `user_id` or link via polymorphic association (or just keep string `from_identity` / `to_identity` and type? No, better to link to User ID).

## New Config/Entities

- No new database tables explicitly planned for Channel Config (YAML based), but `ConversationState` might need to track the `active_channel`.
