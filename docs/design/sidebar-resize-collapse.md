# Sidebar Resize and Collapse

## Problem Definition

The internal console sidebar can be collapsed only by a button. Reviewers asked for direct horizontal dragging: dragging left should collapse the sidebar after a threshold, and dragging right should stop at a fixed maximum width.

## Options

| Option | Result | Tradeoff |
| --- | --- | --- |
| Keep button-only collapse | No new interaction state. | Does not satisfy the requested drag behavior. |
| Use CSS resize | Minimal code. | Browser resize handles are hard to make accessible, threshold-based collapse is unreliable, and max/min behavior is less explicit. |
| Use an explicit separator handle | Pointer and keyboard behavior are controlled and testable. | Adds a small shell state machine. |

Chosen option: explicit separator handle with pointer and keyboard controls.

## State Machine

| State | Event | Guard | Next state | Side effects |
| --- | --- | --- | --- | --- |
| Expanded | Pointer drag left | Raw width is below 180px | Collapsed | Sidebar width becomes 74px; workspace and account popovers close. |
| Expanded | Pointer drag within range | Raw width is 220px to 360px | Expanded | Sidebar width follows the pointer. |
| Expanded | Pointer drag right | Raw width is above 360px | Expanded | Sidebar width stays capped at 360px. |
| Collapsed | Pointer drag right | Raw width reaches 180px or more | Expanded | Sidebar reopens at no less than 220px. |
| Any | Escape during drag | Pointer interaction is active | Current visual state | Drag listeners are removed; the current width is retained. |
| Any | ArrowLeft or ArrowRight on handle | Desktop shell is active | Collapsed or Expanded | Width changes in 20px steps using the same thresholds. |
| Any | Home on handle | Desktop shell is active | Collapsed | Sidebar width becomes 74px. |
| Any | End on handle | Desktop shell is active | Expanded | Sidebar width becomes 360px. |
| Any | Enter or Space on handle | Desktop shell is active | Collapsed or Expanded | Toggles between collapsed and last expanded width. |

## Impact Surface

- Internal app shell sidebar width and collapsed state.
- Content shell left margin.
- Desktop-only pointer and keyboard accessibility for the sidebar separator.
- Frontend console contract and P0 acceptance text.

No API, mock payload, review state, scan state, permission model, authentication, or deployment behavior is changed.

## Rollback Path

Remove the resize handle component, restore fixed sidebar/content widths, remove this design note, and remove the contract/acceptance bullets. Button collapse remains the fallback behavior.

## Primitive Acceptance Criteria

- Dragging the sidebar separator left below 180px collapses the sidebar to icon-only mode.
- Dragging the separator right expands the sidebar and stops at 360px.
- Expanded width never drops below 220px.
- Collapsed width remains 74px.
- The content area follows the sidebar width without overlap.
- The resize separator supports keyboard resize and collapse/expand controls.
- The resize separator is hidden on mobile, where the existing slide-in navigation remains the active behavior.
