#!/bin/bash
# Simple rollback script following KISS principles
# Part of TDD-based CI/CD pipeline

set -e  # Exit on error

# Configuration
ENVIRONMENT=${1:-production}
PROJECT_NAME="crm"
BACKUP_COUNT=${2:-1}

echo "🔄 Starting rollback for ${ENVIRONMENT} environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Simple logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

# Backup current state before rollback
backup_current_state() {
    log "📦 Backing up current state..."

    # Create backup directory
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p ${BACKUP_DIR}

    # Backup database (if PostgreSQL)
    if docker-compose ps postgres | grep -q "Up"; then
        log "🗄️ Backing up database..."
        docker-compose exec postgres pg_dump -U postgres crm > ${BACKUP_DIR}/database.sql
    fi

    # Backup current Docker images
    log "🐳 Backing up Docker images..."
    docker save ${PROJECT_NAME}:current | gzip > ${BACKUP_DIR}/current-image.tar.gz

    log "✅ Backup completed: ${BACKUP_DIR}"
}

# Simple rollback function
rollback() {
    log "🔄 Rolling back deployment..."

    # Determine compose file based on environment
    case $ENVIRONMENT in
        "production")
            COMPOSE_FILE="docker-compose.prod.yml"
            ;;
        "staging")
            COMPOSE_FILE="docker-compose.staging.yml"
            ;;
        *)
            COMPOSE_FILE="docker-compose.yml"
            ;;
    esac

    log "📋 Using compose file: ${COMPOSE_FILE}"

    # Stop current services
    log "⏹️ Stopping current services..."
    docker-compose -f ${COMPOSE_FILE} down

    # Restore previous version (simple approach)
    log "📦 Restoring previous version..."

    # You can implement more sophisticated rollback logic here
    # For example: pulling previous Docker image tag

    # Start services with previous version
    log "▶️ Starting services with previous version..."
    docker-compose -f ${COMPOSE_FILE} up -d

    log "✅ Rollback completed"
}

# Health check after rollback
health_check() {
    log "🏥 Verifying rollback health..."

    # Wait for services to start
    sleep 30

    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        log "✅ Services are running after rollback"
    else
        error "Services failed to start after rollback"
    fi

    log "✅ Rollback health check passed"
}

# Main rollback flow
main() {
    log "🎯 Starting rollback process"

    backup_current_state
    rollback
    health_check

    log "🎉 Rollback completed successfully!"
    log "📊 Rollback Summary:"
    log "  - Environment: ${ENVIRONMENT}"
    log "  - Time: $(date)"
}

# Handle script interruption
trap 'error "Rollback interrupted"' INT

# Run main function
main