# Feature Specification: Business Workflow Defaults

**Feature**: Business Workflow Defaults
**Status**: Draft
**Mission**: software-dev

## 1. Overview

Different businesses operate with fundamentally different workflows. A window cleaning service in Ireland may never send formal invoices, while a US-based contractor sends invoices for every job. Some businesses quote on-the-spot, others send formal quotes. Some expect payment immediately, others invoice with net-30 terms.

This feature introduces configurable workflow defaults that allow each business to tailor the system to match their operational reality. These settings control UI visibility, default behaviors, and available functionality—ensuring the system adapts to the business, not the other way around.

## 2. Functional Requirements

### 2.1. Workflow Settings Configuration

Business owners must be able to configure the following workflow preferences:

#### 2.1.1. Invoicing Workflow

Controls how the business handles customer invoicing.

**Options**:

- **Never**: Business never sends invoices
  - Hide all invoice-related UI elements (tabs, buttons, menu items)
  - Disable invoice-related tool calls (e.g., `SendInvoiceTool`)
  - Invoice functionality is completely unavailable
  
- **Manual**: Business sends invoices when needed
  - Show invoice UI in menus and customer/job views
  - User must explicitly initiate invoice creation/sending
  - No automatic prompts or suggestions
  
- **Automatic**: Business regularly sends invoices
  - Show invoice UI
  - System prompts user to send invoices for completed jobs
  - Suggest invoice creation at appropriate workflow stages

**Default**: Manual

#### 2.1.2. Quoting Workflow

Controls how the business handles customer quotes.

**Options**:

- **Never**: Business quotes on-the-spot, no formal quotes
  - Hide all quote-related UI elements
  - Disable quote-related tool calls (e.g., `SendQuoteTool`)
  - Quote functionality is completely unavailable
  
- **Manual**: Business sends quotes when needed
  - Show quote UI in menus and customer views
  - User must explicitly initiate quote creation/sending
  - No automatic prompts
  
- **Automatic**: Business regularly sends quotes
  - Show quote UI
  - System prompts user to send quotes for new leads or requests
  - Suggest quote creation for appropriate customer interactions

**Default**: Manual

#### 2.1.3. Payment Timing

Controls default payment behavior and UI visibility for payment tracking.

**Options**:

- **Always paid on spot**: All jobs are paid immediately upon completion
  - Automatically set `Job.paid = true` for all new jobs
  - Hide payment tracking UI (payment status fields, "mark as paid" buttons)
  - Payment recording functionality is unavailable
  
- **Usually paid on spot**: Most jobs are paid immediately, but exceptions exist
  - Show payment tracking UI
  - Allow manual payment status updates
  - Default `Job.paid = false` (user can mark as paid)
  
- **Paid later**: Jobs are typically invoiced with payment terms
  - Show payment tracking UI
  - Default `Job.paid = false`
  - Payment status must be manually updated

**Default**: Usually paid on spot

#### 2.1.4. Tax Inclusion

Controls whether recorded prices include tax or if tax is added as a surcharge.

**Options**:

- **Prices include tax** (toggle: true/false)
  - `true`: Recorded job prices already include tax (tax-inclusive pricing)
  - `false`: Tax should be calculated and added as a surcharge on invoices

**Default**: true (prices include tax)

**Note**: Tax calculation logic is not implemented yet. This setting prepares the data model for future tax handling.

#### 2.1.5. Payment Terms on Invoices

Controls whether invoices include payment timing information (due dates, net terms).

**Options**:

- **Include payment terms** (toggle: true/false)
  - `true`: Invoices show due dates and payment terms (e.g., "Net 30")
  - `false`: Invoices do not include payment timing information

**Default**: false

#### 2.1.6. Automatic Reminders & Follow-ups

Controls whether the system sends automatic reminders for scheduled jobs and follow-ups.

**Options**:

- **Enable automatic reminders** (toggle: true/false)
  - `true`: System sends automatic reminders for upcoming appointments and follow-ups
  - `false`: No automatic reminders are sent

**Default**: false

### 2.2. Settings Storage

All workflow settings must be stored as **columns** on the `Business` model.

**Fields**:

- `workflow_invoicing` (`never` | `manual` | `automatic`)
- `workflow_quoting` (`never` | `manual` | `automatic`)
- `workflow_payment_timing` (`always_paid_on_spot` | `usually_paid_on_spot` | `paid_later`)
- `workflow_tax_inclusive` (boolean)
- `workflow_include_payment_terms` (boolean)
- `workflow_enable_reminders` (boolean)

### 2.3. Settings Management Interface

Business owners must be able to view and update workflow settings through a conversational interface.

**User Actions**:

- **View current settings**: "show workflow settings" or "show my settings"
  - System displays current workflow configuration in a readable format
  
- **Update settings**: "change workflow settings" or "update settings"
  - System presents each setting with current value and available options
  - User selects new values
  - System confirms changes and updates `Business.settings`

