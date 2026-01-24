# Quickstart: Google Calendar Integration

## Prerequisites

1. **Google Cloud Project**:
   - Create a project in Google Cloud Console.
   - Enable **Google Calendar API**.
   - Configure **OAuth Consent Screen** (Internal or Test users).
   - Create **OAuth 2.0 Client ID** (Web application).
   - Add Redirect URI: `http://localhost:8000/auth/google/callback` (for local dev).

2. **Environment Variables**:
   Add the following to your `.env`:

   ```bash
   GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="your-client-secret"
   GOOGLE_REDIRECT_URI="http://localhost:8000/auth/google/callback"
   ```

## Running Locally

1. **Start the App**:

   ```bash
   uv run fastapi dev src/main.py
   ```

2. **Connect Calendar**:
   - Open browser to `http://localhost:8000/auth/google/login`.
   - Complete the Google flow.
   - You should see a success message.

3. **Verify Sync**:
   - Send a message to the bot: "Schedule job for Alice at 2pm tomorrow".
   - Check the logs for `GoogleCalendarService`.
   - Check your Google Calendar for the event.

## Troubleshooting

- **Redirect URI Mismatch**: Ensure console matches `.env` exactly.
- **Token Scope Error**: Check if you re-authorized after changing scopes. Delete the user's credentials column to force re-auth.
