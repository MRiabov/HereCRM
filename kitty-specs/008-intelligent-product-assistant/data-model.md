# Data Model: Intelligent Product Assistant

## 1. Existing Entities

### Message

- `role`: `user` or `assistant`
- `body`: The text content.
- `from_number`: Phone number of sender.
- `to_number`: Phone number of recipient.
- `log_metadata`: JSON field containing:
  - `tool_call`: Name and arguments of the tool invoked (if any).
  - `error`: Details of any parsing or execution failures.

## 2. New Entities

### ChannelConfig (Configuration-only)

- `channel_name`: string (e.g., "whatsapp", "email", "sms")
- `max_length`: integer (desired max character count for the assistant)
- `style`: string ("concise", "detailed", "bullet_points")

### UserPreferences (Modified)

- `confirm_by_default`: boolean (already exists, impacts how `HelpTool` triggers)
