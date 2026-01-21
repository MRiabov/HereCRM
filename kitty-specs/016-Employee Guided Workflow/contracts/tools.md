# Tool Contracts

## 1. CompleteJobTool

**Usage**: Employee marks a job as done.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `job_id` | Integer | Yes | The unique ID of the job found in the text (e.g., from "#123"). |
| `notes` | String | No | Any additional comments like "collected check" or "needs follow up". |

**Example Trigger**:
User: "Done with #101, customer paid cash"
Tool: `CompleteJobTool(job_id=101, notes="customer paid cash")`

**System Behavior**:

- Update Job #101 status to `completed`.
- Check for next scheduled job for the same employee on the same day.
- Return structured response with "Next Job" details.

## 2. EditServiceTool (Extension)

**Usage**: Business Owner configures service reminders.

| Field | Type | Description |
|-------|------|-------------|
| ... | ... | Existing fields |
| `reminder_text` | String | The text to include in "Next Job" notifications for jobs of this service type. |

**Example Trigger**:
User: "Update Window Cleaning to remind them to check the screens"
Tool: `EditServiceTool(original_name="Window Cleaning", reminder_text="Check the screens")`

---

# Event Contracts

## 1. SHIFT_STARTER

**Trigger**: Time-based (internal scheduler).

**Payload**:

```json
{
  "event": "SHIFT_STARTER",
  "employee_id": 12,
  "local_time": "06:30",
  "date": "2026-01-22"
}
```

**Handler**:

- Fetches daily schedule.
- Calculates route (using Autoroute logic/mock).
- Sends summary message to Employee.
