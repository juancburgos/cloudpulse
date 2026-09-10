# ADR-0001 — FastAPI (Python) for the API layer

- **Status:** Accepted
- **Date:** 2026-09-09
- **Deciders:** Juan Carlos Burgos (author)

## Context

The API exposes three trivial endpoints: a health probe, a status aggregate and a write that records a ping.
The repository is also a teaching artifact: a reader must be able to understand the whole service in a few
minutes, run it locally, and deploy it to a small VPS without a build platform.

Requirements that actually constrain the choice:

1. Small memory footprint (the target is a 4 GB VPS shared with other workloads).
2. Self-documenting HTTP contract (the app is one of several consumers, including a human with `curl`).
3. Minimal ceremony to add a route, a schema and a test.
4. Trivial containerization.

## Decision

Use **Python 3.12 + FastAPI + Uvicorn**, with **psycopg 3** for database access and no ORM.

## Consequences

**Positive**

- OpenAPI/Swagger is generated from the code, so the contract cannot silently drift from the implementation.
- Pydantic validation at the boundary keeps bad input out of the SQL layer.
- A ~120-line service is readable end-to-end, which is the point of the artifact.
- The container image is small (`python:3.12-slim` + four wheels) and starts in well under a second.

**Negative / accepted trade-offs**

- Python's concurrency model (GIL) means CPU-bound work would not scale on threads; irrelevant here because
  the workload is I/O-bound and we run multiple workers behind the proxy.
- No ORM means the SQL is hand-written: fewer magic behaviours, but schema changes require discipline. At one
  table with an index, that is a feature, not a cost.
- A compiled alternative (Go, Rust) would use less memory per instance; the operational simplicity of Python
  was worth more than the last 30 MB at this scale.

## Alternatives considered

| Option | Why not |
|---|---|
| Node.js + Express/Fastify | Perfectly viable; chosen against only because Python keeps the demo, the scripts and the ADRs in one language for a reader. |
| Go (net/http) | Best resource efficiency and a single static binary; more lines of code per endpoint, which works against the "readable in minutes" goal. |
| Spring Boot (Java) | Strong ecosystem, but ~300 MB RSS and a build toolchain that is disproportionate for three endpoints. |
| Django REST Framework | Batteries included; the admin/auth machinery would be dead weight for a service with no users. |
