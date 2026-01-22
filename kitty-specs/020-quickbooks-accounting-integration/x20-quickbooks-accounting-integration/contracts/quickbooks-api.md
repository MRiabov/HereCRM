# API Contracts: QuickBooks Online Integration

**Feature**: 020-quickbooks-accounting-integration  
**Date**: 2026-01-21  
**Purpose**: Document QuickBooks Online API v3 integration contracts and data mappings

---

## Overview

This document defines the contracts between HereCRM and QuickBooks Online API v3. All API calls use OAuth 2.0 authentication and JSON format.

**Base URL**: `https://quickbooks.api.intuit.com/v3/company/{realmId}/`  
**Authentication**: `Authorization: Bearer {access_token}`  
**Content-Type**: `application/json`

---

## 1. OAuth 2.0 Authentication Flow

### 1.1 Authorization Request

**Endpoint**: `https://appcenter.intuit.com/connect/oauth2`  
**Method**: `GET` (browser redirect)

**Parameters**:

```
client_id={CLIENT_ID}
redirect_uri={REDIRECT_URI}
response_type=code
scope=com.intuit.quickbooks.accounting
state={CSRF_TOKEN}
```

**Response**: Redirect to `{REDIRECT_URI}` with:

```
code={AUTH_CODE}
state={CSRF_TOKEN}
realmId={REALM_ID}
```

---

### 1.2 Token Exchange

**Endpoint**: `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`  
**Method**: `POST`

**Headers**:

```
Authorization: Basic {base64(client_id:client_secret)}
Content-Type: application/x-www-form-urlencoded
```

**Body**:

```
grant_type=authorization_code
code={AUTH_CODE}
redirect_uri={REDIRECT_URI}
```

**Response**:

```json
{
  "access_token": "eyJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwiYWxnIjoiZGlyIn0...",
  "refresh_token": "L011546037639r06SpFOlh9QONLhAzMKlo5rJwLN4TQnN0IbqA",
  "token_type": "bearer",
  "expires_in": 3600,
  "x_refresh_token_expires_in": 8726400
}
```

---

### 1.3 Token Refresh

**Endpoint**: `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`  
**Method**: `POST`

**Headers**:

```
Authorization: Basic {base64(client_id:client_secret)}
Content-Type: application/x-www-form-urlencoded
```

**Body**:

```
grant_type=refresh_token
refresh_token={REFRESH_TOKEN}
```

**Response**: Same as Token Exchange

---

## 2. Customer API

### 2.1 Create Customer

**Endpoint**: `POST /customer`

**Request Body**:

```json
{
  "DisplayName": "John Doe",
  "PrimaryPhone": {
    "FreeFormNumber": "+1234567890"
  },
  "PrimaryEmailAddr": {
    "Address": "john@example.com"
  },
  "BillAddr": {
    "Line1": "123 Main St",
    "City": "Springfield",
    "CountrySubDivisionCode": "IL",
    "PostalCode": "62701",
    "Country": "USA"
  }
}
```

**Response** (201 Created):

```json
{
  "Customer": {
    "Id": "58",
    "DisplayName": "John Doe",
    "PrimaryPhone": {
      "FreeFormNumber": "+1234567890"
    },
    "PrimaryEmailAddr": {
      "Address": "john@example.com"
    },
    "BillAddr": {
      "Id": "59",
      "Line1": "123 Main St",
      "City": "Springfield",
      "CountrySubDivisionCode": "IL",
      "PostalCode": "62701",
      "Country": "USA"
    },
    "SyncToken": "0",
    "MetaData": {
      "CreateTime": "2026-01-21T20:00:00Z",
      "LastUpdatedTime": "2026-01-21T20:00:00Z"
    }
  },
  "time": "2026-01-21T20:00:00.123Z"
}
```

**HereCRM Mapping**:

```python
{
    "DisplayName": customer.name,
    "PrimaryPhone": {"FreeFormNumber": customer.phone} if customer.phone else None,
    "PrimaryEmailAddr": {"Address": customer.email} if customer.email else None,
    "BillAddr": {
        "Line1": customer.street,
        "City": customer.city,
        "CountrySubDivisionCode": customer.state or "",
        "PostalCode": customer.postal_code or "",
        "Country": "USA"  # Default for US-based businesses
    } if customer.street and customer.city else None
}
```

