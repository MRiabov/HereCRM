---
work_package_id: "WP03"
title: "Ingestion Pipelines (WhatsApp & Links)"
lane: "doing"
dependencies: ["WP02"]
subtasks: ["T008", "T009", "T010", "T011"]
shell_pid: "31834"
---
# Work Package 03: Ingestion Pipelines (Media & Links)

**Goal**: Enable the system to receive documents via WhatsApp (media attachments) and SMS/Text (cloud links).

## Context

We need to hook into the messaging pipeline. When a user sends a photo or a Dropbox link, we should catch it, process it via `DocumentService`, and confirm receipt.

## Subtasks

### T008: Implement Link Parsing Utility

**Purpose**: Create a utility to find and validate cloud storage links in text.

**Steps**:

1. Create `src/utils/link_parser.py`.
2. Define ALLOWED_DOMAINS constant: [`dropbox.com`, `drive.google.com`, `docs.google.com`, `onedrive.live.com`, `box.com`, `icloud.com`].
3. Implement `extract_links(text: str) -> List[str]`:
    * Use regex to find URLs.
    * Filter by ALLOWED_DOMAINS.
    * Return list of valid URLs.
4. Write unit tests for this utility in `tests/utils/test_link_parser.py`.

**Files**:
* `src/utils/link_parser.py` (NEW)
* `tests/utils/test_link_parser.py` (NEW)

### T009: Handle WhatsApp Media Attachments

**Purpose**: Process incoming media messages.

**Steps**:

1. Identify where inbound messages are processed (likely `src/api/routes.py` -> `whatsapp_service.py` or a dedicated handler).
2. In the processing flow (e.g., `handle_incoming_message`):
    * Check if message has media (Twilio webhook payload: `NumMedia` > 0, `MediaUrl0`, `MediaContentType0`).
3. If media is present:
    * Iterate through media items.
    * Download content from `MediaUrl`.
    * Call `DocumentService.create_document(..., doc_type='internal', file_obj=content, mime_type=..., ...)`
    * Accumulate results.
4. Send Confirmation:
    * Reply with "✔ [N] Document(s) saved to Job #[ID]" (or similar).
    * Ensure we don't disrupt the normal conversation flow (maybe just a system note or distinct reply).

**Files**:
* `src/services/whatsapp_service.py` (UPDATE)
* `src/api/routes.py` (UPDATE - if payload parsing happens here)

### T010: Handle Text Links (WhatsApp & SMS)

**Purpose**: Process links in text messages.

**Steps**:

1. In the same message processing flow (processing the `Body`):
    * Call `extract_links(body)`.
2. If links found:
    * For each link, call `DocumentService.create_document(..., doc_type='external_link', external_url=link, ...)`
3. Send Confirmation:
    * Reply "✔ Link saved."

### T011: Integration Tests for Ingestion

**Purpose**: Verify the full webhook flow.

**Steps**:

1. Create `tests/integration/test_ingestion_flow.py`.
2. Mock `StorageService` logic (we don't want real downloads/uploads).
3. Simulate a Twilio Webhook Request with `MediaUrl`.
    * Verify `create_document` was called.
    * Verify confirmation response.
4. Simulate a Text Message with "Check this <https://dropbox.com/>..."
    * Verify `create_document` called with external link.

**Validation**:
* Media uploads trigger document creation.
* Links triggers document creation.
* Confirmation is sent.
