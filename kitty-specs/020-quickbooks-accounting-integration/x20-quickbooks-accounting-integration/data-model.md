# Data Model: QuickBooks Accounting Integration

**Feature**: 020-quickbooks-accounting-integration  
**Date**: 2026-01-21  
**Purpose**: Define database schema changes and entity relationships for QuickBooks sync

---

## Overview

This feature requires changes to existing entities and introduces new entities for tracking QuickBooks synchronization state. The design uses **two databases**:

1. **Main Database** (`main.db`): Sync metadata, QuickBooks IDs, sync status
2. **Credentials Database** (`credentials.db`): SQLCipher-encrypted OAuth tokens

---

## Main Database Schema Changes

### 1. Business Entity (Existing - Modified)

**Purpose**: Track QuickBooks connection status and last sync timestamp

**New Fields**:

```python
class Business(Base):
    __tablename__ = "businesses"
    
    # ... existing fields ...
    
    # QuickBooks connection metadata (non-sensitive)
    quickbooks_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    quickbooks_last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

**Notes**:

- `quickbooks_connected`: Quick check if QuickBooks is active (avoids credentials DB lookup)
- `quickbooks_last_sync`: Timestamp of last successful sync (for status display)
- Sensitive OAuth tokens stored in separate encrypted database

---

### 2. Invoice Entity (Existing - Modified)

**Purpose**: Track QuickBooks sync status for invoices

**New Fields**:

```python
class Invoice(Base):
    __tablename__ = "invoices"
    
    # ... existing fields ...
    
    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[str]] = mapped_column(
        SAEnum("pending", "synced", "failed", name="qb_sync_status"),
        nullable=True,
        default="pending"
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

**Field Descriptions**:

- `quickbooks_id`: QuickBooks Invoice ID (for updates)
- `quickbooks_synced_at`: Last successful sync timestamp
- `quickbooks_sync_status`: Current sync state
  - `pending`: Not yet synced or needs re-sync
  - `synced`: Successfully synced to QuickBooks
  - `failed`: Sync failed (see error field)
- `quickbooks_sync_error`: Error message if sync failed

**Indexes**:

- `quickbooks_id`: For lookup when updating existing QuickBooks invoices
- `quickbooks_sync_status`: For querying pending/failed invoices

---

### 3. Payment Entity (Existing - Modified)

**Purpose**: Track QuickBooks sync status for payments

**New Fields**:

```python
class Payment(Base):
    __tablename__ = "payments"
    
    # ... existing fields ...
    
    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[str]] = mapped_column(
        SAEnum("pending", "synced", "failed", name="qb_sync_status"),
        nullable=True,
        default="pending"
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

**Notes**: Same structure as Invoice sync tracking

---

### 4. Customer Entity (Existing - Modified)

**Purpose**: Track QuickBooks sync status for customers

**New Fields**:

```python
class Customer(Base):
    __tablename__ = "customers"
    
    # ... existing fields ...
    
    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[str]] = mapped_column(
        SAEnum("pending", "synced", "failed", name="qb_sync_status"),
        nullable=True,
        default="pending"
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

**Address Validation**:

- When `Business.quickbooks_connected == True`, require `Customer.street` and `Customer.city`
- Validation enforced at application level (not database constraint)

---

### 5. Service Entity (Existing - Modified)

**Purpose**: Track QuickBooks sync status for services/items

**New Fields**:

```python
class Service(Base):
    __tablename__ = "services"
    
    # ... existing fields ...
    
    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[str]] = mapped_column(
        SAEnum("pending", "synced", "failed", name="qb_sync_status"),
        nullable=True,
        default="pending"
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
```

---

### 6. SyncLog Entity (New)

**Purpose**: Audit trail of sync operations for debugging and status display

**Schema**:

```python
class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    
    # Sync metadata
    sync_timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    sync_type: Mapped[str] = mapped_column(
        SAEnum("scheduled", "manual", name="sync_type"),
        nullable=False
    )
    
    # Results
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status and errors
    status: Mapped[str] = mapped_column(
        SAEnum("success", "partial_success", "failed", name="sync_log_status"),
        nullable=False
    )
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Duration tracking
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    business: Mapped["Business"] = relationship(back_populates="sync_logs")
```

**Indexes**:

- `business_id`: For querying sync history per business
- Composite index on `(business_id, sync_timestamp)`: For recent sync queries

**Usage**:

- Created at start of each sync operation
- Updated with results at completion
- Queried for "QuickBooks status" command
- Used for debugging sync issues

---

## Credentials Database Schema (SQLCipher-Encrypted)

### 7. QuickBooksCredential Entity (New)

**Purpose**: Securely store OAuth tokens in encrypted database

**Schema**:

```python
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool
import os

CredentialsBase = declarative_base()

class QuickBooksCredential(CredentialsBase):
    __tablename__ = "quickbooks_credentials"
    
    # Primary key is business_id (one-to-one with Business in main DB)
    business_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # QuickBooks OAuth data
    realm_id: Mapped[str] = mapped_column(String(50), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_expiry: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Metadata
    connected_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

# Separate engine for credentials database
CREDENTIALS_DB_KEY = os.getenv("CREDENTIALS_DB_KEY")
credentials_engine = create_engine(
    f"sqlite+pysqlcipher://:{CREDENTIALS_DB_KEY}@/credentials.db?cipher=aes-256-cfb&kdf_iter=64000",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

CredentialsBase.metadata.create_all(credentials_engine)
```

**Security Notes**:

- Entire database file encrypted with AES-256
- Encryption key stored in environment variable (never in code or version control)
- No foreign key constraints (separate database)
- `business_id` used to correlate with main database

---

## Entity Relationships

```
Main Database:
┌─────────────┐
│  Business   │
│             │
│ + qb_connected: bool
│ + qb_last_sync: datetime
└──────┬──────┘
       │
       │ 1:N
       ├──────────────────┬──────────────────┬──────────────────┐
       │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Customer   │    │   Service   │    │   Invoice   │    │   Payment   │
│             │    │             │    │             │    │             │
│ + qb_id     │    │ + qb_id     │    │ + qb_id     │    │ + qb_id     │
│ + qb_status │    │ + qb_status │    │ + qb_status │    │ + qb_status │
│ + qb_error  │    │ + qb_error  │    │ + qb_error  │    │ + qb_error  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘

       │
       │ 1:N
       ▼
┌─────────────┐
│  SyncLog    │
│             │
│ + sync_type
│ + status
│ + records_*
│ + errors
└─────────────┘

Credentials Database (Encrypted):
┌──────────────────────┐
│ QuickBooksCredential │
│                      │
│ business_id (PK)     │◄─── Correlates with Business.id
│ + realm_id           │
│ + access_token       │
│ + refresh_token      │
│ + token_expiry       │
└──────────────────────┘
```

---

## Sync State Machine

Each syncable entity (Customer, Service, Invoice, Payment) follows this state machine:

```
┌─────────┐
│  NULL   │  (Initial state - never synced)
└────┬────┘
     │ Business connects QuickBooks
     ▼
┌─────────┐
│ PENDING │  (Queued for sync)
└────┬────┘
     │ Sync job runs
     ├──────────┬──────────┐
     ▼          ▼          ▼
┌─────────┐  ┌────────┐  ┌────────┐
│ SYNCED  │  │ FAILED │  │ SYNCED │
└────┬────┘  └───┬────┘  └───┬────┘
     │           │            │
     │ Record    │ Retry      │ Record
     │ updated   │ or fix     │ updated
     ▼           ▼            ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│ PENDING │  │ PENDING │  │ PENDING │
└─────────┘  └─────────┘  └─────────┘
```

**State Transitions**:

- `NULL → PENDING`: When QuickBooks is connected or record is created/updated
- `PENDING → SYNCED`: Successful sync to QuickBooks
- `PENDING → FAILED`: Sync failed (validation error, API error, etc.)
- `SYNCED → PENDING`: Record updated in HereCRM (needs re-sync)
- `FAILED → PENDING`: User fixes issue or manual retry

---

## Migration Strategy

### Alembic Migration

```python
"""Add QuickBooks sync fields

Revision ID: <timestamp>
Revises: <previous_revision>
Create Date: 2026-01-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

def upgrade():
    # Add fields to Business
    op.add_column('businesses', sa.Column('quickbooks_connected', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('businesses', sa.Column('quickbooks_last_sync', sa.DateTime(), nullable=True))
    
    # Create sync status enum
    sync_status_enum = sa.Enum('pending', 'synced', 'failed', name='qb_sync_status')
    
    # Add fields to Customer
    op.add_column('customers', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('customers', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('customers', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('customers', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_customers_quickbooks_id', 'customers', ['quickbooks_id'])
    
    # Add fields to Service
    op.add_column('services', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('services', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('services', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('services', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_services_quickbooks_id', 'services', ['quickbooks_id'])
    
    # Add fields to Invoice
    op.add_column('invoices', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('invoices', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('invoices', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('invoices', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_invoices_quickbooks_id', 'invoices', ['quickbooks_id'])
    
    # Add fields to Payment
    op.add_column('payments', sa.Column('quickbooks_id', sa.String(50), nullable=True))
    op.add_column('payments', sa.Column('quickbooks_synced_at', sa.DateTime(), nullable=True))
    op.add_column('payments', sa.Column('quickbooks_sync_status', sync_status_enum, nullable=True))
    op.add_column('payments', sa.Column('quickbooks_sync_error', sa.Text(), nullable=True))
    op.create_index('ix_payments_quickbooks_id', 'payments', ['quickbooks_id'])
    
    # Create SyncLog table
    op.create_table(
        'sync_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('sync_timestamp', sa.DateTime(), nullable=False),
        sa.Column('sync_type', sa.Enum('scheduled', 'manual', name='sync_type'), nullable=False),
        sa.Column('records_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_succeeded', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_failed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Enum('success', 'partial_success', 'failed', name='sync_log_status'), nullable=False),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sync_logs_business_id', 'sync_logs', ['business_id'])
    op.create_index('ix_sync_logs_business_timestamp', 'sync_logs', ['business_id', 'sync_timestamp'])

def downgrade():
    # Drop SyncLog table
    op.drop_index('ix_sync_logs_business_timestamp', 'sync_logs')
    op.drop_index('ix_sync_logs_business_id', 'sync_logs')
    op.drop_table('sync_logs')
    
    # Remove fields from Payment
    op.drop_index('ix_payments_quickbooks_id', 'payments')
    op.drop_column('payments', 'quickbooks_sync_error')
    op.drop_column('payments', 'quickbooks_sync_status')
    op.drop_column('payments', 'quickbooks_synced_at')
    op.drop_column('payments', 'quickbooks_id')
    
    # Remove fields from Invoice
    op.drop_index('ix_invoices_quickbooks_id', 'invoices')
    op.drop_column('invoices', 'quickbooks_sync_error')
    op.drop_column('invoices', 'quickbooks_sync_status')
    op.drop_column('invoices', 'quickbooks_synced_at')
    op.drop_column('invoices', 'quickbooks_id')
    
    # Remove fields from Service
    op.drop_index('ix_services_quickbooks_id', 'services')
    op.drop_column('services', 'quickbooks_sync_error')
    op.drop_column('services', 'quickbooks_sync_status')
    op.drop_column('services', 'quickbooks_synced_at')
    op.drop_column('services', 'quickbooks_id')
    
    # Remove fields from Customer
    op.drop_index('ix_customers_quickbooks_id', 'customers')
    op.drop_column('customers', 'quickbooks_sync_error')
    op.drop_column('customers', 'quickbooks_sync_status')
    op.drop_column('customers', 'quickbooks_synced_at')
    op.drop_column('customers', 'quickbooks_id')
    
    # Remove fields from Business
    op.drop_column('businesses', 'quickbooks_last_sync')
    op.drop_column('businesses', 'quickbooks_connected')
```

---

## Data Integrity Constraints

### Application-Level Validations

1. **Address Validation** (when QuickBooks connected):

   ```python
   if business.quickbooks_connected and not (customer.street and customer.city):
       raise ValidationError("Address required when QuickBooks is connected")
   ```

2. **Sync Status Consistency**:
   - Only set `quickbooks_sync_status = "synced"` when `quickbooks_id` is populated
   - Clear `quickbooks_sync_error` when status changes to "synced"

3. **Token Expiry Checks**:
   - Refresh access token if `token_expiry < now() + 5 minutes`
   - Notify business owner if refresh token expired (requires re-authorization)

### Database-Level Constraints

- Foreign keys: `business_id` in all entities
- Indexes: `quickbooks_id` for efficient lookups
- Enums: Enforce valid sync status values

---

## Summary

This data model design:

- ✅ Separates sensitive credentials (encrypted DB) from sync metadata (main DB)
- ✅ Tracks sync status at entity level for granular error handling
- ✅ Provides audit trail via SyncLog for debugging and status display
- ✅ Supports incremental sync (only pending/failed records)
- ✅ Enables address validation when QuickBooks is connected
- ✅ Follows existing HereCRM patterns (SQLAlchemy, Alembic migrations)
