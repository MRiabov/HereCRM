# Research Findings: Broadcast Marketing Campaigns

## Decisions

### 1. Scheduler and Rate Limiting

- **Decision**: Leverage the existing `SchedulerService` (wrapping `APScheduler`) to manage campaign execution chunks.
- **Rationale**: The project already uses `APScheduler` for daily tasks. It connects to the existing architecture seamlessly.
- **Implementation**:
  - `CampaignService` will have a `process_next_batch(campaign_id)` method.
  - The scheduler will trigger this job every X seconds/minutes until the campaign is complete.
  - Rate limiting is handled by controlling the batch size and interval (e.g., 50 messages every minute).

### 2. Audience Segmentation

- **Decision**: Utilize the existing `SearchService`.
- **Rationale**: `SearchService.search(params)` implements "Unified Search". We will reuse this logic for finding customer segments via natural language.
- **Constraint**: Need to ensure `SearchService` returns UNLIMITED results for campaign generation (currently capped at 10 for UI).

### 3. Messaging Providers

- **Decision**:
  - **SMS**: Use **TextGrid** (via `TextGridService` which already exists in `src/services/channels/textgrid.py`).
  - **WhatsApp**: Use **Meta Graph API** (via `MessagingService._send_whatsapp` which handles the API calls directly).
  - **Email**: Will need standard SMTP integration (to be implemented).
- **Rationale**: These are the project's standard providers. No new vendor integrations needed.

### 4. Data Persistence

- **Decision**: Create `Campaign` and `CampaignRecipient` tables.
- **Rationale**: Granular tracking is essential for:
  - Resuming interrupted campaigns.
  - Generating detailed reports.
  - Preventing double-sends (idempotency).
