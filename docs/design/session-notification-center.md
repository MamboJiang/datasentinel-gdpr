# Session Notification Center

## Problem Definition

The app shell had a top-right notification button, but operation feedback rendered as a bottom toast. Prelaunch users need feedback to accumulate in a predictable notification center so source registration, scan, connection-test, review, and recoverable server-state messages can be reviewed in time order without covering page content.

## Options

| Option | Decision | Reason |
| --- | --- | --- |
| Keep bottom toast and make the bell decorative | Rejected | The bell remains non-functional and feedback disappears from view. |
| Add a backend notification service | Rejected | P0 does not need durable delivery, user preferences, queues, or external notification integrations. |
| Store session notifications in frontend state | Chosen | It is reversible, does not change the API contract, and satisfies the prelaunch UI behavior. |

## State Machine

| State | Event | Guard | Next state | Side effect |
| --- | --- | --- | --- | --- |
| Empty closed | User opens notifications | None | Empty open | Show empty notification center. |
| Empty closed/open | Operation emits message | Message is safe for UI display | Has notifications, current open state unchanged | Add timestamped notification at the top. |
| Has notifications closed | User opens notifications | None | Has notifications open | Show notifications sorted newest first. |
| Has notifications open | User dismisses one notification | Notification id exists | Has notifications open or empty open | Remove that notification only. |
| Has notifications open | User clears all | None | Empty open | Remove all session notifications. |
| Any open | Escape or outside click | None | Same content, closed | Close the popover. |

## Impact Surface

- Frontend data context changes from one transient toast string to a bounded session notification list.
- The app shell top-right bell becomes an interactive popover with keyboard close behavior.
- No backend routes, persistence schema, audit behavior, or external notification integrations change.
- Notifications remain user-facing status messages and do not replace audit events.

## Rollback Path

Revert the frontend context and app shell changes to the prior single-message toast behavior, remove `frontend/src/notifications.css`, and remove this design note and related acceptance updates. No data migration is required because notifications are session-only frontend state.

## Primitive Acceptance Criteria

- Operation feedback appears in the top-right notification center and does not render as a bottom toast.
- Notifications include a user-readable timestamp and are ordered newest first.
- The notification button opens and closes the panel, and Escape or outside click closes it.
- Users can dismiss one notification or clear all session notifications.
- Notification messages must not include raw sensitive evidence or source file bodies.
