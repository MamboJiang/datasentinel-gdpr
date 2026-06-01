# Prelaunch Account System

## Problem Definition

lawdit needs real user sign-in before prelaunch so reviewers are not operating as a seeded demo actor. The system must support Google and GitHub login while keeping provider secrets and provider access tokens out of the browser.

## Research Basis

- Google OpenID Connect describes user login as a server flow that creates an anti-forgery state token, sends an authentication request, validates the returned state, exchanges the code, obtains an ID token, and authenticates the user. It also says Google OAuth login requires Cloud Console OAuth credentials and redirect URIs.
- Google OAuth for web server applications is designed for apps that can keep confidential information and maintain state, and it warns that client secret files must not be stored in public source trees.
- GitHub OAuth web application flow uses authorization code grant, redirects the user to GitHub, returns a temporary code plus state, and expects the app to abort if state does not match.
- GitHub now strongly recommends PKCE for OAuth web apps. Its token exchange accepts the original code verifier when a challenge was sent.
- GitHub email lookup requires the `user:email` scope when the primary email is not public.

Official references:

- https://developers.google.com/identity/openid-connect/openid-connect
- https://developers.google.com/identity/protocols/oauth2/web-server
- https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps
- https://docs.github.com/en/rest/users/emails

## Options

| Option | Upside | Downside | Decision |
| --- | --- | --- | --- |
| Frontend-only OAuth | Fast UI integration | Exposes tokens to the browser and complicates validation | Rejected |
| Hosted auth provider | Mature session and identity controls | Adds a third-party dependency and configuration surface not yet requested | Rejected |
| Backend-owned Google/GitHub OAuth with local sessions | Keeps secrets server-side, works with stdlib backend, easy to roll back | Still not enterprise SSO or durable production RBAC | Accepted |

## State Machine

States:

- `signed_out`
- `auth_starting`
- `provider_redirected`
- `callback_validating`
- `session_active`
- `auth_failed`
- `signed_out_after_logout`

Events:

- `start_login(provider)`
- `provider_callback(code, state)`
- `provider_denied(error)`
- `session_cookie_present`
- `logout_requested`
- `session_expired`

Guards:

- Provider must be one of `google` or `github`.
- Provider client ID and secret must be configured.
- `LAWDIT_SESSION_SECRET` must be configured before login can start.
- Callback state must match the signed auth transaction cookie.
- GitHub callback must supply the original PKCE verifier.
- Google identity must include a stable `sub` claim and matching client ID audience.
- GitHub identity must be revalidated with the user API after token exchange.

Transitions:

- `signed_out -> auth_starting` on `start_login(provider)` when provider is configured.
- `auth_starting -> provider_redirected` after the server creates signed state, optional PKCE challenge, and redirect.
- `provider_redirected -> callback_validating` on callback with code and state.
- `callback_validating -> session_active` after identity is validated and a first-party session cookie is created.
- `callback_validating -> auth_failed` on state mismatch, provider error, missing identity, or token exchange failure.
- `session_active -> signed_out_after_logout` on logout or expired session.

Side effects:

- Set short-lived signed auth transaction cookie during login start.
- Exchange authorization code on the backend only.
- Store local account profile and session metadata only.
- Use the local `userId` as the owner scope for SQLite-backed prelaunch Sources and workflow state.
- Discard provider access tokens after identity lookup.
- Set HttpOnly first-party session cookie.
- Clear session cookie on logout.

Failure paths:

- Unconfigured provider returns problem details and the UI keeps the user signed out.
- Provider denial redirects to the app with `auth=failed`.
- State mismatch rejects before provider token exchange.
- Token exchange failure rejects without creating a local account or session.
- Missing/expired session returns authenticated `false` on `/api/auth/session`.
- Cross-account Source or Finding identifiers return not found or the current account's empty state.
- A signed-out user who starts login from a same-app deep link can return to that path after successful login; unsafe absolute, protocol-relative, or `/api/*` return targets are ignored and fall back to the configured frontend return URL.

Rollback path:

1. Set `LAWDIT_AUTH_REQUIRED=false`.
2. Remove Google/GitHub client credentials from the runtime environment.
3. Keep existing `/api` workflow endpoints available for local development.
4. Delete local account/session rows from the SQLite file if needed; workflow state remains separate.

## Impact Surface

- Backend auth/session endpoints and cookie handling.
- Local SQLite schema for accounts and sessions.
- Frontend auth gate, account menu, and session page.
- API contract, security notes, deployment configuration, and acceptance criteria.
- Finding deep-link review routes that pass through the sign-in gate.
- Runtime environment variables for provider credentials and session secret.

## Primitive Acceptance Criteria

- An unauthenticated browser can see the configured provider list without receiving secrets.
- Starting Google login redirects to Google only when Google credentials and session secret are configured.
- Starting GitHub login redirects to GitHub with state and PKCE challenge only when GitHub credentials and session secret are configured.
- Starting login from a same-app Finding URL stores only that relative return path in the signed auth transaction and redirects back to it after successful callback.
- Starting login with an absolute or API return target ignores that target and redirects to the configured frontend fallback.
- A callback with mismatched state creates no local session.
- A successful callback creates one local user identity, one active session, and an HttpOnly session cookie.
- `/api/auth/session` returns the current user profile when the session cookie is valid and returns authenticated `false` when it is missing or expired.
- Logout invalidates the local session and clears the browser cookie.
- SQLite-backed Sources, scans, findings, audit events, metrics, and evaluation state are isolated by the current session user.
- Provider access tokens and client secrets are never returned in API payloads, frontend state, logs, mocks, or docs.
- Existing review permission boundaries still expose allowed and denied actions; auth does not imply real deletion rights.