---

### 2.2 Update Customer

**Endpoint**: `POST /customer?operation=update`

**Request Body**:

```json
{
  "Id": "58",
  "DisplayName": "John Doe Updated",
  "SyncToken": "0",
  "sparse": true
}
```

**Notes**:

- `SyncToken` required (prevents concurrent modification conflicts)
- `sparse: true` allows partial updates (only changed fields)

---

## 3. Item (Service/Product) API

### 3.1 Create Item

**Endpoint**: `POST /item`

**Request Body**:

```json
{
  "Name": "Lawn Mowing",
  "Description": "Standard lawn mowing service",
  "Type": "Service",
  "IncomeAccountRef": {
    "value": "1"
  },
  "UnitPrice": 50.00
}
```

**Response** (201 Created):

```json
{
  "Item": {
    "Id": "12",
    "Name": "Lawn Mowing",
    "Description": "Standard lawn mowing service",
    "Type": "Service",
    "IncomeAccountRef": {
      "value": "1",
      "name": "Sales"
    },
    "UnitPrice": 50.00,
    "SyncToken": "0",
    "MetaData": {
      "CreateTime": "2026-01-21T20:00:00Z",
      "LastUpdatedTime": "2026-01-21T20:00:00Z"
    }
  },
  "time": "2026-01-21T20:00:00.123Z"
}
```

**HereCRM Mapping**:

```python
{
    "Name": service.name,
    "Description": service.description or "",
    "Type": "Service",
    "IncomeAccountRef": {"value": "1"},  # Default income account
    "UnitPrice": service.default_price
}
```

---

### 3.2 Update Item

**Endpoint**: `POST /item?operation=update`

**Request Body**:

```json
{
  "Id": "12",
  "Name": "Lawn Mowing - Premium",
  "UnitPrice": 75.00,
  "SyncToken": "0",
  "sparse": true
}
```

---

## 4. Invoice API

### 4.1 Create Invoice

**Endpoint**: `POST /invoice`

**Request Body**:

```json
{
  "CustomerRef": {
    "value": "58"
  },
  "TxnDate": "2026-01-21",
  "DueDate": "2026-02-20",
  "Line": [
    {
      "DetailType": "SalesItemLineDetail",
      "Amount": 100.00,
      "Description": "Lawn mowing for January",
      "SalesItemLineDetail": {
        "ItemRef": {
          "value": "12"
        },
        "Qty": 2,
        "UnitPrice": 50.00
      }
    }
  ]
}
```

**Response** (201 Created):

```json
{
  "Invoice": {
    "Id": "145",
    "DocNumber": "1001",
    "CustomerRef": {
      "value": "58",
      "name": "John Doe"
    },
    "TxnDate": "2026-01-21",
    "DueDate": "2026-02-20",
    "TotalAmt": 100.00,
    "Balance": 100.00,
    "Line": [
      {
        "Id": "1",
        "LineNum": 1,
        "Amount": 100.00,
        "DetailType": "SalesItemLineDetail",
        "Description": "Lawn mowing for January",
        "SalesItemLineDetail": {
          "ItemRef": {
            "value": "12",
            "name": "Lawn Mowing"
          },
          "Qty": 2,
          "UnitPrice": 50.00,
          "TaxCodeRef": {
            "value": "NON"
          }
        }
      }
    ],
    "SyncToken": "0",
    "MetaData": {
      "CreateTime": "2026-01-21T20:00:00Z",
      "LastUpdatedTime": "2026-01-21T20:00:00Z"
    }
  },
  "time": "2026-01-21T20:00:00.123Z"
}
```

**HereCRM Mapping** (Job → Invoice):

```python
{
    "CustomerRef": {"value": customer.quickbooks_id},
    "TxnDate": job.created_at.strftime("%Y-%m-%d"),
    "DueDate": (job.created_at + timedelta(days=30)).strftime("%Y-%m-%d"),
    "Line": [
        {
            "DetailType": "SalesItemLineDetail",
            "Amount": line_item.total_price,
            "Description": line_item.description or service.description,
            "SalesItemLineDetail": {
                "ItemRef": {"value": service.quickbooks_id},
                "Qty": line_item.quantity,
                "UnitPrice": line_item.unit_price
            }
        }
        for line_item in job.line_items
    ]
}
```

