# Runbook — CloudPulse operations

Audience: whoever is on call (currently one person). Everything here is copy-pasteable.

## 0. Topology at a glance

| Thing | Value |
|---|---|
| Host | VPS (Ubuntu 24.04), any provider — currently `2.25.125.53` |
| Project path on the host | `/opt/cloudpulse` |
| Compose stack | `cloudpulse-api` (FastAPI, `127.0.0.1:8001`), `cloudpulse-db` (PostgreSQL, no published port) |
| Edge proxy | `caddy-caddy-1` (Caddy 2, host network, owns 80/443) |
| Static site | `/srv/cloudpulse-web` served by Caddy |
| Hostnames | `api.<domain>` → API, `cloudpulse.<domain>` → landing |
| Volume | `cloudpulse_cloudpulse_pgdata` |

## 1. Deploy (first time)

```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
sudo git clone <repo-url> /opt/cloudpulse && cd /opt/cloudpulse
cp .env.example .env && $EDITOR .env            # DB_PASSWORD, REGION
sudo docker compose -f deploy/docker-compose.yml up -d --build
curl -s http://127.0.0.1:8001/healthz           # expect {"status":"ok","db":"up"}
```

Then point DNS (`api`, `cloudpulse`) at the host and reload the proxy:

```bash
sudo cp deploy/Caddyfile.example /etc/caddy/Caddyfile   # set your domain
sudo systemctl reload caddy
curl -s https://api.<domain>/healthz
```

## 2. Deploy an update (rolling, no downtime)

```bash
cd /opt/cloudpulse
git pull
sudo docker compose -f deploy/docker-compose.yml up -d --build api   # only the API is replaced
curl -s https://api.<domain>/healthz
```

The database container is not touched by an API-only rebuild. If `db` must be recreated, take a backup first
(§5).

## 3. Rollback

Because images are tagged by the compose build, rollback is "checkout the previous revision and rebuild":

```bash
cd /opt/cloudpulse
git log --oneline -5
git checkout <previous-good-commit>
sudo docker compose -f deploy/docker-compose.yml up -d --build api
curl -s https://api.<domain>/healthz
```

For an immediate mitigation without code history, the previous image is still on the host:

```bash
sudo docker images | grep cloudpulse-api
sudo docker tag <previous-image-id> cloudpulse-api:1.0.0
sudo docker compose -f deploy/docker-compose.yml up -d api
```

## 4. Observe

```bash
sudo docker compose -f deploy/docker-compose.yml ps                 # is everything up?
sudo docker logs --tail 100 cloudpulse-api                          # last API requests
sudo docker logs --tail 100 cloudpulse-db                           # database messages
sudo docker logs --tail 100 caddy-caddy-1 | grep -i -E 'error|cert' # TLS & routing
curl -s https://api.<domain>/healthz                                # dependency health
curl -s https://api.<domain>/api/v1/status | python3 -m json.tool   # full picture
```

Key signals and what they mean:

| Signal | Meaning | Action |
|---|---|---|
| `/healthz` → `"db":"down"` | API is up, PostgreSQL is not | §6 database outage |
| `/healthz` → connection refused | API container not running | `docker compose ps`, then logs, then restart |
| HTTP 502 from the proxy | Upstream (API) is down or not listening on `127.0.0.1:8001` | Check the API container, then the port binding |
| Certificate errors in Caddy logs | DNS changed or port 80/443 blocked | Verify A records and that nothing else owns 80/443 |

## 5. Backup and restore (database)

**Backup**

```bash
sudo docker exec cloudpulse-db pg_dump -U cloudpulse cloudpulse \
  | gzip > /var/backups/cloudpulse-$(date +%F-%H%M).sql.gz
```

`scripts/backup-db.sh` does exactly this (and prunes files older than 14 days). Schedule it with cron:

```cron
15 3 * * * /opt/cloudpulse/scripts/backup-db.sh >> /var/log/cloudpulse-backup.log 2>&1
```

**Restore** (drill this before you need it)

```bash
gunzip -c /var/backups/cloudpulse-2026-09-09-0315.sql.gz \
  | sudo docker exec -i cloudpulse-db psql -U cloudpulse -d cloudpulse
curl -s https://api.<domain>/api/v1/status | python3 -c \
  'import json,sys;print("pings:",json.load(sys.stdin)["database"]["total_pings"])'
```

**What data loss actually means here:** the only table is `pings` (a timestamp and a user-agent string per
demo write). Losing it degrades the demo, not the business — this is why a nightly dump on the same host is
proportionate, and why off-host replication would be over-engineering *for this system*. For a system with
real data, the accepted answer would be a managed database with PITR.

## 6. Database outage

```bash
sudo docker compose -f deploy/docker-compose.yml ps
sudo docker logs --tail 50 cloudpulse-db
sudo docker compose -f deploy/docker-compose.yml up -d db
sleep 10 && curl -s http://127.0.0.1:8001/healthz
```

If the volume is suspected corrupt:

```bash
sudo docker compose -f deploy/docker-compose.yml stop db
sudo docker run --rm -v cloudpulse_cloudpulse_pgdata:/var/lib/postgresql/data alpine \
  sh -c 'ls -la /var/lib/postgresql/data'          # inspect before touching anything
```

Restore from §5 if the data directory is unusable.

## 7. Migration to another cloud provider

The client targets a **hostname**, so the app in the store never needs an update. Procedure:

1. Create the new VM (2 vCPU / 4 GB is plenty; ≥ 40 GB disk).
2. Install Docker, copy/clone the repository, create `.env`, `docker compose up -d --build`.
3. Take a fresh backup on the old host (§5) and restore it on the new one (§5).
4. Update the two A records (`api`, `cloudpulse`) to the new IP; keep TTL low (300 s) beforehand.
5. Reload Caddy on the new host (certificates are issued automatically once DNS resolves).
6. Verify `https://api.<domain>/healthz` and the app, then decommission the old host.

Measured: ~20–30 minutes, dominated by DNS propagation. Nothing in the stack is provider-specific.

## 8. Incident response (minimal, but written down)

1. **Detect** — external monitor / user report / `docker compose ps`.
2. **Stabilise** — restore service first (restart, rollback, or fail the status page over), diagnose after.
3. **Communicate** — for this project: the landing page status cards themselves show the degradation.
4. **Learn** — open an issue with timeline and root cause; if the fix is a process change, update this runbook
   or add an ADR. A post-mortem that changes nothing is theatre.

## 9. Useful one-liners

```bash
# Who is listening on 80/443?
sudo ss -tlnp | grep -E ':(80|443)'

# Is the API reachable only from localhost (expected)?
curl -s --max-time 3 http://<public-ip>:8001/healthz || echo "not publicly reachable (good)"

# Disk pressure (containers, logs, volumes)
df -h && sudo docker system df

# Free space safely
sudo docker image prune -f && sudo docker builder prune -f
```
