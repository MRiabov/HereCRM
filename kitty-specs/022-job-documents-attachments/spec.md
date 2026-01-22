# Feature Specification: Job Documents & Attachments

**Feature**: Job Documents & Attachments
**Status**: Draft
**Mission**: software-dev

## 1. Overview

This feature enables customers and business owners to upload, store, and retrieve documents (images, PDFs, text) related to specific jobs via WhatsApp, SMS, and Email. It also supports recognizing and storing external cloud links (Dropbox, Google Drive). Security is a primary concern; therefore, all uploaded files are stored in a private object storage (S3) and accessed only via time-limited presigned URLs.

## 2. Functional Requirements

### 2.1. Document Ingestion (Multi-Channel)

- **WhatsApp**:
  - Automatically capture Image and Document messages sent by the user.
  - Extract file metadata (MIME type, size, filename).
- **SMS (Twilio)**:
  - Handle MMS attachments (images).
  - Parse text messages for standard cloud storage links (Dropbox, Google Drive, OneDrive).
- **Email (Postmark)**:
  - Extract email attachments.
  - Allow listing generic cloud links found in the email body.
- **Link Parsing**:
  - The system must use regex or a parsing library to detect valid URLs from supported cloud providers in text-based messages (SMS/WhatsApp/Email body).

### 2.2. Association Logic

- **Events**:
  - `DOCUMENT_RECEIVED`: Triggered when an attachment or link is validated.
- **Auto-Association**:
  - Incoming documents are automatically linked to the Customer's **most recently updated Active Job** (status not in `COMPLETED`, `CANCELLED` and within proper time window).
  - If no active job exists, link to the Customer profile as a generic "User Document".
- **Confirmation**:
  - Respond to the user confirming receipt: "✔ Document saved to your job at [Address]."

### 2.3. Secure Storage

- **Storage Backend**: Secure Cloud Object Storage (e.g., S3-compatible).
- **Access Control**:
  - Files are stored privately by default (no public access).
  - Files are renamed with a unique identifier to prevent collisions and guessing.
- **Retrieval**:
  - URLs generated for users must be **Secure Temporary Links** (signed URLs) with a short expiration (e.g., 60 minutes).

### 2.4. Retrieval & Management

- **Query Commands**:
  - "Show documents" / "Show files" / "Get photos"
  - Context-aware: Returns documents for the active job or asks for clarification if multiple jobs are recent.
- **Output Format**:
  - A numbered list of links with file types/names.
  - Example:
    1. `invoice.pdf` (Expires in 1h)
    2. `damage_photo.jpg` (Expires in 1h)
    3. `Dropbox Link` (External)

### 2.5. Security Measures

- **File Validation**:
  - **Type Allowlist**: Only allow safe standard document and image types (e.g., PDF, JPEG, PNG, DOCX). Strictly reject executables or scripts.
  - **Size Limit**: Enforce a maximum file size (e.g., 10MB) to prevent system abuse.
- **Tenant Isolation**:
  - All document access must be strictly scoped to the specific Business.
  - Customers can only access documents linked to *their* jobs/profile.

## 3. Data Model (Conceptual)

- **Document**:
  - `ID`: Unique Identifier
  - `Business`: Reference to the Business Owner
  - `Job`: Reference to the associated Job (optional)
  - `Customer`: Reference to the Customer
  - `Type`: Internal Upload vs External Link
  - `Path/URL`: Secure storage location or external URL
  - `Metadata`: Filename, file type, size
  - `Created`: Timestamp
  - `Uploaded By`: Customer or Business User

## 4. User Scenarios

### Scenario 1: Customer Uploads Photo via WhatsApp

1. **Customer** sends a photo of a broken window via WhatsApp.
2. **System** receives webhook with media content.
3. **System** transfers media to secure private storage.
4. **System** links record to Job #123 (Active).
5. **System** replies: "✔ Photo added to your job #123."

### Scenario 2: Business Owner Retrieves Documents

1. **Owner** texts: "Show docs for John Doe"
2. **System** finds Job #123 for John Doe.
3. **System** generates secure temporary links for 3 files.
4. **System** replies:
   "Documents for John Doe (Job #123):
   1. [Photo 1] (link...)
   2. [Contract PDF] (link...)"

### Scenario 3: External Link Handling

1. **Customer** SMS: "Here are the plans: <https://dropbox.com/s/xyz/house_plans.pdf>"
2. **System** detects URL. Validates it's a whitelisted domain.
3. **System** stores as `Document(type=EXTERNAL_LINK)`.
4. **System** replies: "✔ Link attached to Job #123."

## 5. Success Criteria

- **Security**: 100% of internally stored files are private and only accessible via valid presigned URLs.
- **Reliability**: Uploads via WhatsApp and SMS (MMS) are processed and available within 10 seconds.
- **Usability**: Customers receive immediate confirmation of successful upload.
- **Safety**: System rejects 100% of files with disallowed extensions (e.g., .exe, .sh).

## 6. Assumptions & Risks

- **Twilio MMS**: Assumes the business phone number is MMS-enabled.
- **Platform API**: Assumes access to media retrieval endpoints from messaging providers.
- **Storage Metrics**: High-res images may consume significant storage; lifecycle policies (e.g., auto-archive after 1 year) are out of scope for MVP but recommended later.