**Permissions**:

- Only users with `role = OWNER` can modify workflow settings
- All users can view their business's workflow settings

### 2.4. Application Behavior Based on Settings

The system must enforce workflow settings across all relevant components:

#### 2.4.1. UI Visibility

- **Invoicing = Never**: Hide invoice tabs, buttons, and menu items
- **Quoting = Never**: Hide quote tabs, buttons, and menu items
- **Payment Timing = Always paid on spot**: Hide payment status fields and "mark as paid" buttons

#### 2.4.2. Tool Availability

- **Invoicing = Never**: Disable `SendInvoiceTool` and related invoice tools
- **Quoting = Never**: Disable `SendQuoteTool` and related quote tools
- **Payment Timing = Always paid on spot**: Disable payment recording tools

#### 2.4.3. Default Values

- **Payment Timing = Always paid on spot**: Set `Job.paid = true` for all new jobs
- **Payment Timing = Usually paid on spot | Paid later**: Set `Job.paid = false` for new jobs

#### 2.4.4. System Prompts

- **Invoicing = Automatic**: Prompt user to send invoices for completed jobs
- **Quoting = Automatic**: Prompt user to send quotes for new leads/requests
- **Enable Reminders = true**: Send automatic reminders for scheduled appointments

### 2.5. Migration and Defaults

For existing businesses without workflow settings:

- Apply default values on first access to settings
- Do not modify existing job payment statuses
- Settings apply to new records created after configuration

## 3. Data Model Changes

### 3.1. Business Entity

 The `Business` entity will be updated with the following columns:

- `workflow_invoicing`
- `workflow_quoting`
- `workflow_payment_timing`
- `workflow_tax_inclusive`
- `workflow_include_payment_terms`
- `workflow_enable_reminders`

**Note**: Database migration is required to add these columns.

## 4. User Scenarios

### Scenario 1: Irish Window Cleaner (Never Invoices, Always Paid On Spot)

1. **Owner** sends: "change workflow settings"
2. **System** presents workflow options
3. **Owner** configures:
   - Invoicing: Never
   - Quoting: Never
   - Payment Timing: Always paid on spot
4. **System** confirms: "✔ Workflow settings updated. Invoices and quotes are now hidden. All jobs will be marked as paid automatically."
5. **Owner** adds a job: "Add: John, window cleaning, €50"
6. **System** creates job with `paid = true` automatically
7. **Owner** views job list: No invoice or payment status columns visible

### Scenario 2: US Contractor (Regular Invoicing, Net-30 Terms)

1. **Owner** sends: "update settings"
2. **Owner** configures:
   - Invoicing: Automatic
   - Quoting: Manual
   - Payment Timing: Paid later
   - Include Payment Terms: true
3. **Owner** completes a job
4. **System** prompts: "Job completed for Sarah Smith ($150). Would you like to send an invoice?"
5. **Owner** confirms
6. **System** generates invoice with payment terms and due date

### Scenario 3: Freelance Consultant (Quotes First, Then Invoices)

1. **Owner** configures:
   - Invoicing: Manual
   - Quoting: Automatic
   - Payment Timing: Paid later
2. **Owner** adds lead: "add lead: TechCorp, 555-0100"
3. **System** prompts: "New lead added. Would you like to send a quote?"
4. **Owner** sends quote
5. Lead accepts, job is created
6. **Owner** manually sends invoice after job completion

### Scenario 4: Viewing Current Settings

1. **User** (Employee) sends: "show workflow settings"
2. **System** replies:

   ```
   📋 Workflow Settings:
   • Invoicing: Manual
   • Quoting: Never
   • Payment: Usually paid on spot
   • Tax: Prices include tax
   • Payment terms on invoices: No
   • Automatic reminders: Enabled
   ```

## 5. Success Criteria

- Business owners can configure all six workflow settings through a conversational interface
- Settings are persisted in `Business.settings` JSON field
- UI elements (tabs, buttons, menus) are hidden when corresponding workflow is set to "Never"
- Tool calls for disabled workflows return appropriate error messages
- Jobs created with "Always paid on spot" setting have `paid = true` by default
- System prompts appear for "Automatic" workflows at appropriate stages
- Settings can be viewed by all users but modified only by owners
- Existing businesses receive sensible defaults without breaking existing data

## 6. Assumptions & Risks

- **UI Framework**: Assumes UI components can conditionally render based on business settings
- **Tool Execution**: Assumes tool executor can check business settings before executing tools
- **Tax Calculation**: Tax calculation logic is not implemented; this feature only adds the toggle for future use
- **Reminder System**: Assumes reminder/scheduling infrastructure exists or will be implemented separately
- **Settings Validation**: Invalid settings values should be rejected with clear error messages
- **Performance**: Reading settings from JSON field on every request should not impact performance significantly (settings can be cached per business)
