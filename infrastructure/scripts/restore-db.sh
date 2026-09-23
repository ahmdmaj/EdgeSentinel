#!/bin/bash
# =============================================================================
# EdgeSentinel Database Restore Script
# Usage: bash infrastructure/scripts/restore-db.sh ./backups/edgesentinel_backup_YYYYMMDD_HHMMSS.sql
# =============================================================================
set -euo pipefail

BACKUP_FILE="${1:-}"

if [ -z "${BACKUP_FILE}" ]; then
  echo "ERROR: No backup file specified."
  echo "Usage: bash restore-db.sh <path-to-backup.sql>"
  exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "ERROR: Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

# Resolve the repo root (two levels up from this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "${SCRIPT_DIR}/../.." && pwd )"

# Load credentials from .env
if [ -f "${REPO_ROOT}/.env" ]; then
  export $(grep -v '^#' "${REPO_ROOT}/.env" | xargs)
else
  echo "ERROR: .env file not found at ${REPO_ROOT}/.env"
  exit 1
fi

# Validate required variables
: "${MYSQL_USER:?MYSQL_USER is not set in .env}"
: "${MYSQL_PASSWORD:?MYSQL_PASSWORD is not set in .env}"
: "${MYSQL_DATABASE:?MYSQL_DATABASE is not set in .env}"

echo "================================================================"
echo " WARNING: This will COMPLETELY OVERWRITE the '${MYSQL_DATABASE}' database."
echo " Backup file: ${BACKUP_FILE}"
echo "================================================================"
read -r -p "Are you sure you want to proceed? (yes/no): " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
  echo "Restore cancelled."
  exit 0
fi

echo ""
echo "Step 1: Dropping and recreating '${MYSQL_DATABASE}' database..."
docker exec -i edgesentinel-mysql \
  mysql \
    --user="${MYSQL_USER}" \
    --password="${MYSQL_PASSWORD}" \
    --execute="DROP DATABASE IF EXISTS ${MYSQL_DATABASE}; CREATE DATABASE ${MYSQL_DATABASE};"

echo "Step 2: Restoring from backup file..."
docker exec -i edgesentinel-mysql \
  mysql \
    --user="${MYSQL_USER}" \
    --password="${MYSQL_PASSWORD}" \
    "${MYSQL_DATABASE}" < "${BACKUP_FILE}"

echo ""
echo "Restore completed successfully from: ${BACKUP_FILE}"
echo "Restart the cloud-api container to reconnect Prisma:"
echo "  docker compose restart cloud-api"
