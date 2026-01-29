#!/bin/bash

# PICAM Backup Script
# Creates a backup of the MongoDB database

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="picam_backup_${TIMESTAMP}"

echo "=========================================="
echo "PICAM Backup"
echo "=========================================="
echo ""

# Create backup directory
mkdir -p ${BACKUP_DIR}

# Create backup
echo "Creating backup..."
docker compose exec -T mongodb mongodump \
    --db=picam \
    --archive > "${BACKUP_DIR}/${BACKUP_NAME}.archive"

# Compress
gzip "${BACKUP_DIR}/${BACKUP_NAME}.archive"

# Calculate size
SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.archive.gz" | cut -f1)

echo ""
echo "✓ Backup created successfully"
echo "  File: ${BACKUP_DIR}/${BACKUP_NAME}.archive.gz"
echo "  Size: ${SIZE}"
echo ""

# Keep only last 7 backups
echo "Cleaning old backups (keeping last 7)..."
ls -t ${BACKUP_DIR}/picam_backup_*.archive.gz 2>/dev/null | tail -n +8 | xargs -r rm
echo "✓ Cleanup complete"
echo ""