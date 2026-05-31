# Google Drive Source Setup

## Purpose

Google Drive source input uses Google Picker in the browser and Google Drive API reads on the backend. The app stores selected item metadata only. It does not store Google Drive access tokens, refresh tokens, or raw source file bodies.

## Required Google Cloud Setup

Use the same Google Cloud project that has Google Drive API and Google Picker API enabled.

1. Open Google Cloud Console > APIs & Services > Credentials.
2. Create an API key for Google Picker.
3. Restrict the API key:
   - Application restriction: HTTP referrers.
   - Website restrictions:
     - `https://founder-force.uk/*`
     - `http://localhost:*/*` for local testing if needed.
     - `http://127.0.0.1:*/*` for local testing if needed.
   - API restriction: Google Picker API.
4. Copy the API key into host env as `GOOGLE_PICKER_API_KEY`.
5. Copy the numeric Google Cloud project number into host env as `GOOGLE_CLOUD_PROJECT_NUMBER`.
6. Open the existing Google OAuth web client.
7. Add authorized JavaScript origins:
   - `https://founder-force.uk`
   - Local dev origins only when needed, such as `http://localhost:5173` or `http://127.0.0.1:5173`.
8. Keep authorized redirect URIs for account sign-in:
   - `https://founder-force.uk/api/auth/callback/google`
9. On the OAuth consent screen, add Drive scopes:
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/drive.readonly`

## Host Environment

Set these values in ignored host environment configuration such as `.env.local` or the server service manager:

```bash
GOOGLE_CLIENT_ID=<google oauth web client id>
GOOGLE_CLIENT_SECRET=<google oauth web client secret>
GOOGLE_PICKER_API_KEY=<restricted google picker api key>
GOOGLE_CLOUD_PROJECT_NUMBER=<numeric google cloud project number>
```

`GOOGLE_CLIENT_SECRET` is server-only. `/api/integrations/google-drive/picker-config` must never return it. In prelaunch, this route also requires the first-party session cookie when `DATASENTINEL_AUTH_REQUIRED=true`.

## Validation

After restarting the API server, sign in to the app and open the Add Source dialog. The Google Drive option should show as configured. For a direct API check, call the route with a valid `datasentinel_session` cookie:

```bash
curl -s --cookie "datasentinel_session=<session id>" \
  https://founder-force.uk/api/integrations/google-drive/picker-config
```

Expected state when fully configured:

```json
{
  "data": {
    "configured": true,
    "clientId": "<public google oauth client id>",
    "apiKey": "<restricted picker api key>",
    "appId": "<google cloud project number>",
    "missing": []
  }
}
```

The response must not include `GOOGLE_CLIENT_SECRET`, GitHub credentials, provider access tokens, refresh tokens, or raw source content.

## Operational Boundary

- `drive.file` supports files selected through the Picker.
- `drive.readonly` is required when the user selects a folder and DataSentinel recursively lists descendant files.
- Access tokens are requested in the browser and sent only with the scan-start request.
- Refresh tokens are not requested or stored.
- Raw source content is read during scan execution only; public payloads expose redacted evidence, findings, metrics, warnings, and audit events.
