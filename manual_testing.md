Based on the comprehensive specifications provided, here is a categorized list of high-value manual testing scenarios. These are designed to stress-test the **LLM parsing logic**, **multi-tenant isolation**, **edge cases**, and **cross-feature integrations** where bugs typically hide.

---

## 1. Onboarding & Multi-Tenancy

* **The "Cold Start":** Send "Add John 085123123 fix faucet $50" from a brand-new phone number. Verify it creates the Business, the User, the Customer, and the Job in one go.
* **Tenant Leakage:** As User A (Business 1), try to "Show Job #101" (where #101 belongs to Business 2). Verify the system returns "Job not found" rather than the data.
* **Duplicate Onboarding:** Send a message from a number already assigned as an "Employee" in Business A. Verify the system doesn't try to create a new "Business" for them.

## 2. Conversational Billing & Addons (Spec 010)

* **The "Add Seats" Error:** Send "I want to add 5 seats." Verify the system calculates the total and provides a Stripe link.
* **The "Gated Tool" Test:** As a user without the "Campaign Messaging" addon, send "Send a broadcast to all customers." Verify the system blocks the tool and suggests buying the addon.
* **Overage Awareness:** Ask "What is my billing status?" when you have sent 1,050 messages. Verify it correctly identifies the 50-message overage and the cost (e.g., $1.00).

## 3. Advanced Search & Geo-Fencing (Spec 005)

* **The "Detailed" Keyword:** Send "Find John" vs. "Find John detailed." Verify the latter includes notes, line items, and job history.
* **Proximity Search:** Send "Find customers within 1km of [Your Current Address]." Move the radius to 100m and verify the results filter correctly.
* **Ambiguous Entity:** Send "Show me High Street." Verify the system returns both the Customer living there and the Jobs scheduled there.

## 4. Line Items & Catalog Inference (Spec 004)

* **The "Math" Test:** Create a service "Window Cleaning" with a default price of $5. Send "Add job for Sarah, 12 windows for $60." Verify it infers Qty: 12, Unit Price: $5.
* **The "Rounding" Bug:** Send "Add job for Mike, 3 hours of cleaning for $50." Verify the unit price handles the repeating decimal (~$16.67) without breaking the $50 total.
* **Catalog Protection:** While in normal chat, try to say "Change the price of Window Cleaning to $10." Verify the system directs you to the "Settings" menu rather than editing the catalog ad-hoc.

## 5. Pipeline & Automated Messaging (Spec 002, 003)

* **State Machine Progression:** Add a lead. Verify status is "Not Contacted." Add a job. Verify status is "Converted Once." Add a second job. Verify status is "Converted Recurrent."
* **Manual Terminal State:** Send "Mark John as Lost." Then send "Add job for John $50." Verify the status moves back to "Converted Once" (Activity should override "Lost").

## 6. Employee Management & Guided Workflow (Spec 011, 016)

* **The "Assignment" Command:** Send "Assign #101, #102, and #103 to Dave." Verify all three update.
* **The "Done" Trigger:** As an employee, send "Done #101." Verify the system immediately pushes the address and Map link for Job #102.
* **Clock-In Errors:** Send "Start Job #105" before sending "Check in." Verify if the system requires a shift start before a job start (based on your payroll preferences).

## 7. Professional Invoices & Quotes (Spec 006, 012)

* **The "Duplicate" Guard:** Send "Send invoice to Sarah." Wait for confirmation. Send "Send invoice to Sarah" again. Verify the system warns: "Invoice already exists. Resend?"
* **Quote-to-Job Conversion:** Send a quote. As the *customer* (using a different phone), reply "Confirm." Verify the Business Owner gets a notification and the Quote status turns into a Job.

## 8. RBAC & Permissions (Spec 017)

* **The "Sneaky Employee":** As an Employee, send "Export all customer data to CSV." Verify the response: "It seems you are trying to export customers. Sorry, you don't have permission for that."
* **The "Manager" Balance:** As a Manager, try to "Add 2 seats to our plan." Verify denial. Then try to "Optimize today's route." Verify success.

## 9. Help & Troubleshooting (Spec 008)

* **The "Why" Query:** Send a nonsense message like "Glitter banana 50." After it fails, ask "Why did my last prompt fail?" Verify it explains that it couldn't find a name or price.
* **Manual RAG:** Ask "How do I add a lead?" Verify the answer matches the exact steps in your `manual.md`.

## 10. External Integrations (Spec 015, 020)

* **QuickBooks Sync:** Record a payment in the CRM. Wait for the hourly sync (or trigger manual). Check QuickBooks to ensure the payment is linked to the correct invoice.
* **CAPI Privacy:** Trigger a "Job Booked" event. Check logs (if possible) to ensure the phone/email sent to Meta was hashed (SHA-256) and not sent in plain text.

---

### Suggested Next Step

Would you like me to generate a **Python test script** or a **Postman collection** to automate the non-conversational parts (like the Inbound Lead API or the Webhook signatures)?
