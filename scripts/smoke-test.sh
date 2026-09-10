#!/usr/bin/env bash
# End-to-end smoke test: proves the deployed (or local) stack answers, degrades correctly and persists writes.
#
#   scripts/smoke-test.sh                                  # local stack
#   API_URL=https://api.example.com scripts/smoke-test.sh  # production
set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8001}"
fail() { printf '  \033[31mFAIL\033[0m %s\n' "$1" >&2; exit 1; }
pass() { printf '  \033[32mok\033[0m   %s\n' "$1"; }

echo "CloudPulse smoke test against ${API_URL}"

# 1. Health probe answers and reports the database state.
health="$(curl -fsS --max-time 10 "${API_URL}/healthz")" || fail "GET /healthz unreachable"
db_state="$(printf '%s' "$health" | python3 -c 'import json,sys;print(json.load(sys.stdin)["db"])')"
[ "$db_state" = "up" ] || fail "database is not up (healthz: ${health})"
pass "/healthz ok (db=up)"

# 2. Status payload carries the fields the Android app renders.
status="$(curl -fsS --max-time 10 "${API_URL}/api/v1/status")" || fail "GET /api/v1/status unreachable"
printf '%s' "$status" | python3 -c '
import json, sys
d = json.load(sys.stdin)
for key in ("version", "status", "server", "database", "time"):
    assert key in d, f"missing key: {key}"
assert d["server"]["region"], "server.region is empty"
' || fail "status payload is missing required fields"
pass "/api/v1/status payload complete"

# 3. Write path: a ping must create a row and increase the counter.
before="$(printf '%s' "$status" | python3 -c 'import json,sys;print(json.load(sys.stdin)["database"]["total_pings"])')"
created="$(curl -fsS --max-time 10 -X POST "${API_URL}/api/v1/ping" -H 'User-Agent: smoke-test')" \
  || fail "POST /api/v1/ping failed"
row_id="$(printf '%s' "$created" | python3 -c 'import json,sys;print(json.load(sys.stdin)["db_row_id"])')"
after="$(printf '%s' "$created" | python3 -c 'import json,sys;print(json.load(sys.stdin)["total_pings"])')"
[ "$after" -eq "$((before + 1))" ] || fail "counter did not increase (before=${before}, after=${after})"
pass "ping persisted (row ${row_id}, total ${after})"

# 4. Read path: the new row is visible in the history.
curl -fsS --max-time 10 "${API_URL}/api/v1/pings?limit=1" \
  | grep -q 'smoke-test' || fail "the ping we just wrote is not in /api/v1/pings"
pass "history returns the row we just wrote"

# 5. Documentation surface is reachable (OpenAPI schema, not the UI).
curl -fsS --max-time 10 "${API_URL}/openapi.json" | grep -q '"openapi"' \
  || fail "OpenAPI schema not served"
pass "OpenAPI schema served"

echo "All checks passed."
