# Security policy

## Scope

This repository contains a public demonstration API and a mobile client. There are **no user accounts, no
personal data, no payments and no credentials in the repository** (see `.gitignore` and
`docs/ARCHITECTURE.md §7`). The realistic security interests are therefore:

1. Denial of service or abuse of the public write endpoint (`POST /api/v1/ping`).
2. Leakage of infrastructure secrets (SSH keys, database password, signing keystore).
3. Vulnerabilities in the running stack (proxy, API, database, base images).

## Reporting a vulnerability

Please **do not open a public issue** for anything exploitable. Use one of:

- GitHub's private vulnerability reporting on this repository (*Security → Report a vulnerability*), or
- email the maintainer at `juan.carlos.burgos.g@gmail.com` with the subject `[cloudpulse-security]`.

Include: what you found, how to reproduce it, and the impact you believe it has. You will get an
acknowledgement within 72 hours and a decision (accept / decline / need more info) within 7 days.

## What is in scope for a report

- Authentication/authorisation bypass — note there is no auth by design; report it only if you can reach
  something that should not be public (for example the database, or an internal port).
- Injection (SQL, command, template) reachable over HTTP.
- Resource exhaustion achievable with ordinary requests.
- Information disclosure of secrets or host internals through the public API.
- Supply-chain issues in the pinned dependencies.

## What is out of scope

- The absence of rate limiting / authentication on the public demo endpoint when it is simply being used as
  documented (that is a known limitation; a rate limit is on the roadmap).
- Denial of service by very large volumes of traffic (no protection is claimed for a single small VPS).
- Spam or content complaints about the demo `source` field.
- Findings that require a compromised host or physical access.

## Handling of secrets

- `.env`, `*.keystore`, `keystore.properties`, service-account JSON and any token file are git-ignored.
- Production secrets live only on the host, injected as environment variables at container start.
- The Android upload key is stored outside this repository; only the *public* certificate fingerprint belongs
  in documentation.
- If a secret is ever committed by mistake: rotate it first, then rewrite history. Rotation is the fix;
  history rewriting is only hygiene.
