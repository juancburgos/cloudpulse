# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- **API startup is no longer fatal when PostgreSQL is not ready yet.** The schema bootstrap is
  deferred with a warning instead of killing the process, and the next successful health probe
  retries it — a database that arrives late used to take the whole API down with it.
- `GET /api/v1/pings` is now covered by unit tests (the fake cursor implements `fetchall`).
- CI installs `backend/requirements-dev.txt`, so the `TestClient` dependency (`httpx`) is present.

### Added
- **Rate limiting on the only public write endpoint** (`POST /api/v1/ping`): per client address, in
  process, `429` + `Retry-After` when exceeded. Rationale, alternatives and the accepted
  per-worker caveat in `docs/ADR/0005-in-process-rate-limiting.md`.
- **Uptime monitor with alerting** (`.github/workflows/monitor.yml`): every 15 minutes it runs the real
  smoke test against production and opens — and later closes — a labelled issue when the service is
  unhealthy. Alerting via the issue tracker means no third-party account and no extra secret.
- **Scheduled database backups** on the host, plus a recorded **restore drill** in the runbook
  (33 rows in production → 33 rows restored into a disposable container, ~0.5 s).

### Security
- Documented the host hardening the live instance actually enforces (key-only SSH with the drop-in
  ordering gotcha, fail2ban, and the fact that Docker publishes ports past 
Usage: ufw COMMAND

Commands:
 enable                          enables the firewall
 disable                         disables the firewall
 default ARG                     set default policy
 logging LEVEL                   set logging to LEVEL
 allow ARGS                      add allow rule
 deny ARGS                       add deny rule
 reject ARGS                     add reject rule
 limit ARGS                      add limit rule
 delete RULE|NUM                 delete RULE
 insert NUM RULE                 insert RULE at NUM
 prepend RULE                    prepend RULE
 route RULE                      add route RULE
 route delete RULE|NUM           delete route RULE
 route insert NUM RULE           insert route RULE at NUM
 reload                          reload firewall
 reset                           reset firewall
 status                          show firewall status
 status numbered                 show firewall status as numbered list of RULES
 status verbose                  show verbose firewall status
 show ARG                        show firewall report
 version                         display version information

Application profile commands:
 app list                        list application profiles
 app info PROFILE                show information on PROFILE
 app update PROFILE              update PROFILE
 app default ARG                 set default application policy) in the runbook.
- Removed the host's IP address from the public docs: the live service is identified by its hostname,
  which is the only detail a reader of this repository needs.
- Enabled the GitHub-native security stack on this public repository: secret scanning (it flagged
  nothing), Dependabot alerts and security updates, CodeQL default setup, and private vulnerability
  reporting so a report never has to be filed as a public issue.

### Planned
- External uptime monitoring with alerting on the `db` field
- Scheduled database backups (script exists, cron entry pending)
- Rate limiting on the public write endpoint
- Android unit tests wired into CI

## [1.0.0] — 2026-09-09

First public release: the demo app, its API, and the deployment are live and documented.

### Added
- **API** (FastAPI, Python 3.12): `GET /healthz`, `GET /api/v1/status`, `POST /api/v1/ping`,
  `GET /api/v1/pings`, `GET /docs` (OpenAPI).
- **Data layer**: PostgreSQL 16 container with a named volume, `pg_isready` healthcheck and an indexed
  `pings` table created idempotently at startup.
- **Edge**: Caddy 2 as the single public ingress with automatic Let's Encrypt certificates; API bound to
  `127.0.0.1:8001`; database without a published port.
- **Client** (Kotlin, Material 3): status cards, ping action, 15-second auto-refresh, explicit degraded and
  offline states, bounded network timeouts.
- **Static site**: landing page with live status and the privacy policy required by the app store.
- **Deployment**: `deploy/docker-compose.yml` (provider-agnostic), `deploy/Caddyfile.example`.
- **Documentation**: architecture with Mermaid diagrams, four ADRs, runbook (deploy, rollback, backup,
  restore, incident, cloud migration), API contract, roadmap, senior review rubric.
- **Operations**: `scripts/smoke-test.sh`, `scripts/backup-db.sh`.
- **CI**: GitHub Actions workflow running the backend test suite and an end-to-end smoke test against a live
  PostgreSQL service container.
- **Distribution**: signed Android App Bundle published to Google Play (internal testing), Play App Signing
  enabled, upload key kept outside the repository.

### Security
- Secrets only via environment variables; `.env`, keystores and key properties are git-ignored.
- TLS enforced end-to-end; no cleartext traffic allowed by the client.
- No personal data collected: no accounts, no analytics, no advertising identifiers.

[Unreleased]: https://github.com/juancburgos/cloudpulse/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/juancburgos/cloudpulse/releases/tag/v1.0.0
