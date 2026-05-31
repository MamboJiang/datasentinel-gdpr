# Fumadocs User Documentation

## Problem Definition

DataSentinel has detailed engineering, contract, and acceptance documents, but users need a task-oriented guide that explains how to operate the prototype without reading API contracts or implementation notes.

The new documentation surface must help users understand the workflow from sign-in and Workspace selection through source registration, scanning, findings review, audit inspection, evaluation, governance, and safety boundaries.

## Research Basis

- Fumadocs official manual installation for Next.js documents the standard app structure, `source.config.ts`, global CSS imports, and docs route pattern: <https://www.fumadocs.dev/docs/manual-installation/next>.
- Fumadocs official "Source" documentation describes loading MDX content into a docs page tree: <https://www.fumadocs.dev/docs/headless/source-api>.
- Fumadocs official search documentation describes server-side search routes from a configured source: <https://www.fumadocs.dev/docs/ui/search>.
- Next.js official documentation remains the underlying app framework reference for routing, metadata, and build behavior: <https://nextjs.org/docs>.

These references justify using a separate Next/Fumadocs documentation app instead of mixing the docs mechanism into the existing Vite console.

## Options Considered

| Option | Strength | Weakness | Decision |
| --- | --- | --- | --- |
| Add static Markdown files only | Minimal dependency impact | Does not satisfy the Fumadocs requirement or provide searchable docs navigation | Rejected |
| Embed Fumadocs into the existing Vite console | One app URL | Fumadocs is Next-oriented and would force a broad frontend framework change | Rejected |
| Add a separate `docs-site` Next/Fumadocs app | Isolated, reversible, matches Fumadocs model, avoids touching console behavior | Adds a second Node app and dependency lockfile | Selected |

## State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| No user docs site | Documentation app added | Fumadocs dependencies are scoped to `docs-site` | Docs app scaffolded | New Next/Fumadocs files exist outside the Vite console |
| Docs app scaffolded | User-guide pages added | Pages describe accepted product behavior and boundaries only | Content ready | MDX pages and sidebar metadata exist |
| Content ready | Build requested | Dependencies installed and MDX compiles | Build verified | Static/server build succeeds |
| Build verified | Deploy requested | `agent-us` Caddy and Node runtime are available | Deployed | `/docs*` routes proxy to the docs service |
| Deployed | Account menu Docs clicked | Browser is inside the console | Docs visible | The click performs a document navigation to `/docs` |
| Deployed | Docs search requested | Search endpoint stays outside product `/api/*` | Search results visible | Search uses `/docs/api/search` |
| Build verified | Docs content changes later | Changes stay user-facing and do not invent product behavior | Content ready | Re-run docs build and redeploy |
| Any state | Rollback requested | No production data migration depends on docs app | Previous state | Remove `docs-site`, generated lockfile, and acceptance/design references |

## Impact Surface

- Adds `docs-site/` as an isolated Next.js and Fumadocs application.
- Adds user-facing MDX guide content under `docs-site/content/docs/`.
- Adds docs-specific package dependencies and scripts in `docs-site/package.json`.
- Adds Tailwind v4 PostCSS processing for Fumadocs UI styles in `docs-site/postcss.config.mjs`.
- Adds `.source/` to `.gitignore` for Fumadocs generated source artifacts.
- Updates repository-level documentation and acceptance tracking for the new user docs surface.
- Adds a deployed docs route at `https://founder-force.uk/docs` through the existing `agent-us` Caddy server.
- Adds a docs-only Next service behind Caddy and keeps the product backend `/api/*` route unchanged.
- Changes the console account-menu Docs row to perform a document navigation to `/docs`.

No backend API, mock payload, product route, permission model, scan state, source integration, or deletion behavior changes are introduced.

## Rollback Path

1. Delete `docs-site/`.
2. Remove the `.source/` ignore entry if no other Fumadocs app uses it.
3. Remove this design note and the Fumadocs acceptance/test entries.
4. Re-run the existing frontend and backend checks if rollback touches shared files.

The rollback does not require database migration, contract version changes, or source-data cleanup.

## Primitive Acceptance Criteria

- A user can run the documentation app locally from `docs-site` with npm scripts.
- The docs app uses Fumadocs and Next.js rather than a custom static page.
- The docs sidebar exposes task-oriented pages for quick start, accounts/workspaces, sources, scans, findings/review, audit/evaluation, governance, safety, and FAQ.
- User-facing documentation states that DataSentinel does not provide legal advice or full GDPR compliance claims.
- User-facing documentation states that deletion is simulated in P0 and external files are not deleted.
- User-facing documentation explains redacted evidence, visible permission boundaries, audit events, evaluation metrics, and Workspace scoping.
- The docs content does not invent API fields, endpoints, production integrations, real deletion, production Microsoft Graph access, or hidden permission powers.
- The docs build passes after dependencies are installed.
- The remote host serves `https://founder-force.uk/docs` from the Fumadocs app without changing the `founder-force.uk` prefix.
- The remote docs search endpoint is under `/docs/api/search` and does not intercept product `/api/*` calls.
- The account-menu Docs button navigates to the deployed Fumadocs page instead of rendering the internal repository-docs placeholder.
