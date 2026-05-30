# Deployment

## Remote Preview and API Server

The approved deployment path is a controlled frontend plus P0 API server on `agent-us`. Caddy serves the Vite build and reverse-proxies `/api/*` to the local Python API server.

Current remote layout:

- Static releases: `/srv/datasentinel/frontend/releases/<timestamp>`
- Active release symlink: `/srv/datasentinel/frontend/current`
- API command: `python3 -m backend.datasentinel.source_server --host 127.0.0.1 --port 8000`
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
python3 -m backend.datasentinel.source_server --host 127.0.0.1 --port 8000
```

For a persistent preview, run that command under the host's service manager and keep it bound to `127.0.0.1`. The P0 API is in-memory and contract-backed. It must not be exposed as a production source connector or deletion-capable service.

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

```bash
curl -I http://127.0.0.1/
curl -I http://127.0.0.1/dashboard
curl -s http://127.0.0.1/api/health
curl -s http://127.0.0.1/api/sources | grep source_001
curl -I https://founder-force.uk/
curl -I https://founder-force.uk/dashboard
curl -s https://founder-force.uk/api/health
curl -s http://127.0.0.1/ | grep DataSentinel
curl -s http://127.0.0.1/dashboard | grep DataSentinel
curl -s https://founder-force.uk/ | grep DataSentinel
curl -s https://founder-force.uk/dashboard | grep DataSentinel
```

If `founder-force.uk` is Cloudflare-proxied, its DNS origin record must point to `52.159.109.133` before the domain can reach the `agent-us` Caddy site.

The remote API is a P0 in-memory contract server. It may serve mock-compatible envelopes and in-memory scan/review state only. It must not connect to production file sources, call Microsoft Graph, mutate source files, use OAuth or tenant credentials, add a database or queue, call AI services, or perform deletion.

## Rollback

Restore the saved Caddyfile backup and reload Caddy:

```bash
sudo cp /etc/caddy/Caddyfile.datasentinel-backup-<timestamp> /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

To roll back only the frontend assets, repoint `/srv/datasentinel/frontend/current` to a previous release directory and reload or recheck the site. To roll back the API route, stop the Python API service, remove the `/api/*` reverse proxy block, validate Caddy, and reload.
