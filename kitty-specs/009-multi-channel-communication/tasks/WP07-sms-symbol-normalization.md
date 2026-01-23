---
lane: "doing"
agent: "Antigravity"
shell_pid: "46891"
---
# Work Package 07: SMS Symbol Standardization

**Goal**: Implement strict GSM-7 character set normalization to minimize SMS costs.
**Spec**: [Spec 009](../spec.md) (WP07)

## Context

Standard SMS uses the GSM-7 encoding (160 characters per segment). If a message contains a single non-GSM-7 character (e.g., emoji, smart quote, accent), it shifts to UCS-2 encoding (70 characters per segment). This can more than double the cost.
We need a utility to aggressively normalize text to GSM-7 equivalents before sending via SMS.

## Requirements

1. **GSM-7 Utilities**:
    - Create `src/services/channels/sms_utils.py`.
    - Define the standard GSM-7 basic character set + extension table.
    - Implement `is_gsm7(text: str) -> bool`.
    - Implement `normalize_to_gsm7(text: str) -> str`:
        - Replace common "fancy" characters with ASCII equivalents:
            - Smart quotes (“ ” ‘ ’) -> Normal quotes (" ').
            - En/Em dashes (– —) -> Hyphen (-).
            - Ellipsis (…) -> Three dots (...).
            - Accented chars (á, é, etc.) -> Standard chars if possible (or keep if in GSM-7 extension, but preferably strip accents for simplicity unless critical).
        - Strip emojis or replace with text equivalent (e.g. `:)`).
        - Final fallback: Replace unknowable characters with `?`.

2. **Integration**:
    - Update `SMSMessagingService` (in `src/services/channels/base.py`) to automatically call `normalize_to_gsm7` on the `body` before sending.

## Files to Create/Edit

- `src/services/channels/sms_utils.py` (New)
- `src/services/channels/base.py` (Edit)

## Testing

- Create unit tests `tests/unit/test_sms_utils.py`.
- Test cases:
  - Pure ASCII (unchanged).
  - GSM-7 extended chars (e.g., brackets `[]`, pipe `|`) -> should pass or be handled correctly.
  - Smart quotes -> normal quotes.
  - Emojis -> stripped or converted.

## Activity Log

- 2026-01-23T11:14:04Z – Antigravity – shell_pid=46891 – lane=doing – Started implementation via workflow command
