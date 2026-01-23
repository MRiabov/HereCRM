# HereCRM Product Manual (Detailed LLM Reference)

This manual defines the features, extraction logic, and operational states of HereCRM. It is optimized for LLM retrieval (RAG) to provide precise guidance to users.

---

## 🟢 STATE: MAIN CRM (Core Daily Operations)

These actions are performed from the primary chat interface and represent 90% of user interaction.

### 1. Customer & Lead Management

- **Concepts**:
  - **Lead**: A customer with NO associated jobs.
  - **Client/Customer**: A record with or without jobs.
- **Extraction Logic**: When adding a customer, the system extracts:
  - `Name` (Required)
  - `Phone` (Required for communication)
  - `Address` (Parsed into Street, City, Country. Defaults to Business City/Country if missing).
  - `Description` (Any extra notes).
- **Commands**:
  - "Add lead John Smith, 0851234567, 12 High St, Dublin"
  - "Register client: Sarah in Cork"

### 2. Job & Request Management

- **Extraction**: The system extracts `Description`, `Location`, `Value` (Price), and `Scheduled Time`.
- **Inference**: If a service matches the **Service Catalog**, the system infers missing values ($Total / Default Price = Quantity).
- **Requests**: If "add request:" is used, it stores the intent without creating a formal job yet.
- **Commands**:
  - "Add John, fix leaky faucet, 50eur" (Creates customer + job)
  - "Schedule Mary for next Tuesday at 2pm for window cleaning"
  - "Add request: John wants 12 windows cleaned"

### 3. Expense Tracking (NEW)

- **Role**: Expenses are recorded from the main screen for quick entry.
- **Linking**: Expenses can be general (Business overhead) or linked to a specific `Job` or `Line Item` to calculate job profitability.
- **Commands**:
  - "Add expense: Truck Diesel $80"
  - "Link $50 expense to Sarah's window cleaning job"

### 4. Unified Search & Proximity

- **Unified Search**: LLM identifies if the user is looking for a Job, Customer, or Request.
- **Keywords**:
  - `detailed`: Returns full record including history and line items (e.g., "Show Sarah detailed").
  - `near [Location]`: Performs a Geo-search (requires OSM geocoding).
- **Proximity**: "Search within 500m of High St" or "Jobs near me".

---

## 🟠 STATE: SALES & COMMUNICATION

Logic for funnel movement and automated customer outreach.

### 1. Sales Pipeline Logic

- **Automatic Transitions**:
  - New Customer (No jobs) -> `Not Contacted`.
  - First Message/Reply -> `Contacted`.
  - 1st Job Created -> `Converted Once`.
  - 2nd+ Job Created -> `Converted Recurrent`.
- **Manual Overrides**: "Mark John as Lost" or "Move Sarah to Not Interested".

### 2. Messaging & Reminders

- **Triggers**:
  - `On My Way`: Triggered via manual command.
  - `Job Booked/Scheduled`: Automated confirmation sent to customer.
- **Settings**: Owners can set messaging to `never`, `manual`, or `automatic`.

### 3. Professional Quotes

- **Purpose**: Generates a PDF quote for approval before a job is 'Booked'.
- **Command**: "Send quote to John for $150".

---

## 💰 STATE: FINANCIALS & DOCUMENTS

Handles professional document generation and payment processing.

### 1. Professional Invoices (PDF)

- **Selection**: By default, it finds the *last completed job* that hasn't been invoiced.
- **Safety**: The system checks for existing `Invoice` records to prevent duplicates.
- **Command**: "Send invoice to Sarah".

### 2. Stripe Payment Integration

- **Onboarding**: "Setup payments" generates a Stripe Connect link.
- **Payment Links**: Every PDF invoice contains a unique "Pay Now" link.
- **Auto-Update**: Once paid, the `Invoice` and `Job` status automatically move to `PAID`.

### 3. Service Catalog (Settings)

- **Management**: Managed ONLY via the **Settings** menu.
- **Purpose**: Standardizes `Name`, `Default Price`, and `Description`.
- **Logic**: Use "Update settings" to add or modify services.

---

## 🏦 STATE: ACCOUNTING (Back-Office)

Specialized tools for financial health and payroll, distinct from daily field CRM work.

### 1. QuickBooks Integration

- **Function**: One-way sync (HereCRM -> QuickBooks) occurring **Hourly**.
- **Sync Entities**: Customers, Services, Invoices, and Payments.
- **Constraints**: Duplicate names in QB will be updated, not duplicated.
- **Commands**: "QuickBooks status", "Sync QuickBooks now".

### 2. Payroll & Employee Ledger

- **Wage Models**:
  - `Commission %`: Calculated on job revenue.
  - `Hourly (Job)`: Time between "Start" and "Done".
  - `Hourly (Shift)`: Time between "Check In" and "Check Out".
  - `Fixed Daily`: Flat rate per day worked.
- **Workflow**: Employees use "Check In", "Start #123", and "Check Out".

---

## 🛠️ ADMINISTRATION & PERMISSIONS

### 1. Tool-Level RBAC

- **OWNER**: Full access to all tools including Billing.
- **MANAGER**: Access to all operations EXCEPT Billing/Subscription.
- **EMPLOYEE**: Restricted to Job/Customer actions only. No data exports.

### 2. Data Management (Bulk)

- **Import**: Atomic (all or nothing) CSV/Excel/JSON import with LLM-powered header mapping.
- **Export**: "Export all Dublin jobs as CSV".

### 3. Workflow Configuration

- **Settings Keys**: `Invoicing Workflow`, `Quoting Workflow`, `Payment Timing` (e.g., "Paid on spot"), `Tax Inclusive`.
- **Access**: "Show workflow settings".

---

## 🤖 ASSISTANT TIPS (LLM Context)

- **History**: Use the last 5 turns to explain failures (e.g., "You didn't provide a price").
- **Undo**: Any mutation (Add/Update) can be reverted by saying "Undo".
- **Refinement**: Use "Edit Last" to fix the previous command's data.
