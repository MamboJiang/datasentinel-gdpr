# Project Homepage Parallax

## Problem Definition

The root route currently behaves like an internal operations dashboard. The project also needs a public-facing homepage that explains lawdit as a GDPR data discovery and review workflow before a user enters the product workspace.

## Research Basis

- `greensock/gsap-skills` documents GSAP as the recommended animation engine for scroll-driven React animations and points to ScrollTrigger for parallax, scrubbed motion, and pinned sections.
- GSAP ScrollTrigger documentation defines `trigger`, `start`, `end`, `scrub`, `pin`, and cleanup-sensitive scroll animation patterns.
- The Tailscale reference uses a minimal announcement bar, simple navigation, large product headline, and product-category strip. lawdit should borrow the structural clarity, not the exact visual execution.

## Options

| Option | Description | Tradeoff | Decision |
| --- | --- | --- | --- |
| Keep dashboard at `/` | Leave the root route as the internal dashboard. | Fast, but does not support project introduction or external sharing. | Rejected |
| Static marketing page | Add a non-animated homepage. | Low risk, but misses the requested parallax effect and feels less product-specific. | Rejected |
| Public homepage with GSAP parallax | Move the internal dashboard to `/dashboard`, make `/` a project homepage, and use GSAP ScrollTrigger for product-scene parallax. | Adds one animation dependency and route change, but matches the requested homepage goal. | Accepted |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Homepage visible | Open dashboard clicked | Always | Dashboard route | Navigate to `/dashboard` |
| Homepage visible | Anchor nav clicked | Target section exists | Section focused | Browser scrolls to section |
| Homepage visible | User scrolls | Reduced motion is not requested | Parallax active | GSAP updates transform and opacity |
| Homepage visible | User scrolls | Reduced motion is requested | Static page | Motion remains disabled |
| Homepage unmounts | Route changes | Always | Animations disposed | GSAP context reverts ScrollTriggers and inline transforms |

## Impact Surface

- Frontend route `/` becomes the public homepage.
- Internal dashboard route becomes `/dashboard`.
- Sidebar dashboard navigation points to `/dashboard`.
- New landing page component and scoped CSS are added.
- `gsap` is added as the animation dependency.
- No API contract, mock payload, backend behavior, deletion behavior, or sensitive data exposure changes.

## Rollback Path

Restore the root route to `DashboardPage`, point sidebar navigation back to `/`, remove the homepage files, remove the `gsap` dependency, and delete this design note.

## Primitive Acceptance Criteria

- Visiting `/` shows a public lawdit project homepage, not the internal dashboard shell.
- The homepage introduces GDPR data discovery, evidence, owner routing, human review, audit trails, and evaluation without claiming full legal compliance.
- A user can navigate from the homepage to the internal dashboard at `/dashboard`.
- Scroll movement animates product-scene layers when reduced motion is not requested.
- Reduced-motion users can read the same page without required animation.
- Existing internal routes such as `/sources`, `/findings`, and `/dashboard` remain available.
