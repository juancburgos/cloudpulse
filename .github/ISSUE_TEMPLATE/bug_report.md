---
name: Bug report
about: Something behaves differently from what the documentation says
title: "[bug] "
labels: bug
assignees: ''
---

## What happened

<!-- The exact request/command and the response you got. -->

```bash
$ curl -s https://api.example.com/healthz
{"status":"ok",...}
```

## What you expected

<!-- Quote the doc that made you expect it, e.g. docs/API.md or docs/RUNBOOK.md -->

## How to reproduce

1.
2.
3.

## Environment

| | |
|---|---|
| Where | production / local `docker compose` |
| Component | API / database / Android app / proxy / docs |
| Version | `curl -s <host>/healthz` output, or the app's version shown in the UI |
| Client | Android version, or the tool you used (`curl 8.x`, browser, …) |

## Extra evidence

<!-- Logs (`docker logs cloudpulse-api --tail 50`), screenshots, or the output of scripts/smoke-test.sh -->
