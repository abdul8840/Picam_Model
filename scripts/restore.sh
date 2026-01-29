#!/bin/bash

# PICAM Restore Script
# Restores a MongoDB backup

set -e

if [ -z "$1" ]; then
    echo "Usage: ./restore.sh <backup_file>"
    echo ""
    echo "Available backups:"
    ls -la ./backups/*.archive.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=========================================="
echo "PICAM Restore"
echo "=========================================="
echo ""
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "This will overwrite the current database. Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Restoring backup..."

# Decompress and restore
gunzip -c "$BACKUP_FILE" | docker compose exec -T mongodb mongorestore \
    --archive \
    --drop

echo ""
echo "✓ Restore complete"
echo ""