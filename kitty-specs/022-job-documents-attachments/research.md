# Phase 0 Research: Job Documents & Attachments

## 1. Storage Backend

**Decision**: Use Backblaze B2 (S3-compatible) via `boto3`.
**Rationale**: User preference and standard AWS S3 API compatibility.
**Implementation Details**:

* Configuration via `.env` variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BUCKET_NAME`, `AWS_ENDPOINT_URL`.
* Files stored with path structure: `business_{id}/job_{id}/{uuid}_{filename}`.
* Access via Presigned URLs (expiry: 1 hour).

## 2. Webhook Media Extraction

**Problem**: Current `src/api/routes.py` has stub implementation for "Real Meta Payload". It identifies `image` messages but sets `media_url=None`.
**Resolution**:

* **WhatsApp**: The standard Meta Graph API payload provides an `id` for media. Retrieval requires a GET request to the Graph API with the bot token.
  * *Note*: For this implementation, we will update `routes.py` to attempt extracting `url` if provided (common in some BSPs) or at least pipe the `id` through. *Correction*: The user asked for "quick research". Given the constraints, we will implement a pattern that supports receiving the `id` and fetching the URL using the `WhatsappService`.
* **Postmark**: Current webhook ignores `Attachments`. We must parse the `Attachments` JSON array (Name, ContentType, ContentID).

## 3. Association Logic

**Approach**:

* **DocumentService** will listen for `document_received`(conceptual event).
* It queries `JobRepository` for the most recent active job (Status != COMPLETED/CANCELLED) for that Customer.
* If found -> Attach to Job.
* If not found -> Attach to Customer Profile (Job ID = Null).

## 4. Deferred Scope

* **Twilio MMS**: User explicitly requested to skip SMS media support for now.
* **Permissions**: Standard RBAC applies (Owner sees all, Employee sees assigned).
