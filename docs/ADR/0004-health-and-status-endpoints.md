# ADR-0004 — Health and status as two separate endpoints

- **Status:** Accepted
- **Date:** 2026-09-09
- **Deciders:** Juan Carlos Burgos (author)

## Context

Two very different consumers need to know whether the service is well:

1. **Machines** — the container runtime's healthcheck, an uptime monitor, a load balancer. They need a cheap,
   fast, stable answer with a strict status code contract. They poll frequently (every 10–30 seconds).
2. **Humans and the mobile app** — they need the rich picture: version, region, uptime, database latency,
   row counts, last write timestamp.

A single endpoint serving both would either make monitoring expensive (running aggregates every 15 seconds) or
make the app's payload poor.

## Decision

Expose **`GET /healthz`** for machines and **`GET /api/v1/status`** for the app and humans.

- `/healthz` runs a single `SELECT 1`, returns `{"status": "ok|degraded", "db": "up|down", ...}` and is used by
  the container healthcheck. It has no aggregates and no formatting work.
- `/api/v1/status` returns the composite payload with a latency probe (`SELECT 1` timed with
  `perf_counter`) and the aggregate counts/timestamps.

Both endpoints return **HTTP 200** when the service is reachable, and carry the degradation in the body
(`status`, `db`) instead of flipping to 5xx. The client decides how to render that — this keeps a real
outage (process not answering) distinguishable from a partial failure (database unreachable), and avoids
removing a partially working instance from rotation.

## Consequences

**Positive**

- Monitoring stays cheap and stable; the rich contract can evolve without breaking probes.
- One round trip from the app yields everything the UI needs (status + database + uptime).
- Degradation is observable without a second tool: `curl /healthz` tells you instantly whether the DB is gone.
- 200-with-body semantics let the app show a meaningful "degraded/offline" UI instead of a generic error.

**Negative / accepted trade-offs**

- Two endpoints to keep consistent; both are small and live in the same module, and the app only consumes the
  richer one.
- A naive external monitor that only checks the HTTP status code will report "up" during a database outage.
  Documented in the runbook: monitoring should alert on the `db` field, not only the status code.
- Returning 200 on partial failure is a deliberate, documented convention; a consumer expecting 5xx on
  degradation must read the body. This trade-off is the reason this ADR exists.

## Alternatives considered

| Option | Why not |
|---|---|
| Single `/status` endpoint for everything | Aggregates on every 15-second probe from every monitor; coupling monitoring cost to UI richness. |
| `/healthz` returning 503 when the DB is down | Simpler for monitors, but conflates "process alive" with "dependency alive" and makes the app's degraded state indistinguishable from a hard failure. |
| Separate sidecar/probe process | Extra container to run and document; no benefit at this size. |
