---
work_package_id: "WP05"
title: "Email Integration"
lane: "doing"
dependencies: ["WP02"]
subtasks: ["T015", "T016"]
agent: "Antigravity"
shell_pid: "144678"
review_status: "has_feedback"
reviewed_by: "MRiabov"
---
# Work Package 05: Email Integration

**Goal**: Process inbound emails via Postmark and attach files to jobs.

## Context

Postmark can POST JSON webhooks for inbound emails. We need to handle this payload, extract attachments, and link them to the user (by From: address).

## Subtasks

### T015: Implement Postmark Webhook

**Purpose**: API Endpoint to receive email data.

**Steps**:

1. In `src/api/routes.py` (or new `webhooks.py`), add POST `/webhooks/postmark/inbound`.
2. Validate payload (if secret/signature check is feasible, otherwise rely on obscure URL or IP allowlist - check config).
3. Parse the JSON body using Pydantic model (PostmarkInboundModel).
    * Fields: `From`, `Subject`, `Attachments`.

### T016: Extract and Process Attachments

**Purpose**: Process the parsed email data.

**Steps**:

1. Extract Sender Email from `From`.
2. Find Customer by Email (using `src.repositories.user_repository` or similar).
    * If no customer found, maybe create one or ignore (decide policy - simpler to ignore for now or log error).
3. Iterate over `Attachments`.
    * Decode Base64 content.
    * Call `DocumentService.create_document`:
        * `customer_id`: Found customer.
        * `file_obj`: Decoded bytes.
        * `filename`: Attachment Name.
        * `mime_type`: ContentType.
        * `doc_type`: 'internal'.
4. Reply? Postmark expects 200 OK. We don't usually reply to the email sender unless we buy sending credits, but we could if `EmailService` exists. For now, just process silently.

**Files**:
* `src/api/routes.py` (UPDATE)
* `tests/integration/test_email_ingestion.py` (NEW)

**Validation**:
* Send Mock Postmark JSON to endpoint.
* Verify Document created.

## Activity Log

- 2026-01-23T15:44:31Z – Antigravity – shell_pid=106664 – lane=doing – Started implementation via workflow command
- 2026-01-23T16:03:49Z – Antigravity – shell_pid=106664 – lane=for_review – Implemented Postmark Email Integration with Attachment processing. Added Document model/service and Customer email field.
- 2026-01-23T16:04:00Z – Antigravity – shell_pid=106664 – lane=for_review – Implemented Postmark Email Integration with Attachment processing. Added Document model/service and Customer email field.
- 2026-01-23T16:53:53Z – Antigravity – shell_pid=140703 – lane=doing – Started review via workflow command
- 2026-01-23T17:02:49Z – Antigravity – shell_pid=140703 – lane=planned – Moved to planned
- 2026-01-23T17:03:24Z – Antigravity – shell_pid=140703 – lane=doing – Moved to doing
- 2026-01-23T17:04:20Z – Antigravity – shell_pid=140703 – lane=for_review – Moved to for_review
- 2026-01-23T17:06:19Z – Antigravity – shell_pid=144678 – lane=doing – Started review via workflow command
