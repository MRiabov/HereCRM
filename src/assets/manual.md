# HereCRM Product Manual

Welcome to HereCRM! This manual explains how to use our WhatsApp-based CRM.

## Core Features

### 1. Adding Leads

To add a new lead without an immediate job, use phrases like:

- "Add new lead: Mike, 089999999"
- "Register client: Sarah in Cork"

### 2. Managing Jobs

You can add jobs for past work or schedule future jobs:

- **Add Past Job**: "Add job for John, cleaned windows for $50 done"
- **Schedule Future Job**: "Schedule Mary for next Tuesday at 2pm for window cleaning"

### 3. Searching

Find your data quickly:

- "Search for John"
- "Find jobs in Dublin"
- "Show me pending jobs"

### 4. Sales Pipeline

Track your business health:

- "How is the pipeline looking?"
- "Show me funnel status"

### 5. Settings

Customize your experience:

- "Settings" or "Config" to enter settings mode.
- Change default city, language, or services.

### 6. Workflow Settings (Owner Only)

Configure how the CRM handles automation and billing. Only users with the **OWNER** role can change these:

- **Invoicing Workflow**: Set to `never`, `manual`, or `automatic`. Controls when and if invoices are sent.
- **Quoting Workflow**: Set to `never`, `manual`, or `automatic`. Controls when and if quotes are sent.
- **Payment Timing**: Options are `always_paid_on_spot`, `usually_paid_on_spot`, or `paid_later`.
- **Tax Inclusive**: Whether your prices already include tax.
- **Include Payment Terms**: Whether to show Net terms/due dates on documents.
- **Enable Reminders**: Toggle automatic customer follow-ups.

Use phrases like:

- "Show my workflow settings"
- "Set invoicing to automatic"
- "Update payment timing to always paid on spot"

## QuickBooks Integration

Connect HereCRM to your QuickBooks Online account to automatically sync your customers, services, invoices, and payments.

### 1. How to Connect

To start the integration, simply say:

- "Connect QuickBooks"

You will receive a link to authorize HereCRM to access your QuickBooks account. Once authorized, the integration will be active.

### 2. What is Synced

The integration performs a **one-way sync** from HereCRM to QuickBooks for the following entities:

- **Customers**: Synced when created or updated.
- **Services**: Your service catalog items are synced as QuickBooks Items.
- **Invoices**: Sent to QuickBooks once they are created in HereCRM.
- **Payments**: Recorded in QuickBooks and linked to their respective invoices.

### 3. Sync Frequency

Data is automatically synchronized **HOURLY**. If you need to push changes immediately, you can say:

- "Sync QuickBooks now"

### 4. Viewing Status and Errors

To check the health of your integration, use:

- "QuickBooks status"

This will show you the last sync time and any records that failed to sync.

### 5. Common Issues

- **Address Required**: QuickBooks requires at least a street and city for customers. If these are missing, the sync will fail for that customer and their invoices.
- **Disconnected Account**: If you change your QuickBooks password or revoke access, you may need to reconnect by saying "Connect QuickBooks" again.
- **Duplicates**: HereCRM tries to match existing customers and services by name to avoid duplicates, but it is recommended to keep names consistent across both systems.

To stop the integration, say:

- "Disconnect QuickBooks"

## Troubleshooting Tips

- **Missing Information**: If I ask for a customer name, it's because I couldn't find one in your message.
- **Ambiguous Queries**: If you have multiple customers with the same name, try using their phone number or address.
- **Undo**: If you made a mistake, just say "Undo" to revert the last action.

## Asking for Help

You can always ask me:

- "How do I add a lead?"
- "What can I do?"
- "Why did my last prompt fail?"
- "What can I do to use you better?"
