#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL restore & verification script for Docker Compose deployments.
# Usage:
#   ./scripts/restore_postgres.sh <backup.sql.gz> [--verify-sandbox]
#
# --verify-sandbox restores into a temporary scratch database and drops it afterward,
# letting you prove backup recoverability without touching live data.

BACKUP_FILE="${1:-}"
MODE="${2:-}"

if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
  echo "Usage: $0 <path-to-backup.sql.gz> [--verify-sandbox]" >&2
  exit 1
fi

CONTAINER_NAME="${POSTGRES_CONTAINER:-finance_tracker_postgres_prod}"
DB_NAME="${POSTGRES_DB:-finance_tracker}"
DB_USER="${POSTGRES_USER:-finance_user}"

gzip -t "${BACKUP_FILE}"

if [ "${MODE}" = "--verify-sandbox" ]; then
  TEST_DB="restore_verify_$(date -u +%s)"
  echo "[restore-test] Creating temporary database '${TEST_DB}'..."
  docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${TEST_DB}\";"
  trap 'docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${TEST_DB}\";" >/dev/null 2>&1 || true' EXIT

  echo "[restore-test] Restoring '${BACKUP_FILE}' into '${TEST_DB}'..."
  gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${TEST_DB}" >/dev/null

  TABLE_COUNT=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${TEST_DB}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
  echo "[restore-test] Verified ${TABLE_COUNT} restored public tables in '${TEST_DB}'."
  exit 0
fi

echo "[restore] WARNING: Restoring '${BACKUP_FILE}' directly into '${DB_NAME}' on '${CONTAINER_NAME}'..."
gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}"
echo "[restore] Restore complete."

