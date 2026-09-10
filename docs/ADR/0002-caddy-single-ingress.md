# ADR-0002 — Caddy as the single public ingress (TLS termination)

- **Status:** Accepted
- **Date:** 2026-09-09
- **Deciders:** Juan Carlos Burgos (author)

## Context

Three things must be reachable over HTTPS from the public internet: the API (`api.<domain>`), the static
landing page with the privacy policy (`cloudpulse.<domain>`), and — on the same host — other unrelated
services. The host is a single small VPS, and the author is the only operator.

Hard requirements:

1. Valid, publicly trusted TLS certificates, renewed without human intervention.
2. One public surface (ports 80/443) with an explicit mapping of hostname → upstream.
3. Nothing else published: the API and the database must not be directly reachable.

## Decision

Run **Caddy 2** in a container with `network_mode: host` as the only public ingress. It terminates TLS,
obtains and renews Let's Encrypt certificates automatically, proxies to upstreams bound to `127.0.0.1`, and
serves the static landing directory.

## Consequences

**Positive**

- Certificate issuance and renewal (including OCSP stapling and HTTP→HTTPS redirect) require **zero**
  configuration beyond the site block — no `certbot` timer, no renewal hooks.
- Adding a hostname is a three-line block; onboarding a new service takes seconds.
- Because Caddy is the only component on 80/443, the security boundary is easy to state and to audit.
- HTTP/2 and compression are defaults, so the app gets them for free.

**Negative / accepted trade-offs**

- One more process to keep running (mitigated by `restart: unless-stopped` and container healthchecks).
- `network_mode: host` is used so Caddy can reach loopback upstreams; it weakens container network isolation on
  the host. Accepted knowingly: the alternative (a shared Docker network) buys isolation this deployment does
  not need, at the cost of a more confusing network topology for a reader.
- Caddy's configuration is a DSL; readers unfamiliar with it must learn it. The Caddyfile is short enough to be
  read in full in one screen.

## Alternatives considered

| Option | Why not |
|---|---|
| Nginx + certbot | Proven, but the renewal timer, the ACME webroot and the reload hooks are three moving parts to maintain and to document. |
| Traefik | Excellent label-driven routing for dynamic environments; its value is highest when services appear and disappear automatically, which does not happen here. |
| Cloudflare Tunnel / LB | Removes the need for public ports and inbound rules, but adds a third-party dependency and a control plane in front of a demo whose point is to be readable end-to-end. |
| Exposing Uvicorn directly with a self-managed certificate | No renewal automation, no redirect handling, no protection from malformed requests, and the API would need to bind publicly. Rejected outright. |
