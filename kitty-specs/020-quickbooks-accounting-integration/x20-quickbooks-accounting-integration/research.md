# Research: QuickBooks Accounting Integration

**Feature**: 020-quickbooks-accounting-integration  
**Date**: 2026-01-21  
**Purpose**: Document technical research and decisions for QuickBooks Online API integration

---

## Research Tasks

### 1. QuickBooks Online API v3 Integration Patterns

**Question**: What are the best practices for integrating with QuickBooks Online API v3 in Python?

**Findings**:

#### API Structure

- **Base URL**: `https://quickbooks.api.intuit.com/v3/company/{realmId}/`
- **Authentication**: OAuth 2.0 (required for all requests)
- **Data Format**: JSON (request and response)
- **Rate Limits**: 500 requests per minute per app (across all businesses)

#### Entity Endpoints

- **Customer**: `POST /customer` (create), `POST /customer?operation=update` (update)
- **Item** (Service/Product): `POST /item`, `POST /item?operation=update`
- **Invoice**: `POST /invoice`, `POST /invoice?operation=update`
- **Payment**: `POST /payment`, `POST /payment?operation=update`

#### Key Constraints

- ❌ **No batch create/update**: Each record requires individual API call
- ✅ **Batch query**: Can query multiple entities in one request (read-only)
- ⚠️ **Sparse updates**: Can update specific fields without sending entire object
- 🔄 **SyncToken**: Required for updates (prevents concurrent modification conflicts)

**Decision**: Use `python-quickbooks` SDK which handles:

- OAuth token management
- API request formatting
- SyncToken tracking
- Error handling and retries

---

### 2. OAuth 2.0 Flow for QuickBooks

**Question**: How should we implement the OAuth 2.0 authorization flow for QuickBooks?

**Findings**:

#### OAuth Flow Steps

1. **Authorization Request**: Redirect user to Intuit's OAuth server

   ```
   https://appcenter.intuit.com/connect/oauth2?
     client_id={CLIENT_ID}&
     redirect_uri={REDIRECT_URI}&
     response_type=code&
     scope=com.intuit.quickbooks.accounting&
     state={CSRF_TOKEN}
   ```

2. **Authorization Callback**: Intuit redirects back with authorization code

   ```
   {REDIRECT_URI}?code={AUTH_CODE}&state={CSRF_TOKEN}&realmId={REALM_ID}
   ```

3. **Token Exchange**: Exchange code for access + refresh tokens

   ```python
   POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer
   Headers: Authorization: Basic {base64(client_id:client_secret)}
   Body: grant_type=authorization_code&code={AUTH_CODE}&redirect_uri={REDIRECT_URI}
   ```

4. **Token Response**:

   ```json
   {
     "access_token": "...",
     "refresh_token": "...",
     "expires_in": 3600,
     "x_refresh_token_expires_in": 8726400
   }
   ```

#### Token Lifecycle

- **Access Token**: Expires in 1 hour
- **Refresh Token**: Expires in 100 days (if unused)
- **Refresh Process**: Use refresh token to get new access token before expiry

**Decision**:

- Host OAuth flow on `herecrm.io` website (follows Stripe Connect pattern)
- Use `authlib` for OAuth client implementation
- Store tokens in SQLCipher-encrypted database
- Implement automatic token refresh before each sync operation

---

### 3. SQLCipher for Encrypted Credential Storage

**Question**: How do we securely store OAuth tokens in a separate encrypted database?

**Findings**:

#### SQLCipher Overview

- **What**: SQLite extension with transparent AES-256 encryption
- **Python Library**: `pysqlcipher3` (Python 3 compatible)
- **Encryption**: Entire database file encrypted at rest
- **Key Management**: Encryption key provided at connection time

#### Implementation Pattern

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

# Encryption key from environment variable
CREDENTIALS_DB_KEY = os.getenv("CREDENTIALS_DB_KEY")

