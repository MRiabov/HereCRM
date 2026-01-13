# Data Model: WhatsApp CRM

## Entities

### User
- Phone Number (ID)
- Name
- Role/Permissions

### Job
- ID
- Description
- Status
- Customer Link
- Timestamp

### Customer
- ID
- Name
- Phone
- Details

### Request
- ID
- Content
- Status

## Relationships
- User creates Jobs/Requests
- Job linked to Customer
