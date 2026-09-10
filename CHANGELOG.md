# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
