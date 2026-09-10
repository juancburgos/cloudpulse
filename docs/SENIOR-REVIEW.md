# How a senior cloud architect reviews this repository

> This document is intentionally public. It answers the question a candidate should ask before an interview:
> *"I am told I will be evaluated as a cloud architect — what will they actually look at?"*
> It is written from the reviewer's chair, and then used to audit **this** repository honestly.

---

## 1. What I look for (in this order)

I have ~20 minutes and a browser. I do not read every file. I follow a path, and each step decides whether I
keep reading.

### Step 0 — Can I understand it in 60 seconds? (README quality)

- Does the first screen tell me **what it is, where it runs, and why it exists**?
- Is there a **live URL I can hit right now**? A README that describes something I cannot reach is a story,
  not evidence.
- Screenshots of the app *and* the deployed endpoints.
- One architecture diagram. If the diagram needs a paragraph of prose to be understood, it is a bad diagram.

**Red flags:** walls of text with no diagram; "coming soon"; a demo I cannot reach; emojis replacing substance.

### Step 1 — Is there an architecture, or just files?

- Are **layers separated** (client / edge / service / data) with a clear contract between them?
- Can the reviewer see the **request path end-to-end**, including TLS termination and the proxy hop?
- Are failure modes named (DB down, service down, client offline)? Production thinking is mostly about the
  sad path.
- Is there a **scaling story** (stateless service? sessions? where would a queue or a cache go)?

**What impresses me:** a diagram plus a short "what breaks and what happens then" section.

### Step 2 — Is it actually deployed?

- Live HTTPS endpoint with a **valid certificate**.
- A health endpoint that is cheap and honest (`/healthz`), separate from business endpoints.
- Evidence of persistence (a row count that moves).
- The insecure default is absent: the database is **not** reachable from the public internet; the API binds to
  localhost behind a proxy.

**Red flags:** "runs locally on my machine"; `0.0.0.0` on every service with no firewall comment; self-signed
certs described as production.

### Step 3 — Are the decisions explained? (ADR thinking)

Seniority is not *what* you chose, it is *why* — and what you gave up.

- Are major choices recorded (proxy, database, containerization, provider-independence)?
- Does the writing include **consequences and rejected alternatives**?
- Is the reasoning honest about cost and operational burden?

**Red flags:** cargo-culting Kubernetes for a 200-line API; a "microservices" repo that is one process with
three Dockerfiles; no mention of cost.

### Step 4 — Is it operable? (runbook > code)

- Can somebody else **deploy it, roll it back and restore it** using only the docs?
- Backups: what, where, how often, and *how to restore* (a backup you never restored is a hope, not a plan).
- Logs: where do they go? How do I see the last error?
- Secrets: how are they injected, rotated, and kept out of git?

**Red flags:** no runbook; secrets in `.env` committed; "we would add monitoring later".

### Step 5 — Is it secure by default?

- TLS everywhere, automatic renewal.
- Least privilege: non-root containers where practical, DB credentials scoped, no admin ports exposed.
- Input validation at the boundary (schemas), sane timeouts on outbound calls.
- Privacy by design: what data is collected, where it goes, and what is deliberately *not* collected.

### Step 6 — Is it reproducible? (CI, tests, IaC)

- A pipeline that runs on every push: lint/tests, and a build that could produce the artifact.
- Some automated test that would actually fail if the API contract broke.
- Infrastructure expressed as code or, at minimum, as a **single reproducible compose file** plus documented
  provider steps. Terraform is a plus; a hand-built snowflake server is a minus.

### Step 7 — Is it maintainable by a team?

- Commit history that reads like intent ("add DB healthcheck") rather than "update", "fix", "asdf".
- Issue and PR templates, contribution guide, license, changelog, semantic versioning.
- Consistent structure and naming; no dead code paths; no secrets or build artifacts committed.

### Step 8 — Does the author show judgment about scope?

The hardest senior skill: **knowing what not to build**. A junior repository with 4 services, a message bus
and a service mesh for a demo app is a bigger red flag than a small repo that is fully finished, deployed,
documented and honest about its limits.

---

## 2. Scoring rubric (what the notes look like afterwards)

| Area | Weight | What earns full marks |
|---|---|---|
| Problem framing & scope judgment | 15% | Small, complete, honest about being a demonstrator |
| Architecture & diagrams | 20% | Layered, end-to-end view, failure modes, scaling path |
| Deployed reality | 20% | Live HTTPS, health endpoint, persistence proven, nothing exposed |
| Documentation & ADRs | 15% | Why + trade-offs + rejected alternatives + runbook |
| Operability & security | 15% | Backups/restore, secrets handling, least privilege, TLS |
| Automation & tests | 10% | CI on every push, a test that can fail, reproducible deploy |
| Craft (history, templates, license) | 5% | Clean commits, templates, license, changelog |

---

## 3. Self-assessment of this repository

Honest, including the gaps.

| Area | Score | Evidence | Gap that remains |
|---|---|---|---|
| Problem framing | 15/15 | `README` states it is a demonstrator, not a product; fixed scope | — |
| Architecture | 18/20 | Mermaid end-to-end diagram; layers separated; failure modes and scaling path documented | No load test / capacity numbers |
| Deployed reality | 19/20 | Live API + landing over HTTPS with Let's Encrypt; `/healthz` separate from `/api/v1/status`; DB not publicly exposed; pings persisted | No external uptime monitor configured yet (roadmap) |
| Documentation | 14/15 | 4 ADRs with consequences, runbook (deploy/rollback/backup/incident/migration), API contract | No sequence diagrams yet |
| Operability & security | 12/15 | Secrets `.env`-only and git-ignored; containers restart-policy + healthchecks; **documented** backup/restore | Automated backups not yet scheduled; API not yet non-root in the image |
| Automation & tests | 7/10 | CI runs pytest + a real end-to-end smoke test against a live service container | Android unit tests not yet wired into CI |
| Craft | 5/5 | Conventional commit history, templates, MIT license, changelog, `.editorconfig` | — |
| **Total** | **90/100** | | The remaining 10 points are listed in `docs/ROADMAP.md` |

---

## 4. What I would ask in the interview (and the expected answers)

1. **Why a reverse proxy instead of exposing the API directly?** → TLS automation, single ingress, static
   content and API behind one component, and the ability to swap the backend without touching the client.
2. **What happens when PostgreSQL dies?** → `/healthz` degrades to `db: down`, `/api/v1/status` reports
   `degraded`, writes fail with a clear error, the client shows an explicit offline state (demonstrable live).
3. **How would you scale this 100×?** → The API is stateless: run N replicas behind the proxy, move the
   database to a managed service, add a read replica for reads, cache the status payload, then add metrics and
   alerting before adding architecture.
4. **Why no Kubernetes?** → Operational cost exceeds the benefit at this size. It would be the right answer at
   a different scale, and the reasoning is written down (ADR-0003).
5. **How do you migrate to a cheaper cloud in 20 minutes?** → DNS change + `docker compose up`; the Android
   client targets a hostname, so the published app never needs an update (`docs/RUNBOOK.md#migration`).
6. **What did you deliberately not build?** → Auth, multi-tenancy, queues, IaC for the VPS, because they add
   surface area without proving anything new for this demonstrator — and the roadmap says when each would
   become justified.
