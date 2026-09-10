# Deployment notes

## What runs where

| Container | Image | Published port | Reachable from |
|---|---|---|---|
| `cloudpulse-api` | built from `backend/` | `127.0.0.1:8001` | the host only (Caddy) |
| `cloudpulse-db` | `postgres:16-alpine` | none | the API container, on the compose network |
| `caddy` (not part of this file) | `caddy:2` | `80`, `443` | the internet |

The API is bound to loopback on purpose: the only public surface is the proxy. If you change that binding,
you have changed the security model — record it as an ADR.

## Quick start on a fresh VPS (Ubuntu 24.04)

```bash
# 1) Docker
curl -fsSL https://get.docker.com | sh

# 2) Code and configuration
sudo git clone <repo-url> /opt/cloudpulse && cd /opt/cloudpulse
cp .env.example .env
openssl rand -base64 24 | sed 's|^|DB_PASSWORD=|' > /tmp/pw && cat /tmp/pw
$EDITOR .env                     # paste a strong DB_PASSWORD, set REGION

# 3) Stack up
sudo docker compose -f deploy/docker-compose.yml up -d --build
curl -s http://127.0.0.1:8001/healthz

# 4) Edge proxy (TLS) — see Caddyfile.example
sudo cp deploy/Caddyfile.example /etc/caddy/Caddyfile   # set your domain
sudo systemctl reload caddy

# 5) DNS: point api.<domain> and cloudpulse.<domain> at this host, then verify
curl -s https://api.<domain>/healthz
```

## Verifying the deployment

```bash
API_URL=https://api.<domain> bash scripts/smoke-test.sh
```

The script fails loudly if the database is down, if the status payload loses a required field, or if the
write path stops persisting rows — the three failures that matter.

## Tuning knobs

| Variable | Default | Notes |
|---|---|---|
| `REGION` | `us-east-1` | Label shown in the app; keep it truthful to where the host actually is |
| `APP_VERSION` | `1.0.0` | Surfaced by `/healthz` and `/api/v1/status` |
| `DB_PASSWORD` | — | Required. Never commit it |
| `DATABASE_URL` | built from `DB_PASSWORD` | Override for a managed database |

## Why the database has no published port

A published PostgreSQL port on a public VPS is scanned within minutes. The compose file keeps the database on
the internal network and the API on loopback; both are reachable only where they are needed. Backups travel
through `docker exec` (see `scripts/backup-db.sh`), so no port is ever opened for administration.
