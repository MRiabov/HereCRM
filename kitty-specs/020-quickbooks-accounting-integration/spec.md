# Feature Specification: QuickBooks Accounting Integration

**Feature**: QuickBooks Accounting Integration
**Status**: Draft
**Mission**: software-dev

## 1. Overview

This feature integrates QuickBooks Online with HereCRM to automatically synchronize accounting data, enabling businesses to maintain accurate financial records for tax reporting and bookkeeping. The integration provides automated hourly batch synchronization of invoices, payments, customers, and services from HereCRM to QuickBooks, eliminating manual data entry and reducing accounting errors.

Businesses authenticate once via OAuth 2.0, and the system handles all subsequent synchronization automatically with robust error handling and retry logic.

## 2. Functional Requirements

### 2.1. QuickBooks Authentication & Connection

- **FR-001**: System MUST provide a mechanism for Business Owners to initiate QuickBooks connection (e.g., "Connect QuickBooks" button in settings or conversational command).
- **FR-002**: System MUST implement OAuth 2.0 authorization flow using QuickBooks Online API to obtain access tokens.
- **FR-003**: System MUST securely store QuickBooks OAuth tokens (access token, refresh token, realm ID) for each business.
- **FR-004**: System MUST automatically refresh expired access tokens using the refresh token before sync operations.
- **FR-005**: System MUST allow Business Owners to disconnect their QuickBooks account, which removes stored credentials and stops synchronization.
- **FR-006**: System MUST display connection status (Connected/Disconnected) to Business Owners.

### 2.2. Automated Data Synchronization

- **FR-007**: System MUST perform automated batch synchronization every hour for all connected businesses.
- **FR-008**: System MUST synchronize the following data types from HereCRM to QuickBooks:
  - Invoices (new and updated)
  - Payments received
  - Customer/Client information (unidirectional: HereCRM → QuickBooks)
  - Services/Products from the service catalog
- **FR-009**: System MUST track synchronization state for each record to identify new, modified, and already-synced items.
- **FR-010**: System MUST maintain a mapping between HereCRM records and their corresponding QuickBooks IDs (e.g., HereCRM Invoice ID → QuickBooks Invoice ID).

### 2.3. Invoice Synchronization

- **FR-011**: When an invoice is created or updated in HereCRM, it MUST be queued for synchronization in the next hourly batch.
- **FR-012**: System MUST map HereCRM invoice data to QuickBooks Invoice format including:
  - Customer reference
  - Line items (services/products with quantities and prices)
  - Invoice date
  - Due date
  - Total amount
  - Invoice status
- **FR-013**: If an invoice already exists in QuickBooks (duplicate detected via mapping), system MUST update the existing QuickBooks invoice rather than creating a new one.

### 2.4. Payment Synchronization

- **FR-014**: When a payment is recorded in HereCRM, it MUST be queued for synchronization in the next hourly batch.
- **FR-015**: System MUST create Payment records in QuickBooks linked to the corresponding Invoice.
- **FR-016**: System MUST include payment details: amount, payment date, payment method, and reference to the invoice.

### 2.5. Customer Synchronization

- **FR-017**: System MUST synchronize customer/client records from HereCRM to QuickBooks (unidirectional).
- **FR-018**: System MUST map customer data including: name, phone number, email, address (if available).
- **FR-019**: If a customer already exists in QuickBooks, system MUST update the existing record.
- **FR-020**: System MUST create customers in QuickBooks before syncing invoices that reference them.

### 2.6. Service/Product Synchronization

- **FR-021**: System MUST synchronize services from HereCRM service catalog to QuickBooks as Items/Products.
- **FR-022**: System MUST map service data including: name, description, default price.
- **FR-023**: If a service already exists in QuickBooks, system MUST update the existing item.
- **FR-024**: System MUST create services in QuickBooks before syncing invoices that reference them.

### 2.7. Error Handling & Retry Logic

- **FR-025**: If QuickBooks API is unavailable or returns an error, system MUST retry the failed operation up to 3 times with exponential backoff (e.g., 1 minute, 2 minutes, 4 minutes).
- **FR-026**: If all retry attempts fail, system MUST notify the Business Owner with details of the failure.
- **FR-027**: If a record cannot be synced due to missing required data (e.g., customer missing address required by QuickBooks), system MUST:
  - Skip that specific record
  - Log the validation error
  - Notify the Business Owner with details of which record failed and why
  - Continue processing other records in the batch
