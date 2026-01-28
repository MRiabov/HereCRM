# LLM Context Variables Guide

This document lists all variables that influence the LLM's decision-making and tool-calling behavior in HereCRM. These should be considered when creating validation datasets or test cases.

## Core Input Variables

These are directly passed to the `LLMParser.parse` method.

| Variable | Source | Description |
| :--- | :--- | :--- |
| `text` | User Message | The raw input from the user (WhatsApp, SMS, or PWA Chat). |
| `system_time` | Backend | The current server time (ISO format). Crucial for resolving relative times like "tomorrow" or "next week". |
| `service_catalog` | `Service` Model | A markdown list of available services (ID, Name, Price). Used for fuzzy matching and price inference. |
| `channel_name` | `MessageType` | The medium of communication (e.g., `WHATSAPP`, `SMS`, `PWA_CHAT`). Influences brevity requirements. |
| `feedback` | `LLMParser` | Error messages from previous failed attempts or geocoding rejections, used for self-correction. |

## User Context (`user_context`)

Passed as a dictionary to provide agentic "situational awareness".

| Field | Source | Description |
| :--- | :--- | :--- |
| `role` | `User.role` | `OWNER`, `MANAGER`, or `EMPLOYEE`. Used to determine persona and permissions. |
| `name` | `User.name` | The name of the user interacting with the bot. |
| `business_id` | `User.business_id` | Partitioning ID for the business. |
| `active_addons` | `BusinessSettings` | List of enabled features (e.g., `campaigns`, `manage_employees`). |
| `phone_number` | `User.phone_number` | The user's own phone number. |

## Business & Workflow Settings

These settings are crucial for the LLM to know how to calculate totals and when to trigger specific workflows.

| Setting Key | Description | LLM Impact |
| :--- | :--- | :--- |
| `tax_inclusive` | `true`/`false` | Whether prices include tax. Affects the `price` field in `AddJobTool`. |
| `tax_mode` | `"Tax Added"` / `"Tax Inclusive"` | Specific tax calculation strategy. |
| `workflow_invoicing` | `"never"`, `"manual"`, `"automatic"` | Determines if `SendInvoiceTool` should be suggested or blocked. |
| `workflow_quoting` | `"never"`, `"manual"`, `"automatic"` | Determines if `CreateQuoteTool` logic should be suggested. |
| `default_city` | User's base city | Used by `GeocodingService` to disambiguate street names. |
| `default_country` | User's base country | Used by `GeocodingService` to disambiguate locations. |
| `geocoding_safeguard` | `true`/`false` | If enabled, rejects locations too far from the `default_city`. |

## Tool-Specific Schema (Line Items)

The `AddJobTool` and `CreateQuoteTool` accept a list of `LineItemInfo`.

| Field | Description | AI Rule |
| :--- | :--- | :--- |
| `description` | Full name of the service | **DO NOT SHORTEN**. Use catalog name if matched. |
| `service_id` | Database ID of the service | Set if matched with catalog. |
| `quantity` | Number of units | Inferred from text or 1.0 default. |
| `unit_price` | Price per single unit | Inferred from catalog or text. |
| `total_price` | `quantity * unit_price` | **Backend calculated**. LLM usually leaves this NULL if it expects the backend to infer it. |

> [!IMPORTANT]
> To prevent line item shortening (e.g., "Exterior Window Cleaning" -> "windows"), the validation dataset MUST provide the `service_catalog` context and assert that the `description` in `line_items` matches the catalog's canonical name.
