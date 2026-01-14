# Search & Tools Documentation

This document describes the natural language search capabilities and tool behaviors of the WhatsApp AI CRM.

## Search Functionality

The `SearchTool` uses an LLM to parse user intent and delegates to specialized repositories.

### 1. Entity Types

You can filter your search by specifying the entity type:

- **Jobs**: "show all jobs", "find job fix sink"
- **Customers/Clients**: "show all clients", "find John"
- **Leads**: "show all leads" (A lead is defined as a **Customer with no associated Jobs**).
- **Requests**: "show my requests"

### 2. Time-Based Filtering

The system recognizes relative time for two types of queries:

- **Added**: "who did we add yesterday?", "new customers today" (Filters by `created_at`).
- **Scheduled**: "jobs for tomorrow", "schedule for next week" (Filters by `scheduled_at` for Jobs).

**Edge Case**: If you say "who did we see today", the LLM resolves this to a `scheduled` query for `Jobs`.

### 3. Geo-Spatial Proximity

You can search for entities near a specific location:

- "Find customers within 500m of High Street 42"
- "Search for jobs near London"

The system geocodes the address and performs a Haversine distance check (Python-side) within the specified radius.

### 4. Search Scope (The "All" Keyword)

Common broad queries are pre-filtered to avoid matching the word "all" against names or descriptions:

- `show all jobs` -> lists all jobs for the tenant.
- `show all customers` -> lists all customers.
- `show all leads` -> lists only customers without jobs.

---

## Tool Behaviors & Confirmation

### MUTATION Flow (Add/Edit/Schedule)

1. **Parsing**: LLM extracts entities (Name, Phone, Price, Time).
2. **Drafting**: System stores a draft in `ConversationState`.
3. **Confirmation**: System replies with a summary:
   - "Please confirm: Job summary: ... (Reply 'Yes' to confirm, 'No' to cancel)"
4. **Execution**: Upon "Yes", the record is committed to the database.

### Edit Last

If you made a mistake *immediately after* a confirmation, say **"edit last"**.

- The system retrieves the metadata of your last action.
- It prompts you with the previous details.
- You can then provide the update.

### Undo

Say **"undo"** within the same session to revert the last creation or status change.

- **Add Job** -> Undo deletes the Job.
- **Schedule** -> Undo reverts the status to `pending`.

---

## Intent Extraction Edge Cases

| User Input | Parsed Tool | Logic / Reasoning |
|------------|-------------|-------------------|
| "Fix sink for John $50" | `AddJobTool` | Presence of price ($50) or job description triggers Job creation instead of Lead. |
| "Add John 087123123" | `AddCustomerTool` | No price/job info -> adds as a Lead/Customer. |
| "Update phone for Mary to 085..." | `EditCustomerTool` | Explicit "update" or "edit" for an existing entity. |
| "Schedule John for Tuesday" | `ScheduleJobTool` | Explicit "schedule" or future time. |
| "Add request: Please call Bob" | `StoreRequestTool` | Explicit "request" keyword used. |
| "Hello" / Greeting | *None* | Greetings are pre-filtered. For new users, triggers Onboarding. For existing users, shows Help. |
