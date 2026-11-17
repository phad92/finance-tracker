#!/usr/bin/env bash
set -euo pipefail

# PostgreSQL restore & verification script for Docker Compose deployments.
# Usage:
#   ./scripts/restore_postgres.sh <backup.sql.gz> [--verify-sandbox]
#
# --verify-sandbox restores into a temporary scratch database and drops it afterward,
# verifying table count, FK constraint validity, and core financial table row counts.

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
  START_EPOCH=$(date -u +%s)
  TEST_DB="restore_verify_${START_EPOCH}"
  echo "[restore-test] Creating temporary database '${TEST_DB}'..."
  docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "CREATE DATABASE \"${TEST_DB}\";"
  trap 'docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS \"${TEST_DB}\";" >/dev/null 2>&1 || true' EXIT

  echo "[restore-test] Restoring '${BACKUP_FILE}' into '${TEST_DB}'..."
  gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${TEST_DB}" >/dev/null

  PG_VERSION=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${TEST_DB}" -tAc "SHOW server_version;")
  TABLE_COUNT=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${TEST_DB}" -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
  if [ "${TABLE_COUNT}" -le 0 ]; then
    echo "[restore-test] FAILED: No public tables restored." >&2
    exit 1
  fi

  UNVALIDATED_FKS=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${TEST_DB}" -tAc "SELECT count(*) FROM pg_constraint WHERE contype = 'f' AND NOT convalidated;")
  if [ "${UNVALIDATED_FKS}" -ne 0 ]; then
    echo "[restore-test] FAILED: Found ${UNVALIDATED_FKS} unvalidated foreign-key constraints." >&2
    exit 1
  fi

  echo "[restore-test] Checking core financial table row counts:"
  for TBL in users assets liabilities portfolios portfolio_holdings instrument_prices exchange_rates; do
    EXISTS=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${TEST_DB}" -tAc "SELECT to_regclass('public.${TBL}') IS NOT NULL;")
    if [ "${EXISTS}" = "t" ]; then
      CNT=$(docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${TEST_DB}" -tAc "SELECT count(*) FROM \"${TBL}\";")
      echo "  - ${TBL}: ${CNT} rows"
    fi
  done

  END_EPOCH=$(date -u +%s)
  DURATION=$((END_EPOCH - START_EPOCH))
  echo "[restore-test] PASSED | pg_version=${PG_VERSION} | tables=${TABLE_COUNT} | unvalidated_fks=0 | duration=${DURATION}s | backup=${BACKUP_FILE}"
  exit 0
fi

echo "[restore] WARNING: Restoring '${BACKUP_FILE}' directly into '${DB_NAME}' on '${CONTAINER_NAME}'..."
gunzip -c "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}"
echo "[restore] Restore complete."
