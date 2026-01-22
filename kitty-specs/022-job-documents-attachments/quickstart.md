# Quickstart: Job Documents & Attachments

## Configuration

1. **Environment Variables**:
    Ensure the following are set in `.env`:

    ```bash
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    AWS_BUCKET_NAME=...
    AWS_ENDPOINT_URL=... # e.g., https://s3.us-west-002.backblazeb2.com
    ```

2. **Dependencies**:
    Running `pip install boto3` is required (already in pyproject.toml).

## Usage Guide

### 1. Uploading a Document (Customer)

* **WhatsApp**: Simply send an image or file attachment to the business number.
* **External Link**: Send a text message containing a link (e.g., "Here is the drive link: <https://drive.google.com/>...")
* **Email**: Reply to any email from the system with an attachment.

### 2. Retrieval (Business Owner)

* User command: "Show documents for [Customer Name]" or "Show files".
* System returns: A generated list of **safe, time-limited links**.
* Click the link to view/download.

### 3. Verification

* Check the logs for `Document stored: ...`.
* Verify the file appears in the Backblaze B2 bucket under `business_{id}/...`.