- **FR-028**: System MUST track failed synchronization attempts and allow manual retry or correction.

### 2.8. Sync Status & Visibility

- **FR-029**: System MUST provide Business Owners visibility into synchronization status:
  - Last successful sync timestamp
  - Number of records synced in last batch
  - Any pending errors or failures
- **FR-030**: System MUST allow Business Owners to manually trigger an immediate sync outside the hourly schedule.
- **FR-031**: System MUST maintain a sync log/history showing recent synchronization activities and outcomes.

## 3. Data Model Enhancements

### Business Entity

- `quickbooks_realm_id` (String, nullable): QuickBooks company/realm identifier
- `quickbooks_access_token` (String, encrypted, nullable): OAuth access token
- `quickbooks_refresh_token` (String, encrypted, nullable): OAuth refresh token
- `quickbooks_token_expiry` (DateTime, nullable): Access token expiration timestamp
- `quickbooks_connected_at` (DateTime, nullable): When QuickBooks was first connected
- `quickbooks_last_sync` (DateTime, nullable): Timestamp of last successful sync

### Invoice Entity

- `quickbooks_id` (String, nullable): QuickBooks Invoice ID
- `quickbooks_synced_at` (DateTime, nullable): Last sync timestamp
- `quickbooks_sync_status` (Enum, nullable): PENDING, SYNCED, FAILED

### Payment Entity

- `quickbooks_id` (String, nullable): QuickBooks Payment ID
- `quickbooks_synced_at` (DateTime, nullable): Last sync timestamp
- `quickbooks_sync_status` (Enum, nullable): PENDING, SYNCED, FAILED

### Customer Entity

- `quickbooks_id` (String, nullable): QuickBooks Customer ID
- `quickbooks_synced_at` (DateTime, nullable): Last sync timestamp
- `quickbooks_sync_status` (Enum, nullable): PENDING, SYNCED, FAILED

### Service Entity

- `quickbooks_id` (String, nullable): QuickBooks Item/Product ID
- `quickbooks_synced_at` (DateTime, nullable): Last sync timestamp
- `quickbooks_sync_status` (Enum, nullable): PENDING, SYNCED, FAILED

### SyncLog Entity (New)

- `id` (Integer, primary key)
- `business_id` (Integer, foreign key)
- `sync_timestamp` (DateTime): When sync occurred
- `sync_type` (Enum): SCHEDULED, MANUAL
- `records_processed` (Integer): Total records in batch
- `records_succeeded` (Integer): Successfully synced
- `records_failed` (Integer): Failed to sync
- `error_details` (JSON, nullable): Details of any errors
- `status` (Enum): SUCCESS, PARTIAL_SUCCESS, FAILED

## 4. User Scenarios & Testing

### Scenario 1: Initial QuickBooks Connection

1. **Business Owner** navigates to settings or sends: "Connect QuickBooks"
2. **System** replies: "Click here to connect your QuickBooks account: [OAuth Link]"
3. **Business Owner** clicks link, authorizes HereCRM in QuickBooks portal
4. **System** receives OAuth callback, stores credentials
5. **System** confirms: "✅ QuickBooks connected! Your data will sync automatically every hour."

**Acceptance Criteria**:

- OAuth flow completes successfully
- Credentials are securely stored
- Connection status shows "Connected"

### Scenario 2: Automatic Hourly Sync (Happy Path)

1. **System** triggers hourly sync job at scheduled time
2. **System** identifies 5 new invoices, 3 payments, 2 new customers, 1 new service
3. **System** syncs customers first (dependency)
4. **System** syncs services second (dependency)
5. **System** syncs invoices third
6. **System** syncs payments last
7. **System** updates sync log: "11 records synced successfully"
8. **System** updates `last_sync` timestamp

**Acceptance Criteria**:

- All records sync in correct dependency order
- QuickBooks IDs are stored in HereCRM
- Sync status updated to SYNCED
- No errors logged

### Scenario 3: Sync with Missing Customer Data