# SQLCipher connection string
engine = create_engine(
    f"sqlite+pysqlcipher://:{CREDENTIALS_DB_KEY}@/credentials.db?cipher=aes-256-cfb&kdf_iter=64000",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
```

#### Schema Design

```python
class QuickBooksCredential(Base):
    __tablename__ = "quickbooks_credentials"
    
    business_id = Column(Integer, primary_key=True)  # FK to main DB
    realm_id = Column(String, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=False)
    connected_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
```

**Decision**:

- Use `pysqlcipher3` for encrypted database
- Store encryption key in environment variable (never in code)
- Separate session factory for credentials database
- Only store sensitive OAuth tokens in encrypted DB
- Store sync metadata (QuickBooks IDs, sync status) in main DB

---

### 4. Data Mapping: HereCRM → QuickBooks

**Question**: How do we map HereCRM entities to QuickBooks entities?

**Findings**:

#### Entity Mappings

**Customer (HereCRM) → Customer (QuickBooks)**

```python
{
    "DisplayName": customer.name,
    "PrimaryPhone": {"FreeFormNumber": customer.phone},
    "PrimaryEmailAddr": {"Address": customer.email},
    "BillAddr": {
        "Line1": customer.street,
        "City": customer.city,
        "CountrySubDivisionCode": customer.state,  # If available
        "PostalCode": customer.postal_code  # If available
    }
}
```

**Service (HereCRM) → Item (QuickBooks)**

```python
{
    "Name": service.name,
    "Description": service.description,
    "Type": "Service",
    "IncomeAccountRef": {"value": "1"},  # Default income account
    "UnitPrice": service.default_price
}
```

**Job + LineItems (HereCRM) → Invoice (QuickBooks)**

```python
{
    "CustomerRef": {"value": quickbooks_customer_id},
    "TxnDate": job.created_at.strftime("%Y-%m-%d"),
    "DueDate": (job.created_at + timedelta(days=30)).strftime("%Y-%m-%d"),
    "Line": [
        {
            "DetailType": "SalesItemLineDetail",
            "Amount": line_item.total_price,
            "SalesItemLineDetail": {
                "ItemRef": {"value": quickbooks_item_id},
                "Qty": line_item.quantity,
                "UnitPrice": line_item.unit_price
            }
        }
        for line_item in job.line_items
    ]
}
```

**Payment (HereCRM) → Payment (QuickBooks)**

```python
{
    "CustomerRef": {"value": quickbooks_customer_id},
    "TotalAmt": payment.amount,
    "TxnDate": payment.payment_date.strftime("%Y-%m-%d"),
    "Line": [{
        "Amount": payment.amount,
        "LinkedTxn": [{
            "TxnId": quickbooks_invoice_id,
            "TxnType": "Invoice"
        }]
    }]
}
```

#### Dependency Order

1. **Customers first**: Must exist before creating invoices
2. **Services second**: Must exist before creating invoice line items
3. **Invoices third**: Require customer and service references
4. **Payments last**: Require invoice references

**Decision**:

- Create `sync_mappers.py` module with mapping functions
- Validate required fields before API calls (fail fast)
- Store QuickBooks IDs in main database for future updates
- Use SyncToken for update operations (prevent conflicts)

---

### 5. APScheduler for Hourly Batch Sync

**Question**: How do we implement hourly automated synchronization?

**Findings**:

#### APScheduler Configuration

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

# Run every hour at :00 minutes
scheduler.add_job(
    sync_all_businesses,
    trigger=CronTrigger(minute=0),
    id="quickbooks_hourly_sync",
    replace_existing=True
)

scheduler.start()
```

#### Sync Job Logic

```python
async def sync_all_businesses():
    """Sync QuickBooks for all connected businesses."""
    async with get_session() as session:
        # Get all businesses with QuickBooks connected
        businesses = await get_connected_businesses(session)
        
        for business in businesses:
            try:
                await sync_business_to_quickbooks(business.id)
            except Exception as e:
                logger.error(f"Sync failed for business {business.id}: {e}")
                # Continue with other businesses
```

#### Error Handling

- **Retry Logic**: 3 attempts with exponential backoff (1min, 2min, 4min)
- **Partial Failures**: Continue processing other records if one fails
- **Notifications**: Send WhatsApp message for critical errors only

**Decision**:

- Use APScheduler with AsyncIO scheduler (matches existing async patterns)
- Run hourly sync at :00 minutes (predictable timing)
- Process businesses sequentially (avoid rate limit issues)
- Log all sync operations to SyncLog table
- Implement retry logic at individual record level

---

### 6. Conversation State: ACCOUNTING

**Question**: How should we integrate QuickBooks commands into the conversational interface?

**Findings**:

#### Existing Pattern: DATA_MANAGEMENT State

- User enters state via conversational command
- LLM parses commands within that state
- State-specific tools available
- Exit state via "back" or "done"

#### ACCOUNTING State Design

```python
class ConversationStatus(str, enum.Enum):
    IDLE = "idle"
    WAITING_CONFIRM = "waiting_confirm"
    PENDING_AUTO_CONFIRM = "pending_auto_confirm"
    SETTINGS = "settings"
    DATA_MANAGEMENT = "data_management"
    BILLING = "billing"
    ACCOUNTING = "accounting"  # NEW
```

#### ACCOUNTING State Commands

- **"Connect QuickBooks"**: Initiate OAuth flow
- **"Sync now"**: Trigger immediate sync
- **"QuickBooks status"**: Show sync status and errors
- **"Disconnect QuickBooks"**: Remove OAuth credentials

#### LLM Parser Method

```python
async def parse_accounting(self, text: str) -> AccountingTool:
    """Parse accounting-related commands."""
    # LLM extracts intent and parameters
    # Returns appropriate tool: ConnectQBTool, SyncQBTool, QBStatusTool, DisconnectQBTool
```

**Decision**:

- Add `ACCOUNTING` to `ConversationStatus` enum
- Create `parse_accounting()` method in `llm_client.py`
- Add accounting tools to `uimodels.py`
- Follow `data_management.py` pattern for state handling
- Update `messages.yaml` with ACCOUNTING state prompts

---

### 7. Address Validation When QuickBooks Connected

**Question**: How do we enforce address requirements when QuickBooks is connected?

**Findings**:

#### QuickBooks Address Requirements

- QuickBooks **recommends** but doesn't strictly require addresses for customers
- However, for proper accounting and tax reporting, addresses are highly recommended
- Missing addresses can cause issues with tax calculation features (future enhancement)

#### Validation Strategy

```python
async def validate_customer_for_quickbooks(customer: Customer, business: Business) -> None:
    """Validate customer has required fields for QuickBooks sync."""
    if not business.quickbooks_realm_id:
        return  # QuickBooks not connected, no validation needed
    
    if not customer.street or not customer.city:
        raise ValidationError(
            "Customer address is required when QuickBooks is connected. "
            "Please provide street and city."
        )
```

#### Integration Points

- **Customer creation**: Validate before saving
- **Job creation**: Validate associated customer has address
- **Invoice generation**: Validate customer address exists

**Decision**:

- Enforce address validation (street + city minimum) when QuickBooks connected
- Add validation to customer creation/update flows
- Leverage existing geocoding service for address lookup
- Provide clear error messages guiding users to add addresses
- Allow disconnecting QuickBooks to bypass validation if needed

---

## Summary of Key Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **API Client** | `python-quickbooks` SDK | Handles OAuth, SyncToken, error handling |
| **OAuth Flow** | Hosted on `herecrm.io` | Follows Stripe Connect pattern, secure callback |
| **Token Storage** | SQLCipher-encrypted DB | Isolates sensitive credentials, AES-256 encryption |
| **Sync Schedule** | APScheduler hourly | Balances freshness with API limits |
| **Sync Strategy** | Individual API calls | QuickBooks limitation (no batch endpoints) |
| **Dependency Order** | Customers → Services → Invoices → Payments | Ensures references exist |
| **Error Handling** | 3 retries + proactive notifications | Resilient sync, user awareness |
| **Conversation State** | New ACCOUNTING state | Follows DATA_MANAGEMENT pattern |
| **Address Validation** | Required when QB connected | Prevents sync failures, ensures data quality |
| **Data Mapping** | Dedicated mapper module | Clean separation, testable |

---

## Open Questions for Phase 1

1. **Website Integration**: What's the exact callback URL structure on `herecrm.io`?
2. **Environment Variables**: Where are QuickBooks app credentials (client ID, secret) stored?
3. **Scheduler Lifecycle**: Where/when is APScheduler initialized in the application?
4. **Error Notification Format**: What's the exact message template for sync errors?

These will be resolved during Phase 1 design and implementation.
