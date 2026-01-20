# Research: Employee Management Dashboard

**Feature Branch**: `011-employee-management-dashboard`
**Date**: 2026-01-20

## 1. Text-Only Dashboard Formatting

**Context**: The "Dashboard" is a text response sent via WhatsApp/SMS. It must represent a schedule of multiple employees and jobs.

**Decision**: Use a **list-based format with emoji indicators** rather than ASCII tables.

- **Format**:

  ```text
  📅 *Schedule for Today*
  
  👤 *John Doe*
  • 08:00 - Job #123 (Fix leak)
  • 10:00 - Job #124 (Install tap)
  
  👤 *Jane Smith*
  • 09:00 - Job #125 (Inspection)
  
  ⚠️ *Unassigned*
  • Job #126 (Emergency)
  ```

- **Rationale**:
  - Mobile screens wrapping text breaks ASCII tables.
  - Emojis provide quick visual parsing.
  - Vertical rythm allows for infinite scrolling/length unlike side-by-side columns.

**Alternatives Considered**:

- **ASCII Tables (`prettytable`)**: Rejected because they look terrible on narrow mobile screens (WhatsApp).
- **Image Generation**: Rejected because text is searchable and copy-pasteable (for IDs).

## 2. Natural Language Assignment (Fuzzy Matching)

**Context**: User commands like "Assign #123 to John" need to resolve "John" to a specific user ID, even if multiple Johns exist or spelling is slightly off.

**Decision**: Use **`thefuzz` (fka `fuzzywuzzy`)** library coupled with **Levenshtein distance**.

- **Strategy**:
  1. Extract potential name from command.
  2. Filter candidates by role='member'.
  3. Calculate match score.
  4. If score > 80:
     - If single match -> Auto-assign.
     - If multiple matches (e.g. John A vs John B) -> Return specific disambiguation prompt.
  5. If score < 80 -> Prompt "Who did you mean?".

**Rationale**:

- `thefuzz` is industry standard for Python simple string matching.
- Explicit disambiguation prevents costly schedule errors.

## 3. State Management

**Context**: The "Dashboard" is described as a "Screen". We need to "enter" this screen to use its specific tools.

**Decision**: Add `EMPLOYEE_MANAGEMENT` to `UserRole` or better, a dedicated `ConversationStatus` enum value.

- **Implementation**:
  - Update `src/models.py`: `ConversationStatus.EMPLOYEE_MANAGEMENT`.
  - When in this state, the ToolExecutor prioritizes `employee_management` tools.
  - "Exit" command returns state to `IDLE`.

**Rationale**:

- Keeps the global namespace of tools clean (don't accidentally assign jobs when trying to chat).
- Matches existing pattern for "Settings" or "Import".
