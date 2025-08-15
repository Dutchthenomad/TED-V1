#!/bin/bash

# Automatic Backup Scheduler for TED MongoDB
# Run this script to set up automated backups

BACKUP_SCRIPT="/mnt/c/Users/nomad/OneDrive/Desktop/GRAD_STUDIES/TED-V1/scripts/backup_mongodb.sh"
BACKUP_DIR="/mnt/c/Users/nomad/OneDrive/Desktop/GRAD_STUDIES/TED-V1-MONGO-BACKUP"

echo "=========================================="
echo "   TED MongoDB Auto-Backup Setup         "
echo "=========================================="
echo ""
echo "📁 Backup Directory: $BACKUP_DIR"
echo ""
echo "🔧 OPTION 1: Manual Backup Commands"
echo "   Quick backup:     ./scripts/backup_mongodb.sh"
echo "   JSON export:      ./scripts/backup_mongodb.sh json"
echo "   Full backup:      ./scripts/backup_mongodb.sh both"
echo ""
echo "🔧 OPTION 2: Add to Crontab (Linux/WSL)"
echo "   To backup daily at 2 AM, add this to crontab:"
echo "   0 2 * * * $BACKUP_SCRIPT backup"
echo ""
echo "🔧 OPTION 3: Windows Task Scheduler"
echo "   Create a scheduled task that runs:"
echo "   wsl.exe bash -c '$BACKUP_SCRIPT backup'"
echo ""
echo "📊 Current Backup Status:"
ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -5 || echo "   No backups yet"
echo ""
echo "=========================================="