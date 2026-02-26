# HereCRM: The Text-First AI CRM

**HereCRM** is a conversational CRM designed for service-based businesses that operate on the move. Instead of forcing users into complex dashboards and rigid forms, HereCRM lives entirely within messaging apps like **WhatsApp** and **SMS**, allowing you to manage your entire business—from lead to invoice—using natural language.

---

## 🌟 The Vision: A CRM without the "Work"

Most CRMs fail because they require too much manual data entry. HereCRM replaces forms with an **LLM-powered engine** that understands how you talk. Whether you're adding a new job, scheduling a technician, or generating an invoice, you just text it.

### 💬 Conversational Business Core

* **Zero-Form Entry:** Create customers and jobs by texting: *"Add John Doe, fix leaking sink at 123 High St tomorrow at 10am."*
* **Lead Intelligence:** Automatically track leads and requests. The system parses line items and costs directly from your chat history.
* **Guided Workflows:** Employees receive proactive prompts: *"Job finished? Upload a photo and I'll send the invoice to the customer."*

### 🚀 Automated Operations

* **Auto-Pipeline:** Customers move through stages (Not Contacted → Contacted → Converted) based on their actual activity, giving you an instant view of your sales health.
* **Smart Invoicing & Quotes:** Generate professional PDFs and send them via WhatsApp with a single command. Includes built-in tax calculation and Stripe/PayPal payment links.
* **Intelligent Assistant:** A built-in "Product Assistant" that knows your specific business data and can answer questions like *"Why did the last invoice fail?"* or *"Show me jobs near my current location."*

---

## 🏗️ Architecture & Infrastructure

HereCRM is built on a modern, event-driven stack designed for high reliability and data isolation.

### 🛡️ Secure Multi-Tenancy

The system is built from the ground up for **strict data isolation**. Every piece of data—jobs, customer lists, and financial records—is cryptographically bound to a unique `Business ID`. Even within a business, **Tool-Level RBAC** (Role-Based Access Control) ensures technicians can only see the jobs they are assigned to, while admins retain full oversight.

### 🧠 The LLM Brain

We use an advanced **Tool-Calling Architecture**. When a message arrives, our orchestration layer:

1. Analyzes intent using Large Language Models.
2. Maps the request to specific internal tools (Search, Job Creation, Invoicing).
3. Validates security constraints before executing any database change.

### 🛰️ Distributed Infrastructure

* **Messaging Ingress:** Integrated via webhooks with WhatsApp (Meta API), Twilio (SMS), and Postmark (Email).
* **Async Processing:** A robust event bus handles long-running tasks like PDF generation, geocoding addresses, and syncing with external accounting software (QuickBooks).
* **Geospatial Engine:** All customer addresses are automatically geocoded, enabling "Jobs near me" searches and optimized routing for mobile teams.

---

## 📊 Business Intelligence & Integration

* **Accounting Sync:** Real-time synchronization with QuickBooks and usage-based billing tracking.
* **Data Portability:** Natural language "Export" commands allow you to request CSVs of your data via chat, while a dedicated dashboard supports bulk CSV/Excel imports.
* **Live Visibility:** Live location tracking for field technicians with real-time ETA updates sent automatically to customers.

---

## 🛠 Tech Stack Summary

* **Backend:** Python / FastAPI
* **Database:** PostgreSQL (with spatial indexing)
* **Auth:** Clerk (PWA) + Internal WhatsApp session management
* **LLM:** OpenAI/Anthropic via a custom tool-calling framework
* **Deployment:** Containerized (Docker) with support for Railway/AWS/Local

---

*Developed based on the feature specifications in `kitty-specs/`.*
