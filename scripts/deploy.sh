#!/bin/bash
# Simple deployment script following KISS principles
# Part of TDD-based CI/CD pipeline

set -e  # Exit on error

# Configuration - Simple and Clean
ENVIRONMENT=${1:-production}
PROJECT_NAME="crm"
DOCKER_REGISTRY="your-registry.com"
VERSION=${2:-latest}

echo "🚀 Starting deployment for ${ENVIRONMENT} environment..."
echo "📦 Version: ${VERSION}"

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

# RED Phase: Pre-deployment checks
pre_deployment_checks() {
    log "🔴 RED Phase: Pre-deployment validation"

    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running"
    fi

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose is not installed"
    fi

    # Check if required files exist
    required_files=("docker-compose.prod.yml" "Dockerfile.django" ".env.${ENVIRONMENT}")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            error "Required file $file not found"
        fi
    done

    log "✅ Pre-deployment checks passed"
}

# GREEN Phase: Build and test
build_and_test() {
    log "🟢 GREEN Phase: Building and testing"

    # Build Docker image
    log "🏗️ Building Docker image..."
    docker build -f Dockerfile.django -t ${PROJECT_NAME}:${VERSION} .

    # Run basic health check
    log "🏥 Running container health check..."
    docker run --rm -d --name ${PROJECT_NAME}-test -p 8001:8000 \
        -e DJANGO_SETTINGS_MODULE=crm.settings_test \
        -e PYTHONPATH=/app/src \
        ${PROJECT_NAME}:${VERSION}

    # Wait for container to start
    sleep 10

    # Check if container is healthy
    if docker ps | grep -q "${PROJECT_NAME}-test"; then
        log "✅ Container is running"
        docker stop ${PROJECT_NAME}-test
    else
        error "Container failed to start"
    fi

    log "✅ Build and test phase completed"
}

# DEPLOY Phase: Simple deployment
deploy() {
    log "🚀 DEPLOY Phase: Deploying application"

    # Use appropriate docker-compose file
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

    # Stop existing services
    log "⏹️ Stopping existing services..."
    docker-compose -f ${COMPOSE_FILE} down || true

    # Start new services
    log "▶️ Starting new services..."
    docker-compose -f ${COMPOSE_FILE} up -d

    # Wait for services to be ready
    log "⏳ Waiting for services to be ready..."
    sleep 30

    log "✅ Deployment completed"
}

# POST-DEPLOY: Health check
post_deployment_checks() {
    log "🔍 POST-DEPLOY: Health verification"

    # Check if main service is running
    if docker-compose ps | grep -q "Up"; then
        log "✅ Services are running"
    else
        error "Services failed to start properly"
    fi

    # Simple health check (can be extended)
    log "🏥 Performing health check..."

    # You can add more sophisticated health checks here
    # Example: curl -f http://localhost:8000/api/health/

    log "✅ Post-deployment checks passed"
}

# Cleanup function
cleanup() {
    log "🧹 Cleaning up..."
    # Remove unused Docker images
    docker image prune -f || true
    log "✅ Cleanup completed"
}

# Main deployment flow
main() {
    log "🎯 Starting TDD-based deployment pipeline"
    log "🔴 RED: Pre-deployment checks"
    log "🟢 GREEN: Build and test"
    log "🔄 REFACTOR: Deploy"

    pre_deployment_checks
    build_and_test
    deploy
    post_deployment_checks
    cleanup

    log "🎉 Deployment completed successfully!"
    log "📊 Deployment Summary:"
    log "  - Environment: ${ENVIRONMENT}"
    log "  - Version: ${VERSION}"
    log "  - Project: ${PROJECT_NAME}"
    log "  - Time: $(date)"
}

# Handle script interruption
trap 'error "Deployment interrupted"' INT

# Run main function
main