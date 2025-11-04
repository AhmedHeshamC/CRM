#!/bin/bash
# PostgreSQL Database Backup Script for CRM Project
# Following SOLID and KISS principles
# Single Responsibility: Database backup automation

set -e  # Exit on any error

# Configuration
DB_NAME=${DB_NAME:-"crm_db"}
DB_USER=${DB_USER:-"crm_user"}
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
BACKUP_DIR=${BACKUP_DIR:-"/var/backups/crm"}
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/crm_backup_$TIMESTAMP.sql"

echo "🔄 Starting PostgreSQL database backup..."
echo "Database: $DB_NAME"
echo "Backup file: $BACKUP_FILE"

# Function to check if PostgreSQL is running
check_postgres() {
    pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1
}

# Function to create backup
create_backup() {
    echo "📦 Creating database backup..."

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Set environment variable for password
    export PGPASSWORD="$DB_PASSWORD"

    # Create backup
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --no-password --format=custom --compress=9 \
        --file="$BACKUP_FILE" || {
        echo "❌ Backup failed"
        exit 1
    }

    echo "✅ Backup created successfully: $BACKUP_FILE"
}

# Function to verify backup
verify_backup() {
    echo "🔍 Verifying backup file..."

    if [ -f "$BACKUP_FILE" ]; then
        file_size=$(du -h "$BACKUP_FILE" | cut -f1)
        echo "✅ Backup file verified (Size: $file_size)"
    else
        echo "❌ Backup file not found"
        exit 1
    fi
}

# Function to clean old backups (keep last 7 days)
cleanup_old_backups() {
    echo "🧹 Cleaning up old backups (keeping last 7 days)..."

    find "$BACKUP_DIR" -name "crm_backup_*.sql" -mtime +7 -delete || {
        echo "⚠️  Warning: Failed to clean old backups"
    }
}

# Main execution
main() {
    echo "🎯 Starting PostgreSQL database backup process..."

    # Check if PostgreSQL is running
    if ! check_postgres; then
        echo "❌ PostgreSQL is not running or not accessible"
        exit 1
    fi

    # Create backup
    create_backup

    # Verify backup
    verify_backup

    # Clean old backups
    cleanup_old_backups

    echo ""
    echo "🎉 Database backup completed successfully!"
    echo "📁 Backup location: $BACKUP_FILE"
    echo "📅 Created at: $(date)"
}

# Run main function
main "$@"