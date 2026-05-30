# Account Menu Utility Actions

## Problem Definition

The account menu exposed visible controls for theme, feedback, homepage navigation, changelog, help, docs, logout, platform status, account settings, and plan upgrade, but most controls had no behavior. Reviewers need these controls to either open a concrete surface or expose a safe prototype boundary.

## Options

| Option | Result | Tradeoff |
| --- | --- | --- |
| Keep controls inert | No new routes or UI state. | Fails the visible account-control expectation and makes the menu misleading. |
| Use modal-only panels | Keeps navigation unchanged. | Harder to deep-link, test, and document; can overload the app shell. |
| Add internal utility routes plus local-only actions | Gives each button a testable behavior while keeping P0 mock-backed. | Adds small route surface that must remain clearly outside production auth, billing, and support integrations. |

Chosen option: internal utility routes plus local-only theme, language preference, and feedback behavior.

## State Machine

### Account Menu

| State | Event | Guard | Next state | Side effects |
| --- | --- | --- | --- | --- |
| Closed | Open account menu | Sidebar account trigger exists | Open | Menu receives keyboard-accessible controls. |
| Open | Close menu, Escape, backdrop, route click | None | Closed | Popover is removed from the shell. |
| Open | Select utility route | Route exists | Closed, routed | Router opens the selected utility page. |
| Open | Toggle sidebar | None | Closed, sidebar collapsed or expanded | Workspace/account popovers close before layout changes. |

### Theme

| State | Event | Guard | Next state | Side effects |
| --- | --- | --- | --- | --- |
| System | Select light | Browser storage available | Light | `data-theme=light` and local theme mode are stored. |
| System | Select dark | Browser storage available | Dark | `data-theme=dark` and local theme mode are stored. |
| Light or Dark | Select system | Browser media query available | System | Theme resolves from `prefers-color-scheme`. |

### Language Preference

| State | Event | Guard | Next state | Side effects |
| --- | --- | --- | --- | --- |
| Default English preference | Select supported language | Code exists in local supported list | Preference selected | Language code is stored locally; interface copy remains English in P0. |
| Preference selected | Reload app | Stored code remains supported | Preference restored | Menu selector shows the stored code. |

### Feedback

| State | Event | Guard | Next state | Side effects |
| --- | --- | --- | --- | --- |
| Draft | Submit note | Note is at least 8 characters | Submitted | Local success state appears; no network call is made. |
| Submitted | Edit note | None | Draft | Success state clears. |

### Session and Plan Boundaries

| State | Event | Guard | Next state | Side effects |
| --- | --- | --- | --- | --- |
| Viewing session boundary | Return to dashboard | Route exists | Dashboard | No production session is ended. |
| Viewing prototype plan | Read plan | None | Prototype plan | No billing, subscription, or tenant onboarding is started. |

## Impact Surface

- Frontend app shell account menu.
- Internal router utility pages: account, feedback, changelog, help, docs, status, plan, and session boundary.
- Local theme state stored in browser localStorage.
- Frontend console contract and P0 acceptance text.

No API contract, backend endpoint, mock payload, production authentication, billing, Microsoft Graph, OAuth, tenant, translation service, or deletion behavior is added.

## Rollback Path

Revert the account menu component extraction, remove utility routes from `App.tsx`, remove utility pages and their CSS, and remove this design note plus the contract/acceptance bullets. Existing primary console routes remain unaffected.

## Primitive Acceptance Criteria

- Account menu opens and closes by trigger, Escape, backdrop, and route selection.
- Theme controls visibly select system, light, and dark modes without a backend call.
- Language preference selects from EU language entries, persists locally, and keeps interface copy English-only in P0.
- Feedback accepts a local note and confirms it was saved only for the prototype session.
- Home Page opens `/`.
- Account settings, changelog, help, docs, status, plan, and session boundary routes render in the internal shell.
- Log Out opens a session-boundary page and does not claim to end a production session.
- Prototype plan page does not enable billing, subscription, procurement, or tenant onboarding.
- No route exposes raw sensitive content, legal advice, full-compliance claims, real deletion, or production integration.
