# ADR-0003 — Cloud-portable Docker Compose deployment (no Kubernetes, no provider lock-in)

- **Status:** Accepted
- **Date:** 2026-09-09
- **Deciders:** Juan Carlos Burgos (author)

## Context

The workload must survive a change of cloud provider. The concrete trigger: the current VPS is on a
promotional renewal cycle, and the plan is to move to whichever provider offers the best price per month
(Hetzner, DigitalOcean, Contabo, …) — possibly more than once. The published Android app must not require an
update or a new store release each time the infrastructure moves.

Constraints:

1. One operator, no platform team.
2. Cost target: a single small VPS (≤ US$6/month), no managed services that multiply the bill.
3. The deployment must be reproducible from the repository alone.

## Decision

Deploy with **Docker Compose** (two services: `api`, `db`) described in this repository, fronted by Caddy.
Keep the client pointed at a **hostname**, never an IP. Treat the VPS as a replaceable, cattle-like host: all
state lives in a named Docker volume that is backed up per the runbook.

Deliberately **not** used: Kubernetes, Terraform for the host, provider-specific PaaS primitives (managed DB
add-ons, cloud load balancers, serverless functions).

## Consequences

**Positive**

- Migration procedure is literally: create VM → `docker compose up -d --build` → change two DNS records →
  verify `/healthz`. Measured time with a warm image registry: under 30 minutes, dominated by DNS TTL.
- The same compose file runs on a laptop, so "works on my machine" and "works in production" are the same
  artifact.
- No control-plane cost, no per-service pricing, no vendor SDK in the code path.
- The Android client never needs an update when the provider changes, because DNS is the indirection layer.

**Negative / accepted trade-offs**

- No self-healing beyond `restart: unless-stopped`; a dead host stays dead until a human notices. Accepted at
  this scale (see ROADMAP: external uptime monitor is the first item).
- Backups are the operator's responsibility (documented script + restore drill), not a managed feature.
- Horizontal scaling requires manual work (add a host, move the DB to a managed service) instead of a replica
  count. That is intentional: the scaling path is documented in `ARCHITECTURE.md §6` rather than pre-built.
- Kubernetes would be the correct answer for multi-team, multi-environment delivery with compliance isolation;
  at one service and one operator it would add a control plane to maintain and a new failure domain to debug.

## Alternatives considered

| Option | Why not |
|---|---|
| Kubernetes (managed) | Cost (control plane + nodes) and operational surface exceed the workload by an order of magnitude. See the "why not" reasoning in `SENIOR-REVIEW.md`. |
| Serverless (Cloud Run / Lambda + managed DB) | Superb fit for scale-to-zero; rejected because it hides the networking class of problems this demonstrator exists to show (TLS ingress, reverse proxy, container networking, volume persistence), and it re-introduces provider lock-in. |
| PaaS (Render, Railway, Fly.io) | Fast to deploy; the same objection as serverless, plus per-service pricing and less control over the edge layer. |
| Terraform for the VPS | Genuinely useful for multi-host fleets; for one host it adds a state file, a provider credential and a tool to learn. The migration runbook covers the same ground in a page. |
| Ansible | The host has exactly one responsibility (run containers); provisioning is three commands documented in the runbook. |
