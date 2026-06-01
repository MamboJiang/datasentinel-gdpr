# Google Drive Bound Picker Token

## Problem

After a user connects a personal Google Drive binding, Add Source still starts the browser-side Google authorization flow before opening Picker. That sends the user to a Google login or consent surface even though the same lawdit account already has a server-side Drive binding.

## Research Basis

- Google Picker uses `PickerBuilder.setOAuthToken(token)` to authenticate the current user.
- The official Google Picker web sample states that `setOAuthToken` determines which Google Account Picker displays, and that an existing token can skip the account chooser/consent prompt for an existing session.

## Options

| Option | Benefit | Cost | Decision |
| --- | --- | --- | --- |
| Keep browser-only Picker OAuth | No new API | Bound users still see a login/consent flow | Rejected |
| Store Picker tokens in source records | Fast repeated selection | Persists provider access tokens in source state | Rejected |
| Mint a short-lived Picker token from the account binding | Opens Picker for the bound account without persisting tokens | Browser receives a short-lived access token for Picker use | Accepted |

## State Machine

States:

- `unbound`
- `bound`
- `picker_token_refreshing`
- `picker_open`
- `picker_failed`

Events:

- `choose_drive_files_clicked` or `choose_drive_folder_clicked`
- `bound_picker_token_requested`
- `bound_picker_token_returned`
- `bound_picker_token_rejected`
- `picker_selection_picked`
- `picker_cancelled`

Transitions:

- `bound -> picker_token_refreshing -> picker_open`: backend refreshes a short-lived access token from the server-side binding and the frontend passes it to Picker.
- `unbound -> picker_open`: frontend uses the existing browser OAuth Picker path.
- `picker_token_refreshing -> picker_failed`: binding is missing, expired, unconfigured, or refresh fails.
- `picker_open -> picker_selection_picked`: source metadata and the short-lived runtime token stay in browser memory only.
- `picker_open -> unbound|bound`: cancelled selection does not create a source.

Side effects:

- The backend returns a short-lived access token only from `POST /api/integrations/google-drive/picker-token`.
- The frontend uses that token only for `PickerBuilder.setOAuthToken` and the current runtime source authorization.
- Source records, workflow documents, findings, metrics, audit events, logs, and Account binding status payloads do not store or return refresh tokens.

Failure paths:

- Missing first-party session returns authentication required.
- Missing binding returns a command rejection.
- Refresh failure returns a provider-refresh problem and leaves existing source registrations untouched.

Rollback path:

- Remove the Picker token endpoint and the frontend bound-token lookup.
- Existing browser Picker OAuth and server-side scan binding behavior continue to work.

## Impact Surface

- Backend Google Drive binding service and routing.
- Frontend Google Picker launch path in Add Source.
- API contract and OpenAPI schemas.
- Security notes around browser-visible short-lived Picker access tokens.

## Primitive Acceptance

- With a connected Google Drive binding, Add Source `Choose files` and `Choose folder` request a bound Picker token and open Picker with that token without loading Google Identity Services.
- Without a connected binding, Add Source keeps the existing browser OAuth Picker path.
- The Picker token endpoint returns only a short-lived access token and safe metadata; it never returns refresh tokens, client secrets, OAuth transaction state, source file content, or unredacted personal data.
- Disconnecting or changing the binding immediately affects future Picker token requests.