---

### 4.2 Update Invoice

**Endpoint**: `POST /invoice?operation=update`

**Request Body**:

```json
{
  "Id": "145",
  "SyncToken": "0",
  "Line": [
    {
      "Id": "1",
      "DetailType": "SalesItemLineDetail",
      "Amount": 150.00,
      "SalesItemLineDetail": {
        "ItemRef": {
          "value": "12"
        },
        "Qty": 3,
        "UnitPrice": 50.00
      }
    }
  ],
  "sparse": true
}
```

---

## 5. Payment API

### 5.1 Create Payment

**Endpoint**: `POST /payment`

**Request Body**:

```json
{
  "CustomerRef": {
    "value": "58"
  },
  "TotalAmt": 100.00,
  "TxnDate": "2026-01-22",
  "Line": [
    {
      "Amount": 100.00,
      "LinkedTxn": [
        {
          "TxnId": "145",
          "TxnType": "Invoice"
        }
      ]
    }
  ]
}
```

**Response** (201 Created):

```json
{
  "Payment": {
    "Id": "89",
    "CustomerRef": {
      "value": "58",
      "name": "John Doe"
    },
    "TotalAmt": 100.00,
    "TxnDate": "2026-01-22",
    "Line": [
      {
        "Amount": 100.00,
        "LinkedTxn": [
          {
            "TxnId": "145",
            "TxnType": "Invoice"
          }
        ]
      }
    ],
    "SyncToken": "0",
    "MetaData": {
      "CreateTime": "2026-01-22T10:00:00Z",
      "LastUpdatedTime": "2026-01-22T10:00:00Z"
    }
  },
  "time": "2026-01-22T10:00:00.123Z"
}
```

**HereCRM Mapping**:

```python
{
    "CustomerRef": {"value": customer.quickbooks_id},
    "TotalAmt": payment.amount,
    "TxnDate": payment.payment_date.strftime("%Y-%m-%d"),
    "Line": [
        {
            "Amount": payment.amount,
            "LinkedTxn": [
                {
                    "TxnId": invoice.quickbooks_id,
                    "TxnType": "Invoice"
                }
            ]
        }
    ]
}
```

---

## 6. Error Responses

### 6.1 Validation Error

**Status**: 400 Bad Request

**Response**:

```json
{
  "Fault": {
    "Error": [
      {
        "Message": "Required parameter Customer.DisplayName is missing",
        "Detail": "Required parameter Customer.DisplayName is missing",
        "code": "2020"
      }
    ],
    "type": "ValidationFault"
  },
  "time": "2026-01-21T20:00:00.123Z"
}
```

**Handling**: Log error, mark record as `failed`, notify business owner

---

### 6.2 Authentication Error

**Status**: 401 Unauthorized

**Response**:

```json
{
  "Fault": {
    "Error": [
      {
        "Message": "AuthenticationFailed",
        "Detail": "Authentication failed",
        "code": "003200"
      }
    ],
    "type": "AuthenticationFault"
  },
  "time": "2026-01-21T20:00:00.123Z"
}
```

**Handling**: Attempt token refresh, if fails notify business owner to reconnect

---

### 6.3 Rate Limit Error

**Status**: 429 Too Many Requests

**Response**:

```json
{
  "Fault": {
    "Error": [
      {
        "Message": "Rate limit exceeded",
        "Detail": "Too many requests",
        "code": "3200"
      }
    ],
    "type": "ThrottleFault"
  },
  "time": "2026-01-21T20:00:00.123Z"
}
```

**Handling**: Exponential backoff retry (1min, 2min, 4min)

---

### 6.4 Duplicate Error

**Status**: 400 Bad Request

**Response**:

```json
{
  "Fault": {
    "Error": [
      {
        "Message": "Duplicate Name Exists Error",
        "Detail": "The name supplied already exists",
        "code": "6240"
      }
    ],
    "type": "ValidationFault"
  },
  "time": "2026-01-21T20:00:00.123Z"
}
```

