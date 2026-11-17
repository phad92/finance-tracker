#!/usr/bin/env bash
set -euo pipefail

# Automated PostgreSQL logical backup script for Docker Compose deployments.
# Usage: ./scripts/backup_postgres.sh [backup_dir] [retention_days]

BACKUP_DIR="${1:-./backups}"
RETENTION_DAYS="${2:-30}"
CONTAINER_NAME="${POSTGRES_CONTAINER:-finance_tracker_postgres_prod}"
DB_NAME="${POSTGRES_DB:-finance_tracker}"
DB_USER="${POSTGRES_USER:-finance_user}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[backup] Dumping PostgreSQL database '${DB_NAME}' from container '${CONTAINER_NAME}'..."
docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists \
  | gzip -c > "${OUT_FILE}"

if [ ! -s "${OUT_FILE}" ]; then
  echo "[backup] ERROR: Backup file is empty: ${OUT_FILE}" >&2
  exit 1
fi

echo "[backup] Verifying gzip integrity..."
gzip -t "${OUT_FILE}"

echo "[backup] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete

echo "[backup] Completed successfully: ${OUT_FILE}"

