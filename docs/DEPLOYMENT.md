# Deployment

## Remote Preview and API Server

The approved deployment path is a controlled frontend plus P0 API server on `agent-us`. Caddy serves the Vite build and reverse-proxies `/api/*` to the local Python API server.

Current remote layout:

- Static releases: `/srv/datasentinel/frontend/releases/<timestamp>`
- Active release symlink: `/srv/datasentinel/frontend/current`
- API command: `python3 -m backend.datasentinel.source_server --host 127.0.0.1 --port 8000 --db-path /srv/datasentinel/data/datasentinel.sqlite3`
- Local SQLite state: `/srv/datasentinel/data/datasentinel.sqlite3`
- API route: Caddy proxies `/api/*` to `127.0.0.1:8000`
- Caddy config: `/etc/caddy/Caddyfile`
- Current validated public route: `https://founder-force.uk/`
- Host-IP fallback route: `http://52.159.109.133/`
- SSH route: `agent-us`; this may not resolve as an HTTP hostname unless local DNS or hosts configuration maps it

## Build and Deploy Frontend

Run from `frontend/`:

```bash
npm run test
npm run build
```

Upload `frontend/dist/` to a new timestamped release directory under `/srv/datasentinel/frontend/releases/`, then point `/srv/datasentinel/frontend/current` to that release.

## Run API Server

Run from the repository root on `agent-us`:

```bash
mkdir -p /srv/datasentinel/data
python3 -m pip install --user -r requirements.txt
python3 -m backend.datasentinel.db_tool init --db-path /srv/datasentinel/data/datasentinel.sqlite3
python3 -m backend.datasentinel.source_server --host 127.0.0.1 --port 8000 --db-path /srv/datasentinel/data/datasentinel.sqlite3
```

`requirements.txt` includes the PDF text-layer extraction dependency used by prelaunch source scans. DOCX, XLSX, and PPTX text extraction uses Python stdlib ZIP/XML modules and does not add another runtime dependency. Install the requirements on the same Python environment that runs the API service.
On Ubuntu/Debian hosts where Python reports an externally managed environment, either install into a virtual environment and point the service at that Python, or use the host-approved user-site override:

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

For a persistent preview, run the server command under the host's service manager and keep it bound to `127.0.0.1`. The P0 API is contract-backed and may use the local SQLite file for restart-safe demo state. It must not be exposed as a production source connector, production database, or source-file deletion-capable service.

The server can still run in memory for local debugging by omitting `--db-path`. `DATASENTINEL_DB_PATH` may also provide the database path when service-manager configuration is cleaner than command-line arguments.

When account-scoped schema migration runs, historical global source and workflow rows are moved to a `legacy_shared` owner scope. Signed-in users start from their own account scope and do not see those legacy rows unless an operator performs a manual migration.

## Prelaunch Account Configuration

Google and GitHub sign-in are optional locally and required only when `DATASENTINEL_AUTH_REQUIRED=true`.

Local/server `.env.local` values:

```bash
DATASENTINEL_AUTH_REQUIRED=true
DATASENTINEL_AUTH_REDIRECT_BASE_URL=https://founder-force.uk
DATASENTINEL_FRONTEND_RETURN_URL=https://founder-force.uk/dashboard
DATASENTINEL_SESSION_SECRET=<host secret>
DATASENTINEL_COOKIE_SECURE=true
DATASENTINEL_ENABLE_DEMO_FIXTURES=false
GOOGLE_CLIENT_ID=<google oauth client id>
GOOGLE_CLIENT_SECRET=<google oauth client secret>
GOOGLE_PICKER_API_KEY=<google picker api key>
GOOGLE_CLOUD_PROJECT_NUMBER=<google cloud project number>
GITHUB_CLIENT_ID=<github oauth client id>
GITHUB_CLIENT_SECRET=<github oauth client secret>
```

Register provider callbacks as:

- Google: `https://founder-force.uk/api/auth/callback/google`
- GitHub: `https://founder-force.uk/api/auth/callback/github`

The provider credentials authenticate users only. They must not be reused for source connectors, Microsoft Graph, tenant inventory, deletion, or authorization policy.

Google Drive source selection also requires Google Picker public setup. See `docs/GOOGLE_DRIVE_SETUP.md` for the focused checklist.

- Enable the Google Drive API and Google Picker API on the same Google Cloud project.
- Create an API key for Picker and restrict it to the preview origin, such as `https://founder-force.uk/*`, plus localhost origins used for development.
- Set `GOOGLE_PICKER_API_KEY` to that API key.
- Set `GOOGLE_CLOUD_PROJECT_NUMBER` to the numeric Google Cloud project number used as Picker `appId`.
- Add `https://founder-force.uk` as an authorized JavaScript origin on the Google OAuth web client.
- Add Drive scopes to the OAuth consent screen: `https://www.googleapis.com/auth/drive.file` for selected files and `https://www.googleapis.com/auth/drive.readonly` when folder traversal is enabled.

The Picker API key and project number are browser setup configuration, but they still belong in ignored host environment files so deployments can rotate or disable them. The Google OAuth client secret remains server-only and must never be returned by `/api/integrations/google-drive/picker-config`. In prelaunch, the route is protected by the first-party session cookie when `DATASENTINEL_AUTH_REQUIRED=true`.

