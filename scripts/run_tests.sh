#!/bin/bash

# TDD Test Runner Script for CRM Backend
# Following enterprise-grade testing standards

set -e  # Exit on any error

echo "🧪 Running TDD Tests for CRM Backend"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose file exists
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run from project root."
    exit 1
fi

echo "🐳 Starting Docker containers..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "🏥 Checking service health..."
for service in postgres redis; do
    if docker-compose ps $service | grep -q "Up (healthy)"; then
        print_status "$service is healthy"
    else
        print_warning "$service is not healthy yet, waiting..."
        sleep 5
    fi
done

# Build and start Django container
echo "🔨 Building Django development container..."
docker-compose build django --target development

echo "🚀 Starting Django container..."
docker-compose up -d django

# Wait for Django to be ready
echo "⏳ Waiting for Django to be ready..."
sleep 10

# Run database migrations
echo "📊 Running database migrations..."
docker-compose exec django python src/django/crm/manage.py migrate

# Create superuser for testing
echo "👤 Creating test superuser..."
docker-compose exec django python src/django/crm/manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@test.com').exists():
    User.objects.create_superuser('admin@test.com', 'admin123', 'Test', 'Admin')
    print('Test superuser created')
else:
    print('Test superuser already exists')
"

# Run tests with proper coverage
echo "🧪 Running model tests (TDD Approach)..."
echo "Following RED-GREEN-REFACTOR cycle"

# Run User model tests
echo "Testing User Model..."
if docker-compose exec django python -m pytest tests/test_models/test_user.py -v --cov=src/django/crm/crm/apps/authentication --cov-report=term-missing --cov-report=html; then
    print_status "User model tests passed!"
else
    print_error "User model tests failed! This is expected in TDD - implement code to make tests pass."
fi

# Run Contact model tests
echo "Testing Contact Model..."
if docker-compose exec django python -m pytest tests/test_models/test_contact.py -v --cov=src/django/crm/crm/apps/contacts --cov-report=term-missing --cov-report=html; then
    print_status "Contact model tests passed!"
else
    print_error "Contact model tests failed! This is expected in TDD - implement code to make tests pass."
fi

# Run Deal model tests
echo "Testing Deal Model..."
if docker-compose exec django python -m pytest tests/test_models/test_deal.py -v --cov=src/django/crm/crm/apps/deals --cov-report=term-missing --cov-report=html; then
    print_status "Deal model tests passed!"
else
    print_error "Deal model tests failed! This is expected in TDD - implement code to make tests pass."
fi

# Run Activity model tests
echo "Testing Activity Model..."
if docker-compose exec django python -m pytest tests/test_models/test_activity.py -v --cov=src/django/crm/crm/apps/activities --cov-report=term-missing --cov-report=html; then
    print_status "Activity model tests passed!"
else
    print_error "Activity model tests failed! This is expected in TDD - implement code to make tests pass."
fi

# Run all model tests
echo "🧪 Running all model tests..."
if docker-compose exec django python -m pytest tests/test_models/ -v --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=80; then
    print_status "All model tests passed with sufficient coverage!"
else
    print_warning "Some tests failed or coverage is below 80%. This is expected in TDD phase."
fi

# Show coverage report location
echo "📊 Coverage reports generated in htmlcov/index.html"

# TDD Instructions
echo ""
echo "🎯 TDD Next Steps:"
echo "=================="
echo "1. 📝 RED: Tests are failing (expected)"
echo "2. 🟢 GREEN: Implement minimum code to make tests pass"
echo "3. 🔧 REFACTOR: Improve code while keeping tests green"
echo "4. 🔄 Repeat for each feature"
echo ""
echo "To run individual test suites:"
echo "  docker-compose exec django python -m pytest tests/test_models/test_user.py"
echo "  docker-compose exec django python -m pytest tests/test_models/test_contact.py"
echo "  docker-compose exec django python -m pytest tests/test_models/test_deal.py"
echo "  docker-compose exec django python -m pytest tests/test_models/test_activity.py"
echo ""
echo "To run with coverage:"
echo "  docker-compose exec django python -m pytest tests/test_models/ --cov=src --cov-report=html"
echo ""

# Keep containers running for development
echo "🚀 Development environment is ready!"
echo "Django Admin: http://localhost:8000/admin/"
echo "FastAPI Docs: http://localhost:8001/docs"
echo "Flower (Celery): http://localhost:5555"
echo ""
echo "To stop containers: docker-compose down"
echo "To view logs: docker-compose logs -f django"