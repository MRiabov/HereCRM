# WhatsApp App Review Submission Instructions

This guide outlines the steps required to submit **HereCRM** for App Review on the Meta Developer Portal to enable official WhatsApp Business Platform messaging.

## 1. Preparation Checklist

Before starting the submission, ensure you have the following:

* **Business Verification**: A verified Meta Business Account (requires business license, utility bill, or tax documents).
* **Privacy Policy URL**: A public URL housing your app's privacy policy.
* **Website URL**: Your business website.
* **App Icon**: A 1024x1024 PNG/JPG icon.
* **Terms of Service**: Links to your terms.

## 2. Meta Developer Portal Setup

1. Go to [Meta for Developers](https://developers.facebook.com/).
2. Create a new App (Type: **Business**).
3. Add the **WhatsApp** product to your app.
4. Connect your **WhatsApp Business Account (WABA)**.

## 3. Required Permissions

You must request the following permissions during the App Review process:

| Permission | Reason for Request |
| :--- | :--- |
| `whatsapp_business_messaging` | **Core Requirement**: Allows the app to send and receive messages on behalf of the business. Used for the AI CRM agent to process user commands and send confirmations. |
| `whatsapp_business_management` | **Required for Templates**: Allows the app to create, delete, and manage message templates (including marketing templates) for the business. |

---

## 4. Technical Provider Verification

Meta requires additional verification if your app acts as a **Technical Provider** for other businesses.

1. In the Meta App Dashboard, go to **App Review** > **My Permissions and Features**.
2. Find **Tech Provider Role** (if applicable) and initiate verification.
3. **Use Case**: State that HereCRM serves as the technical interface for small businesses to manage their WhatsApp communications and marketing workflows.
4. Ensure your **Business Verification** is complete, as Tech Provider status depends on it.

---

## 5. Marketing Templates

If your app allows users to create marketing templates:

1. **Permission**: Ensure `whatsapp_business_management` is requested in your review.
2. **Demonstration**: In your screencast, you must show the UI where a user creates a template (e.g., "Season's Greeting" or "Special Offer").
3. **Approval Flow**: Explain how templates are submitted to Meta for approval via your interface.

---

## 6. App Review Submission Details

When filling out the App Review form, use the following templates to speed up approval:

### App Description
>
> HereCRM is an AI-powered CRM designed for small businesses and field technicians. It allows users to manage jobs, customers, and schedules directly through WhatsApp using natural language processing. The app also serves as a marketing platform, enabling businesses to create and send approved message templates to their customer base for promotions and service updates.

### Reviewer Instructions (How to Test)
>
> 1. Navigate to the WhatsApp Business number linked to the app.
> 2. Send a message: `Add Job: Test Appointment for John, 123 Main St, $50`.
> 3. The AI agent will parse the request, create a test record in the CRM, and reply with a confirmation.
> 4. **Template Creation**: Navigate to the 'Marketing' section in the CRM dashboard and create a new template titled `Test Promotion`. Verify it appears in the 'Submitted' status.
> 5. Test the undo functionality by replying `undo` to the AI agent.

### Screencast Requirements
>
> [!IMPORTANT]
> You MUST upload a video (MP4) showing the end-to-end flow.

* **Show the user sending a command** (e.g., adding a job).
* **Show the AI agent responding** with a structured confirmation.
* **Template Workflow**: Demonstrate creating a marketing template in the CRM and submitting it.
* **Show the dashboard/database** (if applicable) reflecting the changes.

---

## 7. Best Practices & Pitfalls

* **AI Disclaimer**: If the agent is fully automated, ensure you mention that it is a tool for business management, not a generative AI "chatbot" for general conversation.
* **Opt-in Compliance**: Ensure your screencast or description mentions how customers opt-in to receive messages (e.g., "Customers opt-in via our website or by initiating the first message").
* **Template Status**: If you are using Message Templates (for notifications after 24 hours), ensure they are already submitted and "Approved" before the final App Review.

---

## 8. Next Steps

1. **Submit for Review**: Start with `whatsapp_business_messaging`.
2. **Wait for Approval**: Usually takes 24–72 hours.
3. **Go Live**: Once approved, switch the app mode from "Development" to "Live".
