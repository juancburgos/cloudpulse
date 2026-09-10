# Roadmap

Guiding rule: **finish and document what exists before adding surface area.** Each item below names the
trigger that would justify it — nothing is here "because production systems have it".

## Now (v1.0.x) — hardening the demonstrator

- [x] **External uptime monitor** on `/healthz`, alerting on the `db` field — a scheduled workflow runs
      `scripts/smoke-test.sh` against production and opens a labelled issue when it fails
      (`.github/workflows/monitor.yml`). Alerting rides the repository's own issue tracker: no third-party
      account, no extra secret.
- [x] **Scheduled backups** — daily cron on the host plus a **restore drill recorded in the runbook**
      (a backup nobody restored is a hypothesis, not a backup).
- [x] **Rate limit on `POST /api/v1/ping`** (the only public write) — in process, per client address, with the
      proxy-header subtlety documented in ADR-0005.

- [ ] **Non-root container user** and a read-only root filesystem for the API image.
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
