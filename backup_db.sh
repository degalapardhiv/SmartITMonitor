#!/bin/bash
set -euo pipefail

# Smart IT Monitor DB backup
# Reads POSTGRES_USER / POSTGRES_DB from the repo .env (used by docker-compose).

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

DB_USER="${POSTGRES_USER:-smartadmin}"
DB_NAME="${POSTGRES_DB:-smart_monitor}"
DB_CONTAINER="${DB_CONTAINER:-smart-monitor-db}"
BACKUP_DIR="${BACKUP_DIR:-backups}"

DATE=$(date +"%Y-%m-%d_%H-%M-%S")

mkdir -p "$BACKUP_DIR"

OUTFILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql"

if docker exec "$DB_CONTAINER" \
    pg_dump -U "$DB_USER" "$DB_NAME" \
    > "$OUTFILE"; then
    echo "Backup created: $OUTFILE"
else
    echo "ERROR: backup failed. Check that the compose DB container is running." >&2
    rm -f "$OUTFILE"
    exit 1
fi
