# Deployment

## Remote Preview

The approved deployment path is a controlled static frontend preview on `agent-us`. It serves the existing Vite build through the host's existing Caddy service.

Current remote layout:

- Static releases: `/srv/datasentinel/frontend/releases/<timestamp>`
- Active release symlink: `/srv/datasentinel/frontend/current`
- Caddy config: `/etc/caddy/Caddyfile`
- Current validated public route: `https://founder-force.uk/`
- Host-IP fallback route: `http://52.159.109.133/`
- SSH route: `agent-us`; this may not resolve as an HTTP hostname unless local DNS or hosts configuration maps it

## Build and Deploy

Run from `frontend/`:

```bash
npm run test
npm run build
```

Upload `frontend/dist/` to a new timestamped release directory under `/srv/datasentinel/frontend/releases/`, then point `/srv/datasentinel/frontend/current` to that release.

The Caddy site must keep SPA fallback enabled:

```caddyfile
{
	auto_https disable_redirects
}

founder-force.uk {
	root * /srv/datasentinel/frontend/current
	try_files {path} /index.html
	file_server
}

:80 {
	handle_path /hermes-rich/* {
		root * /srv/hermes-public/rich
		file_server
		header X-Robots-Tag "noindex, nofollow"
	}

	root * /srv/datasentinel/frontend/current
	try_files {path} /index.html
	file_server
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
curl -I https://founder-force.uk/
curl -I https://founder-force.uk/dashboard
curl -s http://127.0.0.1/ | grep DataSentinel
curl -s http://127.0.0.1/dashboard | grep DataSentinel
curl -s https://founder-force.uk/ | grep DataSentinel
curl -s https://founder-force.uk/dashboard | grep DataSentinel
```

If `founder-force.uk` is Cloudflare-proxied, its DNS origin record must point to `52.159.109.133` before the domain can reach the `agent-us` Caddy site.

The remote preview is mock-backed only. It must not run a backend API, connect to production file sources, call Microsoft Graph, mutate files, or perform deletion.

## Rollback

Restore the saved Caddyfile backup and reload Caddy:

```bash
sudo cp /etc/caddy/Caddyfile.datasentinel-backup-<timestamp> /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

To roll back only the frontend assets, repoint `/srv/datasentinel/frontend/current` to a previous release directory and reload or recheck the site.
