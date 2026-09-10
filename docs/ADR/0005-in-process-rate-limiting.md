# ADR-0005 — Rate limit the public write endpoint in process, not with Redis

- **Status:** Accepted
- **Date:** 2026-09-10
- **Deciders:** maintainer
- **Related:** ADR-0001 (FastAPI), ADR-0004 (health and status endpoints)

## Context

`POST /api/v1/ping` is the only endpoint that writes, it is public, and it requires no credentials —
that is the point of the demo. Every call inserts a row in PostgreSQL. Two consequences follow:

1. Any client, including a script, can fill the database or the disk with junk rows.
2. The endpoint is also a load amplifier: one cheap HTTP request becomes one write plus one
   aggregate count on the database.

There is no user system, so "who" can only mean "from which network address". The API runs as a
single container behind Caddy on one host (ADR-0002), and the traffic this project will ever see is
a portfolio's worth: tens of requests per day, with the occasional burst.

## Decision

Meter the write endpoint **per client address, in process memory**, using a fixed-window counter:
`RATE_LIMIT_MAX` requests (default 20) per `RATE_LIMIT_WINDOW_S` seconds (default 60). Callers over
the limit receive `429` with a `Retry-After` header and a small JSON envelope. The counter table is
bounded (`max_keys`, default 10 000) and pruned, because the number of distinct addresses is
attacker-controlled.

The client address is taken from the **right-most** entry of `X-Forwarded-For`. Caddy either
appends the peer it observed or overwrites the header with it, so in both cases the right-most entry
is the address the trusted proxy vouched for, while the left-most is whatever the caller typed.
Reading the left-most entry — the intuitive choice — would let any client choose a fresh bucket per
request and never be throttled at all.

## Alternatives considered

| Option | Why not |
|---|---|
| **No limit** | The endpoint is public and unauthenticated. An unbounded write path is not a demo, it is an open door. |
| **Redis + a sliding window** | Correct and horizontally scalable, but adds a service, a failure mode and a backup target to protect an endpoint that sees a handful of calls per day. Cost is real, benefit is theoretical at this size. |
| **Caddy rate limiting / a plugin** | Keeps application code clean, but leaves the limit invisible in tests and outside the repository (the Caddyfile is host state). The API should enforce its own contract. |
| **Cloudflare or an API gateway** | Adds a provider dependency and another place where the request path can break; contradicts the provider-portable stance of ADR-0003. |
| **Token bucket with smoothing** | Smoother traffic shaping, more state and more tests for a case nobody has. A fixed window is one comparison. |

## Consequences

**Good**

- One request from a misbehaving client cannot translate into unbounded rows or database load.
- Behaviour is unit-tested: the limit is exclusive at the boundary, windows expire, clients are
  independent, the table stays bounded, and a spoofed `X-Forwarded-For` does not buy a new bucket.
- No new infrastructure, no new secret, no new backup.

**Bad / accepted risks**

- The limit is **per process**: with N workers or N containers a client gets N times the quota. The
  deployment runs two Uvicorn workers, so the effective limit is 2 × `RATE_LIMIT_MAX`. Documented
  and accepted at this size.
- A restart clears the counters: an attacker who can force restarts has already won something else.
- The limit is per address, so clients behind a shared NAT share a bucket. For a demo this is the
  right trade-off; a real product with users would key on identity, not address.
- `429` is a new failure mode the Android client can meet. The client already renders any non-2xx
  as a retryable error, so no client change was required.

## When this decision must be revisited

- The API runs more than one instance or more than a handful of workers (the quota multiplies).
- The limit needs to be per account rather than per address.
- Real traffic arrives: at that point a shared counter (Redis, or an edge rate limiter) is both
  justified and measurable, and this ADR should be superseded rather than patched.
