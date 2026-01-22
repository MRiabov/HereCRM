# Quickstart: Business Workflow Defaults

Path: kitty-specs/019-business-workflow-defaults/quickstart.md

## Overview

This feature allows you to customize how HereCRM behaves for your business.

## How to use

### 1. View Current Settings

Send: `"show workflow settings"` or `"show my settings"`
The AI will respond with your current configuration.

### 2. Update Settings

Send: `"update settings"` or `"change workflow settings"`

1. The AI will ask which setting you'd like to change.
2. Provide the new value (e.g., `"Never send invoices"` or `"Set payment timing to Always paid on spot"`).
3. The AI will confirm the update.

### 3. Workflow Impacts

- **Never Invoicing**: Invoice buttons and help commands will be hidden.
- **Always Paid on Spot**: Jobs will be marked as paid automatically; payment tracking fields will be hidden.
- **Automatic Quoting**: The AI will proactively ask if you want to send a quote when you add a new lead.