1. **System** triggers hourly sync
2. **System** attempts to sync Invoice #123 for Customer "John Doe"
3. **QuickBooks API** rejects customer creation (missing required address field)
4. **System** skips Invoice #123, logs error
5. **System** continues syncing other records successfully
6. **System** notifies Business Owner: "⚠️ Sync completed with errors. Invoice #123 for John Doe could not be synced: Customer address is required by QuickBooks. Please update customer details."

**Acceptance Criteria**:

- Failed record is skipped, not retried in same batch
- Other records sync successfully
- Business Owner receives specific error notification
- Error details logged for review

### Scenario 4: QuickBooks API Temporarily Unavailable

1. **System** triggers hourly sync
2. **System** attempts to connect to QuickBooks API
3. **QuickBooks API** returns 503 Service Unavailable
4. **System** waits 1 minute, retries (Attempt 2)
5. **QuickBooks API** still unavailable
6. **System** waits 2 minutes, retries (Attempt 3)
7. **QuickBooks API** still unavailable
8. **System** waits 4 minutes, retries (Attempt 4 - final)
9. **QuickBooks API** responds successfully
10. **System** completes sync normally

**Acceptance Criteria**:

- Retry logic executes with exponential backoff
- Sync eventually succeeds
- No duplicate records created

### Scenario 5: Manual Sync Trigger

1. **Business Owner** sends: "Sync QuickBooks now"
2. **System** initiates immediate sync outside scheduled time
3. **System** processes all pending records
4. **System** replies: "✅ QuickBooks sync completed. 7 records synced successfully."

**Acceptance Criteria**:

- Manual sync executes immediately
- Does not interfere with scheduled sync
- Results reported to owner

### Scenario 6: Viewing Sync Status

1. **Business Owner** sends: "QuickBooks status"
2. **System** replies:

   ```
   📊 QuickBooks Sync Status
   
   Connection: ✅ Connected
   Last Sync: 15 minutes ago
   Last Batch: 12 records synced
   Pending Errors: 1
   
   ⚠️ 1 invoice failed to sync (missing customer data)
   ```

**Acceptance Criteria**:

- Status shows accurate connection state
- Displays last sync time
- Shows any pending errors with details

### Scenario 7: Disconnecting QuickBooks

1. **Business Owner** sends: "Disconnect QuickBooks"
2. **System** confirms: "Are you sure? This will stop automatic syncing."
3. **Business Owner** confirms: "Yes"
4. **System** removes OAuth credentials
5. **System** replies: "QuickBooks disconnected. You can reconnect anytime."

**Acceptance Criteria**:

- Credentials securely deleted
- Sync jobs no longer run for this business
- Connection status shows "Disconnected"

## 5. Success Criteria

- **SC-001**: Business Owners can successfully connect their QuickBooks account via OAuth 2.0 in under 2 minutes.
- **SC-002**: Automated hourly sync completes for 95% of businesses without errors.
- **SC-003**: When sync errors occur, Business Owners receive actionable error notifications within 5 minutes.
- **SC-004**: Invoices created in HereCRM appear in QuickBooks within 65 minutes (worst case: just after hourly sync).
- **SC-005**: Duplicate records are prevented - existing QuickBooks records are updated rather than creating duplicates.
- **SC-006**: Failed syncs retry automatically up to 3 times before notifying the owner.
- **SC-007**: Business Owners can view sync status and history at any time.
- **SC-008**: Manual sync triggers complete within 2 minutes for typical business data volumes (up to 100 records).

## 6. Assumptions & Constraints

### Assumptions

- Businesses using this feature have active QuickBooks Online subscriptions (not QuickBooks Desktop).
- Businesses operate in regions where QuickBooks Online is available.
- HereCRM has a registered QuickBooks app with valid OAuth credentials (client ID, client secret).
- QuickBooks API rate limits are sufficient for hourly batch processing (typical limits: 500 requests per minute).
- Business Owners have administrative access to their QuickBooks account to authorize the integration.
- Internet connectivity is generally reliable for both HereCRM and QuickBooks services.

### Constraints

