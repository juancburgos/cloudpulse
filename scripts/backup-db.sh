#!/usr/bin/env bash
# Dump the CloudPulse database to /var/backups and prune dumps older than RETENTION_DAYS.
# Install as a cron job:
#   15 3 * * * /opt/cloudpulse/scripts/backup-db.sh >> /var/log/cloudpulse-backup.log 2>&1
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
CONTAINER="${CONTAINER:-cloudpulse-db}"
DB_NAME="${DB_NAME:-cloudpulse}"
DB_USER="${DB_USER:-cloudpulse}"

mkdir -p "$BACKUP_DIR"
stamp="$(date +%F-%H%M)"
target="${BACKUP_DIR}/cloudpulse-${stamp}.sql.gz"

docker exec "$CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$target"

size="$(du -h "$target" | cut -f1)"
echo "$(date -Is) backup written: ${target} (${size})"

# Prune old dumps; a backup you never verify is a hope, so the runbook includes a restore drill.
find "$BACKUP_DIR" -name 'cloudpulse-*.sql.gz' -type f -mtime "+${RETENTION_DAYS}" -print -delete
echo "$(date -Is) pruned dumps older than ${RETENTION_DAYS} days"
