---
work_package_id: WP04
title: Confirmation Workflow
lane: "for_review"
dependencies: []
subtasks: [T015, T016, T017, T018, T019]
agent: "Antigravity"
shell_pid: "3779362"
review_status: "has_feedback"
reviewed_by: "MRiabov"
---

### Objective

Close the loop by allowing customers to accept quotes. This must generate a Job and notify the business.

### Context

Confirmation can happen in two ways:

1. Clicking "Accept" on the web view (API call).
2. Replying "Confirm" via WhatsApp.

### Subtasks

#### T015: Confirm Logic & Job Creation

**Purpose**: The shared logic for acceptance.
**Steps**:

1. Edit `src/services/quote_service.py`.
2. Implement `confirm_quote(quote_id) -> Job`:
   - Fetch Quote.
   - Check status is `SENT` (error if `ACCEPTED` or `EXPIRED`).
   - Update Quote status to `ACCEPTED`.
   - creating `Job` entity using `quote.items`.
   - Link `quote.job_id`.
   - Commit.
   - Return Job.

#### T016: Public Confirm Endpoint

**Purpose**: Web acceptance.
**Steps**:

1. Create/Edit `src/api/public.py`.
2. Add route `POST /quotes/{token}/confirm`.
3. Lookup Quote by `external_token`.
4. Call `QuoteService.confirm_quote(quote.id)`.
5. Return 200 OK + Success Message/Page.

#### T017: Text Intent Handler

**Purpose**: WhatsApp acceptance.
**Steps**:

1. Edit `src/services/whatsapp_service.py` (or `intent_router.py`).
2. In the message processing loop, check logic:
   - If user msg ~= "Confirm" / "Accept":
   - Call `QuoteService.get_recent_quote(customer_id)`.
   - If found and status is `SENT`:
     - Call `QuoteService.confirm_quote(quote.id)`.
     - Reply "Great! Job scheduled for...".
   - Else: Reply "No pending active quotes found."

#### T018: Testing

**Purpose**: Verify the flow.
**Steps**:

1. Create `tests/integration/test_quote_confirmation.py`.
2. Test A: Create Quote -> Call Public API -> Verify Job.
3. Test B: Create Quote -> Simulate "Confirm" text -> Verify Job.

#### T019: E2E Verification

**Purpose**: Manual or script verification (Optional scripting).
**Steps**:

1. Documentation or script to simulate the full lifecycle (Create -> Send -> Confirm).

### Verification

- Run `pytest tests/integration/test_quote_confirmation.py`.

## Activity Log

- 2026-01-20T19:12:38Z – unknown – lane=for_review – Ready for review: Implemented scope enforcement in ToolExecutor, added required_scope metadata support, and verified with tests. Also shimmed missing Business model fields and billing_config.yaml from WP00.
- 2026-01-20T19:14:32Z – Antigravity – shell_pid=3779362 – lane=doing – Started review via workflow command
- 2026-01-20T19:54:30Z – Antigravity – shell_pid=3779362 – lane=planned – Moved to planned
- 2026-01-20T19:55:12Z – Antigravity – shell_pid=3779362 – lane=doing – Started implementation via workflow command
- 2026-01-20T20:07:17Z – Antigravity – shell_pid=3779362 – lane=for_review – Ready for review: Implemented scope enforcement in ToolExecutor, added ManageEmployeesTool and MassEmailTool with scope metadata, and verified with tests.