- **Sync Frequency**: Hourly batch sync (not real-time) to balance data freshness with API rate limits and system load.
- **Unidirectional Sync**: Data flows only from HereCRM to QuickBooks (no data pulled from QuickBooks except for tax calculation in future features).
- **OAuth Token Lifespan**: QuickBooks access tokens expire after 1 hour; refresh tokens expire after 100 days of inactivity.
- **Data Mapping Limitations**: Some HereCRM fields may not have direct QuickBooks equivalents and may require transformation or omission.
- **API Dependencies**: Feature functionality is dependent on QuickBooks API availability and stability.

### Out of Scope

- **Tax Calculation**: Automatic tax calculation using QuickBooks or Stripe Tax is explicitly excluded from this feature (deferred to future enhancement).
- **QuickBooks → HereCRM Sync**: Pulling data from QuickBooks into HereCRM is not included.
- **QuickBooks Desktop**: Only QuickBooks Online is supported.
- **Financial Reporting**: Generating reports or analytics from QuickBooks data is not included.
- **Multi-Currency**: Initial version assumes single currency per business.
- **Custom Field Mapping**: Business-specific custom field mapping is not supported in initial version.

## 7. Dependencies

- **Existing Features**:
  - `006-professional-invoices`: Invoice generation and management
  - `004-line-items-and-service-catalog`: Service catalog for product/item sync
  - Customer/Client management system
  - Payment recording system

- **External Services**:
  - QuickBooks Online API (v3)
  - QuickBooks OAuth 2.0 authorization server

- **Infrastructure**:
  - Scheduled job system (cron or task scheduler) for hourly sync
  - Secure credential storage (encryption at rest)
  - Webhook/callback endpoint for OAuth flow

## 8. Security & Compliance

- **SEC-001**: OAuth tokens MUST be encrypted at rest in the database.
- **SEC-002**: OAuth tokens MUST be transmitted only over HTTPS.
- **SEC-003**: Refresh tokens MUST be rotated according to QuickBooks best practices.
- **SEC-004**: System MUST implement proper OAuth state parameter validation to prevent CSRF attacks.
- **SEC-005**: Access to QuickBooks credentials MUST be restricted to authorized system components only.
- **SEC-006**: Sync logs MUST NOT contain sensitive financial data in plain text.
- **SEC-007**: Business Owners MUST be able to revoke QuickBooks access at any time.

## 9. Edge Cases & Error Scenarios

### Edge Case 1: Token Refresh Failure

- **Scenario**: Refresh token has expired or been revoked
- **Handling**: Notify Business Owner that QuickBooks connection has been lost and requires re-authorization

### Edge Case 2: Duplicate Detection Failure

- **Scenario**: Mapping record exists but QuickBooks record was manually deleted
- **Handling**: Attempt to update fails, system creates new record and updates mapping

### Edge Case 3: Concurrent Modifications

- **Scenario**: Invoice updated in HereCRM during sync operation
- **Handling**: Next sync cycle will capture the latest changes (eventual consistency)

### Edge Case 4: Large Batch Size

- **Scenario**: Business has 500+ pending records to sync
- **Handling**: Process in smaller batches to respect API rate limits, may take multiple sync cycles

### Edge Case 5: Partial Batch Failure

- **Scenario**: 10 out of 50 records fail due to validation errors
- **Handling**: Successfully sync 40 records, log 10 failures, notify owner with summary

### Edge Case 6: QuickBooks Account Suspension

- **Scenario**: Business's QuickBooks subscription expires or is suspended
- **Handling**: API returns authorization error, system notifies owner that QuickBooks access is unavailable

## 10. Future Enhancements

The following enhancements are explicitly out of scope for this feature but may be considered in future iterations:

- **Tax Calculation Integration**: Leverage QuickBooks or Stripe Tax for automatic tax calculation on invoices
- **Bidirectional Sync**: Pull data from QuickBooks into HereCRM (expenses, bills, vendor payments)
- **Real-time Sync**: Webhook-based real-time synchronization instead of hourly batches
- **Custom Field Mapping**: Allow businesses to map custom fields between systems
- **Multi-Currency Support**: Handle businesses operating in multiple currencies
- **Advanced Reporting**: Financial reports and dashboards using QuickBooks data
- **QuickBooks Desktop Support**: Extend integration to QuickBooks Desktop via Web Connector
- **Selective Sync**: Allow businesses to choose which data types to sync
- **Conflict Resolution**: Handle scenarios where records are modified in both systems