**Handling**: Query existing entity, update instead of create

---

## 7. Sync Dependency Order

To ensure referential integrity, entities must be synced in this order:

```
1. Customers
   ↓
2. Services (Items)
   ↓
3. Invoices (require Customer + Service references)
   ↓
4. Payments (require Invoice references)
```

**Implementation**:

```python
async def sync_business_to_quickbooks(business_id: int):
    # 1. Sync customers first
    await sync_customers(business_id)
    
    # 2. Sync services
    await sync_services(business_id)
    
    # 3. Sync invoices (now customers and services exist)
    await sync_invoices(business_id)
    
    # 4. Sync payments (now invoices exist)
    await sync_payments(business_id)
```

---

## 8. Retry Strategy

### 8.1 Retry Logic

```python
async def sync_with_retry(entity, sync_func, max_retries=3):
    """Retry sync operation with exponential backoff."""
    for attempt in range(max_retries):
        try:
            result = await sync_func(entity)
            return result
        except QuickBooksAPIError as e:
            if e.status_code == 429:  # Rate limit
                wait_time = 2 ** attempt * 60  # 1min, 2min, 4min
                await asyncio.sleep(wait_time)
            elif e.status_code in [500, 502, 503, 504]:  # Server errors
                wait_time = 2 ** attempt * 60
                await asyncio.sleep(wait_time)
            else:
                # Validation errors don't benefit from retry
                raise
    
    # All retries exhausted
    raise SyncFailedError(f"Failed after {max_retries} attempts")
```

### 8.2 Error Classification

| Error Type | Retry? | Notification |
|------------|--------|--------------|
| Validation (400) | No | Immediate (proactive) |
| Authentication (401) | Yes (after token refresh) | If refresh fails (proactive) |
| Rate Limit (429) | Yes (exponential backoff) | No (passive) |
| Server Error (5xx) | Yes (exponential backoff) | If all retries fail (proactive) |
| Network Error | Yes (exponential backoff) | If all retries fail (proactive) |

---

## 9. Testing Contracts

### 9.1 Mock Responses

Store mock QuickBooks API responses in `tests/fixtures/quickbooks_responses.json`:

```json
{
  "customer_create_success": {
    "Customer": {
      "Id": "58",
      "DisplayName": "Test Customer",
      "SyncToken": "0"
    }
  },
  "invoice_create_success": {
    "Invoice": {
      "Id": "145",
      "DocNumber": "1001",
      "TotalAmt": 100.00,
      "SyncToken": "0"
    }
  },
  "validation_error": {
    "Fault": {
      "Error": [{
        "Message": "Required parameter is missing",
        "code": "2020"
      }],
      "type": "ValidationFault"
    }
  }
}
```

### 9.2 Integration Tests

```python
@pytest.mark.asyncio
async def test_customer_sync_flow():
    """Test end-to-end customer sync."""
    # 1. Create customer in HereCRM
    customer = await create_customer(business_id=1, name="Test", street="123 Main", city="Springfield")
    
    # 2. Sync to QuickBooks (mocked)
    result = await sync_customer_to_quickbooks(customer)
    
    # 3. Verify QuickBooks ID stored
    assert customer.quickbooks_id == "58"
    assert customer.quickbooks_sync_status == "synced"
    
    # 4. Update customer
    customer.name = "Test Updated"
    await session.commit()
    
    # 5. Re-sync (should update, not create)
    result = await sync_customer_to_quickbooks(customer)
    
    # 6. Verify update operation used
    assert result.operation == "update"
```

---

## Summary

This contract specification defines:

- ✅ OAuth 2.0 authentication flow
- ✅ CRUD operations for Customer, Item, Invoice, Payment
- ✅ Data mappings from HereCRM entities to QuickBooks format
- ✅ Error handling and retry strategies
- ✅ Sync dependency order (Customers → Services → Invoices → Payments)
- ✅ Testing patterns with mock responses

All contracts follow QuickBooks Online API v3 standards and are compatible with the `python-quickbooks` SDK.
