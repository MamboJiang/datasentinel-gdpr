# Remote Preview Deployment

## Problem Definition

The project needs a shared remote preview so teammates can inspect the current P0 frontend without running a local Vite server. The preview must not expand the product boundary into production backend, Microsoft Graph, OAuth, tenant, deletion, storage, or legal-compliance claims.

This document covers the original static frontend hosting slice. The later loopback API server and local SQLite state file are governed by `docs/design/agent-us-api-server-integration.md` and `docs/design/local-sqlite-persistence.md`.

## Scope

In scope:

- Build the existing Vite frontend as static assets.
- Serve those assets from the `agent-us` host through its existing Caddy service and the `founder-force.uk` public domain.
- Preserve single-page app routing for `/`, `/dashboard`, `/sources`, `/findings`, `/audit`, `/evaluation`, and `/governance`.
- Keep all data fixture-backed through `contracts/mocks/`.

Out of scope:

- Backend API runtime.
- Authentication, authorization, tenant setup, Microsoft Graph, or OAuth.
- Real source mutation, deletion, quarantine, or production file access.
- New API fields, endpoints, or contract versions.

## Research Basis

- Caddy official documentation describes `root` plus `file_server` as the static-site serving pattern: https://caddyserver.com/docs/caddyfile/directives/root and https://caddyserver.com/docs/caddyfile/directives/file_server.
- Caddy official documentation describes `try_files` as the directive for request path fallback, which supports browser-routed single-page app URLs: https://caddyserver.com/docs/caddyfile/directives/try_files.
- Caddy official documentation recommends `/srv` or `/var/www/html` for systemd-served files instead of `/home`, which matches the `/srv/datasentinel` layout: https://caddyserver.com/docs/caddyfile/directives/file_server.

## Options

| Option | Benefits | Costs | Decision |
| --- | --- | --- | --- |
| Run `vite preview` on a high port | Fast and requires no Caddy change | Preview server is not a production static server and is less persistent | Rejected |
| Add Nginx | Common static-hosting path | Adds a system package and another server when Caddy already exists | Rejected |
| Use existing Caddy static file server | Persistent, already installed, no new runtime dependency, supports SPA fallback | Requires a small Caddyfile change and rollback note | Accepted |

## Deployment State Machine

| State | Event | Guard | Next State | Side Effect |
| --- | --- | --- | --- | --- |
| Not deployed | Build succeeds | `npm run build` passes | Built | `frontend/dist` contains static assets |
| Built | Upload release | SSH and `/srv/datasentinel` are writable by deployment user | Uploaded | Release directory receives static assets |
| Uploaded | Point current symlink | Release directory has `index.html` | Release selected | `/srv/datasentinel/frontend/current` points to the release |
| Release selected | Validate Caddy config | `caddy validate` succeeds | Ready to reload | Existing Caddyfile backup is retained |
| Ready to reload | Reload Caddy | Caddy service is active | Serving | Port 80 serves the selected release |
| Serving | Health check | `/` and `/dashboard` return HTML | Verified | Remote preview is usable |
| Any state | Validation fails | Failure observed | Rolled back or blocked | Keep previous Caddyfile/current release; report failure |

## Impact Surface

- Remote filesystem: `/srv/datasentinel/frontend/releases` and `/srv/datasentinel/frontend/current`.
- Remote server configuration: `/etc/caddy/Caddyfile`.
- Public HTTP surface: `founder-force.uk` and the host-IP fallback on `agent-us`.
- Repository docs: deployment design, validation cases, and acceptance criteria.

No API contract, mock payload, product workflow, review decision, deletion behavior, or sensitive-data display behavior changes.

## Rollback Path

1. Restore the saved Caddyfile backup from `/etc/caddy/Caddyfile.datasentinel-backup-*`.
2. Run `sudo caddy validate --config /etc/caddy/Caddyfile`.
3. Run `sudo systemctl reload caddy`.
4. Optionally repoint `/srv/datasentinel/frontend/current` to the previous release or remove `/srv/datasentinel`.

## Primitive Acceptance Criteria

- A production frontend build passes before upload.
- The remote host serves the static app from Caddy on port 80 without adding Node, Nginx, OAuth, Graph, production database, or deletion services; the loopback API and local SQLite state file are governed by their own design notes.
- Direct visits to `https://founder-force.uk/` and `https://founder-force.uk/dashboard` return the frontend HTML after DNS points to `agent-us`.
- Existing non-DataSentinel Caddy routes remain configured unless explicitly retired.
- The remote preview remains mock-backed and does not expose raw sensitive values.
- Rollback can restore the previous Caddyfile and previous release pointer.
