# IMPL-023 Broadcast Marketing Campaigns Implementation Plan

## Goal Description

Implement "Broadcast Marketing Campaigns" to allow business owners to send proactive mass messages (WhatsApp, Email) to customer segments defined by natural language queries. This shifts the CRM from reactive to proactive revenue generation.

The feature includes:

1. **Segmentation**: Using the existing Unified Search (`SearchService`) to find customers based on natural language (e.g., "Customers in Dublin").
2. **Creation**: A UI to draft messages, select channels (Email/SMS/WhatsApp), and preview the audience.
3. **Execution**: Background processing of the campaign using `APScheduler` to handle rate limiting and batch sending.
4. **Safety**: A "Blast Protocol" requiring explicit confirmation to prevent accidental mass spam.

## User Review Required

> [!IMPORTANT]
> **Credential Security**: SMTP and Twilio credentials will be stored **unencrypted** in the SQLite database for this MVP, as confirmed by the user. This is a known security risk but accepted for the current phase.

> [!WARNING]
> **Rate Limiting**: We are using `APScheduler` for batch processing. Strict rate limits (e.g., 10 emails/sec, 1 WhatsApp/sec) will be enforced in the application logic. If the application restarts, `APScheduler` with a persistent job store (SQLite) should resume, but we must ensure idempotency to avoid double sending.

## Proposed Changes

### Database Layer

#### [NEW] [models_marketing.py](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM/src/models/marketing.py)

- Create `Campaign` model:
  - `id`, `name`, `status` (draft, scheduled, running, completed, failed)
  - `query_string` (the NL query used)
  - `channel` (email, whatsapp, sms)
  - `message_template`
  - `total_recipients`, `sent_count`, `failed_count`
  - `created_at`, `scheduled_at`, `completed_at`
- Create `CampaignRecipient` model:
  - `id`, `campaign_id`, `customer_id`
  - `status` (pending, sent, failed)
  - `error_message`
  - `sent_at`

#### [MODIFY] [models.py](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM/src/models/models.py)

- Import and register new models.

### Backend Services

#### [NEW] [campaign_service.py](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM/src/services/marketing/campaign_service.py)

- `create_campaign(query, channel, template)`:
  - Calls `SearchService.search(query, entity_type='customer')` to get recipients.
  - Persists `Campaign` and `CampaignRecipient`s.
- `execute_campaign(campaign_id)`:
  - Orchestrates the sending process.
  - Loads pending recipients.
  - Process in batches.
- `send_batch(campaign_id, limit=50)`:
  - Called by Scheduler.
  - Sends messages via `MessagingService`.

#### [MODIFY] [scheduler.py](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM/src/services/scheduler.py)

- Add method `schedule_campaign(campaign_id, run_at)` to trigger `CampaignService.execute_campaign`.

#### [MODIFY] [messaging_service.py](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM/src/services/messaging_service.py)

- Ensure generic `enqueue_message` or specific `send_email`/`send_whatsapp` methods can accept dynamic credentials if meant to be per-user, or use system defaults if that's the design. *Correction*: Spec says "User provides credentials". We need to pass these or retrieve them from `Settings`.

### API Layer

#### [NEW] [marketing.py](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM/src/routers/marketing.py)

- `POST /campaigns/draft`: Create a draft, returns preview (count, sample recipients).
- `POST /campaigns/{id}/launch`: Execute the blast protocol (requires confirmation string).
- `GET /campaigns`: List campaigns.
- `GET /campaigns/{id}`: Get details and progress.

#### [MODIFY] [main.py](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM/src/main.py)

- Register `marketing` router.

### Frontend (PWA)

#### [NEW] [MarketingCampaignsScreen.jsx](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM-PWA/src/components/MarketingCampaignsScreen.jsx)

- List of past/active campaigns.
- Button to "New Campaign".

#### [NEW] [NewCampaignScreen.jsx](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM-PWA/src/components/NewCampaignScreen.jsx)

- **Step 1: Audience**: Input for NL query (e.g., "Customers in Dublin"). Calls API to preview segment size.
- **Step 2: Channel & Content**: Select WhatsApp/Email. Text area for message.
- **Step 3: Blast Protocol**: "Review" screen. Show big numbers. Disable button. Input field for "EXECUTE BLAST".

#### [NEW] [CampaignDetailsScreen.jsx](file:///home/maksym/Work/proj/HereCRM-combined/HereCRM-PWA/src/components/CampaignDetailsScreen.jsx)

- Live progress bar of sending.
- Stats (Sent vs Failed).

## Verification Plan

### Automated Tests

- **Unit Tests**:
  - `test_campaign_service.py`: Test creation logic, segment resolution from mock SearchService.
  - `test_rate_limiting.py`: Verify that the batch processor respects limits (mocking time).
- **Integration Tests**:
  - Create a campaign with checking that `CampaignRecipient` rows are created matching `SearchService` results.

### Manual Verification

1. **Audience Check**: Type "Customers in [City]" in the UI, verify the count matches the `sqlite3` count of customers in that city.
2. **Blast Protocol**: Try to click "Send" without typing confirmation. Should be disabled. Type confirmation -> enabled.
3. **Execution**: Launch a campaign to 5 test users.
    - Verify 5 rows in `CampaignRecipient`.
    - Verify 5 messages sent (via logs or actual receipt if creds provided).
    - Verify status updates in UI to "Completed".
4. **Resilience**: Restart backend mid-campaign. Verify it resumes (or at least doesn't double send) - *Note: exact resume logic depends on Scheduler persistence, verification is optional for MVP but good to check.*
