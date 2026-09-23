#!/bin/bash
# =============================================================================
# EdgeSentinel Database Backup Script
# Usage: bash infrastructure/scripts/backup-db.sh
# =============================================================================
set -euo pipefail

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

# Set up backup destination
BACKUP_DIR="${REPO_ROOT}/backups"
mkdir -p "${BACKUP_DIR}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/edgesentinel_backup_${TIMESTAMP}.sql"

echo "Starting backup of '${MYSQL_DATABASE}' database..."
echo "Destination: ${BACKUP_FILE}"

docker exec edgesentinel-mysql \
  mysqldump \
    --user="${MYSQL_USER}" \
    --password="${MYSQL_PASSWORD}" \
    --single-transaction \
    --routines \
    --triggers \
    "${MYSQL_DATABASE}" > "${BACKUP_FILE}"

echo "Backup completed successfully: ${BACKUP_FILE}"
echo "Size: $(du -sh "${BACKUP_FILE}" | cut -f1)"

# Optional: remove backups older than 7 days
find "${BACKUP_DIR}" -name "edgesentinel_backup_*.sql" -mtime +7 -delete
echo "Old backups (>7 days) pruned."

# =============================================================================
# To schedule this script via cron (runs daily at 2 AM):
#
#   crontab -e
#
# Add the following line:
#   0 2 * * * /bin/bash /path/to/EdgeSentinel/infrastructure/scripts/backup-db.sh >> /var/log/edgesentinel-backup.log 2>&1
#
# =============================================================================
