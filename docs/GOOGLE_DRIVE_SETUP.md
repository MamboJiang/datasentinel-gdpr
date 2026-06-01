# Google Drive Source Setup

## Purpose

Google Drive source input uses Google Picker in the browser and Google Drive API reads on the backend. The app stores selected item metadata only. One-off Picker access tokens are not stored. When a user connects Google Drive in Account settings, the local API stores a server-side refresh token for that signed-in account so Drive scans can survive browser refresh. Raw source file bodies are not stored.

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
9. Add the authorized redirect URI for Drive account binding:
   - `https://founder-force.uk/api/integrations/google-drive/bind/callback`
10. On the OAuth consent screen, add Drive scopes:
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

`GOOGLE_CLIENT_SECRET` is server-only. `/api/integrations/google-drive/picker-config` and `/api/integrations/google-drive/binding` must never return it. Binding, disconnect, and scan routes must never return provider access tokens or refresh tokens. In prelaunch, Picker config requires the first-party session cookie when `LAWDIT_AUTH_REQUIRED=true`; Drive binding routes always require a first-party session.

## Validation

After restarting the API server, sign in to the app and open the Add Source dialog. The Google Drive option should show as configured. For a direct API check, call the route with a valid `lawdit_session` cookie:

```bash
curl -s --cookie "lawdit_session=<session id>" \
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

To validate the personal binding route, open Account settings and connect Google Drive. Then call:

```bash
curl -s --cookie "lawdit_session=<session id>" \
  https://founder-force.uk/api/integrations/google-drive/binding
```

The response should show `connected: true`, safe Google profile fields, scopes, and timestamps. It must not include access tokens or refresh tokens.

## Operational Boundary

- `drive.file` supports files selected through the Picker.
- `drive.readonly` is required when the user selects a folder and lawdit recursively lists descendant files.
- One-off Picker access tokens are requested in the browser and sent only with the scan-start request.
- Account settings Drive binding requests offline access through the backend; refresh tokens are stored server-side in the local account binding store and used only to mint short-lived scan access tokens.
- Disconnecting the binding removes the local binding and attempts provider-token revocation. It does not delete lawdit source registrations or Google Drive files.
- Raw source content is read during scan execution only; public payloads expose redacted evidence, findings, metrics, warnings, and audit events.
