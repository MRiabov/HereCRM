# Data Model: Multi-channel Communication

## User Model Refactor

- **PK**: `id` (Integer, Auto-increment/Serial).
- **Identity Fields**:
  - `phone_number` (String, nullable, unique, indexed)
  - `email` (String, nullable, unique, indexed)
  - *Constraint*: At least one of `phone_number` or `email` must be present.
- **Preferences**:
  - `preferred_channel` (Enum: 'whatsapp', 'sms', 'email') - Defaults to the channel of first contact.

## Schema Updates

### Users Table

```sql
ALTER TABLE users ADD COLUMN id SERIAL PRIMARY KEY;
ALTER TABLE users ADD COLUMN email VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN preferred_channel VARCHAR(50) DEFAULT 'whatsapp';
-- Migration Note: Ensure existing users get IDs and preserve phone_number.
```

### Conversation State

- **New Columns**:
  - `active_channel` (VARCHAR) - Tracks which channel the current conversation flow is using.
  - `pending_action_timestamp` (TIMESTAMP) - For auto-confirmation logic.
  - `pending_action_payload` (JSON) - Stores the tool call to be executed.

### Messages

- **FK Update**: `user_id` (Integer) replacing `phone_number` as the foreign key to `Users`.
- **New Columns**:
  - `channel_type` (VARCHAR) - 'whatsapp', 'sms', 'email', 'webhook'.
  - `external_id` (VARCHAR) - Twilio SID / Postmark MessageID.

## Configuration (File-based / Env)

Defined in YAML/Env, not DB, per spec.

- `CHANNELS_CONFIG`:
  - `sms`: { provider: 'twilio', auto_confirm: true, timeout: 45, max_len: 160 }
  - `email`: { provider: 'postmark', auto_confirm: true, timeout: 45, max_len: 2000 }
  - `whatsapp`: { provider: 'meta', auto_confirm: false }
