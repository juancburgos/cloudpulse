# Roadmap

Guiding rule: **finish and document what exists before adding surface area.** Each item below names the
trigger that would justify it — nothing is here "because production systems have it".

## Now (v1.0.x) — hardening the demonstrator

- [ ] **External uptime monitor** on `/healthz`, alerting on the `db` field (the smallest real improvement:
      right now nobody is told if the host dies).
- [ ] **Scheduled backups** — enable the cron entry for `scripts/backup-db.sh` and record one successful
      restore drill in this repository.
- [ ] **Non-root container user** and a read-only root filesystem for the API image.
- [ ] **Rate limit on `POST /api/v1/ping`** (the only public write) — a proxy-level limit is enough.
- [ ] **Android unit tests in CI** (currently only the backend is covered by the pipeline).

## Next (v1.1) — observability and cost transparency

- [ ] **Metrics endpoint** (`/metrics`, Prometheus format): request count/latency, error rate, DB probe
      latency. Trigger: the moment there is more than one operator or any real traffic.
- [ ] **Structured logs** (JSON) with request ids, so a log line can be correlated with a `ping_id`.
- [ ] **Cost dashboard** in the docs: monthly run rate per component, including what a managed database would
      add. Reasoning about cost is part of the job.
- [ ] **Load test** (k6 or `hey`) with recorded numbers in the README: p50/p95/p99 for `/api/v1/status`.

## Later (v2) — only if the purpose changes

- [ ] **History chart in the app** (uptime/availability over time) — needs a small time-series table or an
      external metric store; justified only if the app is used as a monitoring client, not as a demo.
- [ ] **Multi-region demo** (two providers, DNS latency routing) — the honest way to show provider
      portability beyond a migration runbook. Cost: two VPS.
- [ ] **Infrastructure as code** (Terraform for the host + cloud-init for provisioning) — justified when there
      is more than one host to keep consistent.
- [ ] **Authentication and API keys** — only if the endpoint becomes private; a public read-only demo API with
      no personal data does not need identity.

## Explicitly out of scope

These are common in "portfolio production stacks" and deliberately absent here. Each one would make the system
larger without proving anything new at this size:

- **Kubernetes / service mesh** — see ADR-0003.
- **Message broker / event bus** — no asynchronous workflow exists.
- **Microservices split** — three endpoints in one process; splitting would add network hops and distributed
  failure modes for zero benefit.
- **Multi-tenancy / user accounts** — the app stores nothing personal by design.
- **Machine-learning components** — the value of this artifact is architectural clarity, not novelty.