Start the API with one or more local roots that users may register as sources:

```bash
python3 -m backend.datasentinel.source_server --host 127.0.0.1 --port 8000 --db-path /srv/datasentinel/data/datasentinel.sqlite3 --allowed-root /srv/datasentinel/sources
```

## OpenRouter AI Configuration

OpenRouter assistive AI is optional and must be configured only through ignored environment files or host secret management. Never commit a real API key.

Local/server `.env.local` values:

```bash
DATASENTINEL_AI_MODE=assistive
OPENROUTER_API_KEY=<host secret>
OPENROUTER_MODEL=google/gemini-3.1-flash-lite
OPENROUTER_SITE_URL=https://founder-force.uk/
OPENROUTER_APP_TITLE="DataSentinel GDPR"
DATASENTINEL_AI_BUDGET_EUR=25.00
DATASENTINEL_AI_BUDGET_USD=25.00
OPENROUTER_USAGE_BASELINE_USD=<usage from GET https://openrouter.ai/api/v1/key>
DATASENTINEL_AI_FAIL_CLOSED=true
DATASENTINEL_AI_MAX_PROMPT_TOKENS=6000
DATASENTINEL_AI_MAX_COMPLETION_TOKENS=350
DATASENTINEL_OCR_MODE=local
```

The server loads `.env.local` on startup without overriding existing process environment variables. The app reports AI readiness through `/api/health` and optional `aiProcessing` metadata in scan, metrics, and evaluation responses. Existing scans remain deterministic and show zero model calls unless a redacted assistive AI classification path is explicitly invoked.

Install the host `tesseract` binary when `DATASENTINEL_OCR_MODE=local`; otherwise supported image files are counted as hard/OCR-deferred warnings. Raw video media remains deferred until a separate approved FFmpeg-based processor is deployed.

OpenRouter bills in USD credits, so the runtime uses a conservative 25 USD application cap for the requested 25 EUR budget. Set the OpenRouter dashboard key credit limit as well when available; the application guard is not a replacement for provider-side spend limits.

The Caddy site must keep `/api/*` proxying before SPA fallback:

```caddyfile
{
	auto_https disable_redirects
}

founder-force.uk {
	route {
		handle /api/* {
			reverse_proxy 127.0.0.1:8000
		}

		handle {
			root * /srv/datasentinel/frontend/current
			try_files {path} /index.html
			file_server
		}
	}
}

:80 {
	route {
		handle /api/* {
			reverse_proxy 127.0.0.1:8000
		}

		handle_path /hermes-rich/* {
			root * /srv/hermes-public/rich
			file_server
			header X-Robots-Tag "noindex, nofollow"
		}

		handle {
			root * /srv/datasentinel/frontend/current
			try_files {path} /index.html
			file_server
		}
	}
}
```

Validate and reload after Caddyfile changes:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

## Validation

For shared preview work, validate the deployed server route directly. Local Vite or loopback API runs may help while editing, but they do not count as delivery validation for this project.

```bash
curl -I http://127.0.0.1/
curl -I http://127.0.0.1/dashboard
curl -s http://127.0.0.1/api/health
curl -s http://127.0.0.1/api/health | grep openrouter
curl -s --cookie "datasentinel_session=<session id>" http://127.0.0.1/api/integrations/google-drive/picker-config
curl -s http://127.0.0.1/api/sources | grep source_001
python3 -m backend.datasentinel.db_tool status --db-path /srv/datasentinel/data/datasentinel.sqlite3
curl -I https://founder-force.uk/
curl -I https://founder-force.uk/dashboard
curl -s https://founder-force.uk/api/health
curl -s --cookie "datasentinel_session=<session id>" https://founder-force.uk/api/integrations/google-drive/picker-config
curl -s http://127.0.0.1/ | grep DataSentinel
curl -s http://127.0.0.1/dashboard | grep DataSentinel
curl -s https://founder-force.uk/ | grep DataSentinel
curl -s https://founder-force.uk/dashboard | grep DataSentinel
```

If `founder-force.uk` is Cloudflare-proxied, its DNS origin record must point to `52.159.109.133` before the domain can reach the `agent-us` Caddy site.

The remote API is a P0 contract server. It may serve mock-compatible envelopes, in-memory scan/review state, or the approved local SQLite state file only. It must not connect to production file sources, call Microsoft Graph, mutate source files, use OAuth or tenant credentials, add a production database or queue, or perform source-file deletion. Source-registration deletion is allowed because it removes DataSentinel metadata only. If OpenRouter AI assistive mode is enabled, it must remain redacted-evidence-only, fail-closed, and capped by the configured project budget.

## Rollback

Restore the saved Caddyfile backup and reload Caddy:

```bash
sudo cp /etc/caddy/Caddyfile.datasentinel-backup-<timestamp> /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

To roll back only the frontend assets, repoint `/srv/datasentinel/frontend/current` to a previous release directory and reload or recheck the site. To roll back API persistence, stop the Python API service and restart it without `--db-path`; keep, archive, or remove `/srv/datasentinel/data/datasentinel.sqlite3` according to the demo-state retention decision. To roll back the API route, stop the Python API service, remove the `/api/*` reverse proxy block, validate Caddy, and reload.
