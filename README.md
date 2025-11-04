# 🏢 Enterprise CRM Backend System

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-4.2+-green.svg)](https://www.djangoproject.com/)
[![Test Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen.svg)](https://github.com/your-org/crm-backend)

A comprehensive, enterprise-grade Customer Relationship Management (CRM) backend system built with Django, following SOLID principles, Test-Driven Development (TDD), and KISS methodology. This system provides complete business functionality for managing customer relationships, sales pipelines, and business operations with military-grade security and advanced DevOps capabilities.

---

## 📋 Table of Contents

1. [🛠️ Tech Stack & Architecture](#️-tech-stack--architecture)
2. [🚀 Quick Start](#-quick-start)
3. [📡 API Documentation](#-api-documentation)
4. [🧪 Testing Guide](#-testing-guide)
5. [🔧 Development Setup](#-development-setup)
6. [🚀 Deployment](#-deployment)
7. [🤝 Contributing](#-contributing)
8. [📄 License](#-license)

---

## 🛠️ Tech Stack & Architecture

### **Backend Framework**
- **Django 4.2.16** - Core web framework with enterprise features
- **Django REST Framework** - Powerful API toolkit for RESTful APIs
- **Django Extensions** - Additional management commands and utilities

### **Database & Storage**
- **SQLite** - Development and testing database
- **PostgreSQL** - Production database (recommended)
- **Redis** - Caching and session storage (optional)

### **Authentication & Security**
- **JWT (JSON Web Tokens)** - Stateless authentication with access/refresh tokens
- **Django Allauth** - Advanced authentication system
- **Django CORS Headers** - Cross-origin resource sharing support
- **Custom Security Middleware** - Rate limiting, security headers, and threat protection

### **Performance & Optimization**
- **orjson 3.10.12** - High-performance JSON serialization (100x faster than standard json)
- **Django Debug Toolbar** - Development debugging and profiling
- **Simple Cache System** - Custom caching implementation with Redis support

### **Testing & Quality Assurance**
- **pytest 8.3.3** - Advanced testing framework with Django integration
- **pytest-django** - Django-specific pytest plugin
- **pytest-cov** - Test coverage reporting
- **Factory Boy** - Test data generation
- **Faker** - Realistic test data creation

### **Development Tools**
- **Black** - Code formatting (opinionated code formatter)
- **isort** - Import statement organization
- **flake8** - Code linting and style checking
- **mypy** - Static type checking
- **bandit** - Security vulnerability scanning
- **safety** - Dependency vulnerability checking

### **Architecture Patterns**
- **SOLID Principles** - Single responsibility, Open/closed, Liskov substitution, Interface segregation, Dependency inversion
- **KISS Principle** - Keep it simple, stupid approach to code complexity
- **TDD Methodology** - Test-driven development with red-green-refactor cycle
- **Repository Pattern** - Data access abstraction layer
- **Service Layer** - Business logic separation from controllers

### **Project Structure**
```
crm/
├── src/django/crm/           # Main Django project
│   ├── crm/                 # Project configuration
│   │   ├── settings.py      # Base settings
│   │   ├── settings_test.py # Test configuration
│   │   └── urls.py          # URL routing
│   └── apps/                # Django applications
│       ├── authentication/  # User management & auth
│       ├── contacts/        # Contact management
│       ├── deals/          # Deal pipeline management
│       ├── activities/     # Activity and task tracking
│       └── monitoring/     # System health & metrics
├── src/shared/              # Shared utilities
│   ├── repositories/        # Data access patterns
│   ├── validators/          # Validation logic
│   └── services/           # Business logic services
├── tests/                  # Comprehensive test suite
│   ├── unit/              # Unit tests (21 tests)
│   ├── integration/       # Integration tests (30 tests)
│   └── api/               # API endpoint tests
└── docs/                  # Documentation
```

---

## 🚀 Quick Start

### **Prerequisites**
- Python 3.11+ (3.13 recommended)
- pip (Python package manager)
- Git

### **Installation Steps**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd crm
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   export DJANGO_SETTINGS_MODULE=crm.settings_test
   export PYTHONPATH=/path/to/crm/src
   ```

4. **Run initial setup**
   ```bash
   cd src/django/crm
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

5. **Start the development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/api/v1/`

---

## 📡 API Documentation

### **Base Configuration**
- **Base URL**: `http://localhost:8000/api/v1/`
- **Content-Type**: `application/json`
- **Authentication**: Bearer Token (JWT)
- **API Version**: v1

### **Authentication Headers**
```http
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

## 🔐 Authentication Endpoints

### **User Registration**
```http
POST /api/v1/auth/register/
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "role": "sales",
  "phone": "+1-555-123-4567",
  "department": "Sales"
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "sales",
    "full_name": "John Doe"
  },
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### **User Login**
```http
POST /api/v1/auth/login/
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "sales"
  }
}
```

### **Token Refresh**
```http
POST /api/v1/auth/refresh/
```

**Request Body:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

### **Get Current User Profile**
```http
GET /api/v1/auth/users/me/
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "role": "sales",
  "full_name": "John Doe"
}
```

## 👥 Contact Management Endpoints

### **List Contacts**
```http
GET /api/v1/contacts/
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `search` - Search in name/email/company fields
- `is_active` - Filter by active status (true/false)
- `company` - Filter by company name
- `page` - Page number for pagination
- `page_size` - Items per page (max 100)

**Response (200 OK):**
```json
{
  "count": 50,
  "next": "http://localhost:8000/api/v1/contacts/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "phone": "+1-555-123-4567",
      "company": "Example Inc",
      "title": "Sales Manager",
      "is_active": true,
      "owner": 1,
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z",
      "deals_count": 3,
      "total_deal_value": "$150,000.00"
    }
  ]
}
```

### **Create Contact**
```http
POST /api/v1/contacts/
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@example.com",
  "phone": "+1-555-987-6543",
  "company": "Tech Corp",
  "title": "CEO",
  "website": "https://techcorp.com",
  "address": "456 Tech Blvd",
  "city": "San Francisco",
  "state": "CA",
  "country": "USA",
  "postal_code": "94105",
  "tags": ["VIP", "Enterprise", "Tech"],
  "lead_source": "Website"
}
```

### **Get Contact Details**
```http
GET /api/v1/contacts/{id}/
Authorization: Bearer <access_token>
```

### **Update Contact**
```http
PATCH /api/v1/contacts/{id}/
Authorization: Bearer <access_token>
```

**Request Body (partial update):**
```json
{
  "title": "Senior Sales Manager",
  "phone": "+1-555-555-5555"
}
```

### **Delete Contact (Soft Delete)**
```http
DELETE /api/v1/contacts/{id}/
Authorization: Bearer <access_token>
```

*Note: This performs a soft delete. The contact is marked as deleted but not removed from the database.*

## 💼 Deal Management Endpoints

### **List Deals**
```http
GET /api/v1/deals/
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `stage` - Filter by pipeline stage (prospect, qualified, proposal, negotiation, closed_won, closed_lost)
- `contact` - Filter by contact ID
- `owner` - Filter by owner ID
- `is_won` - Filter by won status (true/false)
- `is_lost` - Filter by lost status (true/false)
- `min_value` - Minimum deal value
- `max_value` - Maximum deal value

**Response (200 OK):**
```json
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Enterprise Software License",
      "description": "Annual software license agreement",
      "value": 150000.00,
      "currency": "USD",
      "formatted_value": "$150,000.00",
      "probability": 50,
      "stage": "proposal",
      "pipeline_position": 3,
      "expected_close_date": "2024-12-31",
      "is_won": false,
      "is_lost": false,
      "is_open": true,
      "owner": 1,
      "contact": 1,
      "contact_name": "John Doe",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z"
    }
  ]
}
```

### **Create Deal**
```http
POST /api/v1/deals/
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "title": "Enterprise Software License",
  "description": "Annual software license agreement for enterprise customer",
  "value": 150000.00,
  "currency": "USD",
  "stage": "proposal",
  "probability": 50,
  "expected_close_date": "2024-12-31",
  "contact": 1
}
```

### **Update Deal Stage**
```http
PATCH /api/v1/deals/{id}/
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "stage": "negotiation",
  "probability": 75,
  "expected_close_date": "2024-11-30"
}
```

## 📅 Activity Management Endpoints

### **List Activities**
```http
GET /api/v1/activities/
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `type` - Filter by activity type (call, email, meeting, note, task)
- `contact` - Filter by contact ID
- `deal` - Filter by deal ID
- `is_completed` - Filter by completion status (true/false)
- `priority` - Filter by priority (low, medium, high)
- `scheduled_after` - Activities scheduled after this date
- `scheduled_before` - Activities scheduled before this date

**Response (200 OK):**
```json
{
  "count": 15,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "uuid": "550e8400-e29b-41d4-a716-446655440001",
      "type": "call",
      "type_display": "Phone Call",
      "title": "Follow up with client",
      "description": "Discuss proposal and pricing",
      "scheduled_at": "2024-01-15T14:00:00Z",
      "duration_minutes": 30,
      "duration_display": "30 minutes",
      "priority": "high",
      "priority_display": "High Priority",
      "is_completed": false,
      "is_cancelled": false,
      "status": "scheduled",
      "contact": 1,
      "contact_name": "John Doe",
      "deal": 1,
      "deal_title": "Enterprise Software License",
      "owner": 1,
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z"
    }
  ]
}
```

### **Create Activity**
```http
POST /api/v1/activities/
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "type": "call",
  "title": "Follow up with client",
  "description": "Discuss proposal and pricing",
  "scheduled_at": "2024-01-15T14:00:00Z",
  "duration_minutes": 30,
  "priority": "high",
  "contact": 1,
  "deal": 1,
  "location": "Client Office",
  "video_conference_url": "https://zoom.us/j/123456789",
  "reminder_minutes": 15
}
```

### **Complete Activity**
```http
PATCH /api/v1/activities/{id}/
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "is_completed": true,
  "completion_notes": "Had a productive discussion about pricing terms"
}
```

## 🏥 System Health Endpoints

### **Basic Health Check**
```http
GET /health/
```

**Response (200 OK):**
```json
{
  "status": "healthy"
}
```

### **Detailed Health Check**
```http
GET /api/v1/monitoring/health/detailed/
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T10:00:00Z",
  "components": {
    "database": {
      "healthy": true,
      "response_time_ms": 15,
      "status": "ok"
    },
    "cache": {
      "healthy": true,
      "response_time_ms": 5,
      "status": "ok"
    }
  },
  "business_metrics": {
    "active_users": 25,
    "total_contacts": 150,
    "total_deals": 45,
    "open_deals_value": "$2,500,000.00"
  }
}
```

## 🔄 Pagination & Filtering

### **Pagination Format**
All list endpoints return paginated responses:
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/contacts/?page=2",
  "previous": null,
  "results": [...]
}
```

### **Default Pagination**
- Default page size: 20 items
- Maximum page size: 100 items
- Use `page_size` query parameter to customize

### **Common Search Parameters**
Most endpoints support these common parameters:
- `search` - Text search across relevant fields
- `page` - Page number
- `page_size` - Items per page
- `ordering` - Sort order (e.g., `-created_at` for newest first)

## ❌ Error Handling

### **Standard Error Response Format**
```json
{
  "detail": "Error message description",
  "code": "ERROR_CODE",
  "field_errors": {
    "field_name": ["Error message for this field"]
  }
}
```

### **Common HTTP Status Codes**
- **200 OK** - Successful request
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request data or validation errors
- **401 Unauthorized** - Authentication required or failed
- **403 Forbidden** - Insufficient permissions
- **404 Not Found** - Resource not found
- **422 Unprocessable Entity** - Validation errors
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

### **Common Error Scenarios**

**Authentication Error (401):**
```json
{
  "detail": "Authentication credentials were not provided.",
  "code": "not_authenticated"
}
```

**Validation Error (422):**
```json
{
  "detail": "Validation failed",
  "code": "validation_error",
  "field_errors": {
    "email": ["This field is required."],
    "password": ["Password must be at least 8 characters long."]
  }
}
```

**Rate Limit Error (429):**
```json
{
  "detail": "Rate limit exceeded. Try again later.",
  "code": "rate_limit_exceeded",
  "retry_after": 60
}
```

---

## 🧪 Testing Guide

### **🎯 The "No-Suffering" Testing Setup**

We've designed our testing setup to be bulletproof and frustration-free. Follow these steps EXACTLY and you'll have zero issues.

### **Critical Setup Requirements**

#### **1. Environment Variables (NON-NEGOTIABLE)**
You MUST set these environment variables before running ANY tests:

```bash
# Set the Python path to include the src directory
export PYTHONPATH=/Users/m/Desktop/crm/src

# Set Django to use test settings
export DJANGO_SETTINGS_MODULE=crm.settings_test
```

**Why this is critical**: Without these exact paths, Django can't find your project and tests will fail with confusing import errors.

#### **2. Working Directory**
Always run tests from the Django project directory:
```bash
cd src/django/crm
```

### **Testing Commands That ALWAYS Work**

#### **Unit Tests (21 tests)**
```bash
cd src/django/crm
export PYTHONPATH=/Users/m/Desktop/crm/src
export DJANGO_SETTINGS_MODULE=crm.settings_test
pytest /Users/m/Desktop/crm/tests/unit/django/ -v
```

#### **Integration Tests (30 tests)**
```bash
cd src/django/crm
export PYTHONPATH=/Users/m/Desktop/crm/src
export DJANGO_SETTINGS_MODULE=crm.settings_test
pytest /Users/m/Desktop/crm/tests/integration/ -v
```

#### **API Tests (13 tests)**
```bash
cd src/django/crm
export PYTHONPATH=/Users/m/Desktop/crm/src
export DJANGO_SETTINGS_MODULE=crm.settings_test
pytest /Users/m/Desktop/crm/tests/api/ -v
```

#### **Run All Tests (64 tests total)**
```bash
cd src/django/crm
export PYTHONPATH=/Users/m/Desktop/crm/src
export DJANGO_SETTINGS_MODULE=crm.settings_test
pytest /Users/m/Desktop/crm/tests/ -v
```

### **Test Results Breakdown**

Our test suite covers everything:

**Unit Tests (21 tests ✅)**
- User Model Tests: 6 tests (user creation, email validation, roles)
- Contact Model Tests: 6 tests (contact creation, phone validation, soft delete)
- Deal Model Tests: 6 tests (deal creation, pipeline stages, value validation)
- Activity Model Tests: 3 tests (activity creation, scheduling, completion)

**Integration Tests (30 tests ✅)**
- Basic Model Integration: 7 tests (user-contact, contact-deal, deal-activity relationships)
- API Integration Tests: 9 tests (user lifecycle, security, database transactions, performance)
- SOLID & KISS Architecture Tests: 14 tests (principles validation, code quality)

**API Tests (13 tests ✅)**
- Authentication API Tests: 3 tests (register, login, profile)
- Contact API Tests: 5 tests (create, list, detail, update, delete)
- Deal API Tests: 3 tests (create, list, update stage)
- Activity API Tests: 2 tests (create, list)

**Total: 64 tests with 100% pass rate** 🎉

### **Troubleshooting Common Issues**

#### **Issue 1: "No module named 'crm'"**
```bash
# Solution: Set the Python path correctly
export PYTHONPATH=/Users/m/Desktop/crm/src
```

#### **Issue 2: Django settings not found**
```bash
# Solution: Set Django settings module
export DJANGO_SETTINGS_MODULE=crm.settings_test
```

#### **Issue 3: Database errors**
```bash
# Solution: Use test database (SQLite in-memory)
export DJANGO_SETTINGS_MODULE=crm.settings_test
```

#### **Issue 4: Import errors**
```bash
# Solution: Run from correct directory
cd src/django/crm
```

### **Test Configuration Details**

Our test configuration (`crm/settings_test.py`) includes:
- **Database**: SQLite in-memory database for ultra-fast testing
- **Caching**: Dummy cache backend for isolation
- **Email**: Console backend for email testing
- **Logging**: Simplified logging to reduce noise
- **Debug Mode**: Enabled for detailed error reporting

### **Running Individual Tests**

#### **Run Specific Test Class**
```bash
cd src/django/crm
export PYTHONPATH=/Users/m/Desktop/crm/src
export DJANGO_SETTINGS_MODULE=crm.settings_test
pytest /Users/m/Desktop/crm/tests/unit/django/test_models.py::TestUserModel -v
```

#### **Run Specific Test Method**
```bash
cd src/django/crm
export PYTHONPATH=/Users/m/Desktop/crm/src
export DJANGO_SETTINGS_MODULE=crm.settings_test
pytest /Users/m/Desktop/crm/tests/unit/django/test_models.py::TestUserModel::test_user_creation_with_email -v
```

### **Testing Best Practices**

1. **Always set environment variables first** - This prevents 99% of testing issues
2. **Run from the correct directory** - Django needs to find manage.py
3. **Use the exact commands provided** - Don't experiment with different pytest configurations
4. **Check test output carefully** - All tests should pass with clean output
5. **Run tests before commits** - Ensure code quality and functionality

### **Performance Tips**

- Unit tests complete in ~0.2 seconds
- Integration tests complete in ~2.0 seconds
- Full test suite completes in ~2.5 seconds
- Tests run in parallel when possible with pytest's default configuration

---

## 🔧 Development Setup

### **Virtual Environment Setup**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **Development Database Setup**
```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

### **Development Server**
```bash
# Start development server
python manage.py runserver

# Start with specific port
python manage.py runserver 8080
```

### **Code Quality Tools**

#### **Code Formatting**
```bash
# Format code with Black
black .

# Organize imports with isort
isort .
```

#### **Code Linting**
```bash
# Run flake8 linting
flake8 .

# Run type checking
mypy .
```

#### **Security Scanning**
```bash
# Run security vulnerability scan
bandit -r .

# Check dependency vulnerabilities
safety check
```

---

## 🚀 Deployment

### **Production Environment Setup**

#### **Environment Variables for Production**
```bash
# Database configuration
export DATABASE_URL=postgresql://user:password@localhost:5432/crm_db

# Security settings
export SECRET_KEY=your-production-secret-key
export DEBUG=False
export ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Email configuration
export EMAIL_HOST=smtp.gmail.com
export EMAIL_PORT=587
export EMAIL_HOST_USER=your-email@gmail.com
export EMAIL_HOST_PASSWORD=your-app-password
```

#### **Production Database Migration**
```bash
# Set production settings
export DJANGO_SETTINGS_MODULE=crm.settings_production

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

### **Docker Deployment**
```bash
# Build Docker image
docker build -t crm-backend .

# Run with Docker Compose
docker-compose up -d
```

### **Monitoring & Health Checks**

Production deployment includes comprehensive monitoring:
- Health check endpoints for load balancers
- Prometheus metrics collection
- Detailed error logging and alerting
- Performance monitoring and optimization

---

## 🤝 Contributing

### **Development Workflow**

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Run tests**: `pytest tests/ -v` (ensure 100% pass rate)
4. **Commit changes**: `git commit -m 'Add amazing feature'`
5. **Push to branch**: `git push origin feature/amazing-feature`
6. **Open Pull Request**

### **Code Standards**

- Follow PEP 8 style guidelines
- Use Black for code formatting
- Write comprehensive tests for new features
- Update documentation for API changes
- Ensure all tests pass before submitting PR

### **Testing Requirements**

All contributions must maintain:
- **100% test pass rate** (64/64 tests passing)
- **95%+ test coverage**
- **SOLID principles compliance**
- **KISS principle adherence**

---

## 📞 Support & Documentation

### **Getting Help**

1. **Check this README first** - Most common questions are answered here
2. **Review the test suite** - Tests serve as usage examples
3. **Check API endpoints** - Use `/api/v1/monitoring/health/detailed/` for system status
4. **Review code comments** - Complex logic is documented inline

### **System Status**

- **API Health**: `GET /health/`
- **Detailed System Status**: `GET /api/v1/monitoring/health/detailed/`
- **Test Results**: Run the test suite to verify system integrity

---

## 📄 License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

### **What the AGPLv3 License Means**

- **✅ You can**: Use, modify, and distribute this software
- **✅ You can**: Use it for commercial purposes
- **❌ You must**: Provide the source code to any users who interact with the software over a network
- **❌ You cannot**: Use this code in proprietary software without making the entire combined work available under AGPLv3

For the full license text, see the [LICENSE](LICENSE) file in this repository.

---

## 🎯 Quick API Usage Examples

### **Complete User Workflow**
```bash
# 1. Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'

# 2. Login to get tokens
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'

# 3. Create a contact (using the access token from login)
curl -X POST http://localhost:8000/api/v1/contacts/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Jane",
    "last_name": "Smith",
    "email": "jane@company.com",
    "company": "Tech Corp"
  }'
```

### **Frontend Integration Pattern**
```javascript
// JavaScript/TypeScript example for frontend integration
class CRMClient {
  constructor(baseURL, accessToken) {
    this.baseURL = baseURL;
    this.accessToken = accessToken;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}/api/v1${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.accessToken}`,
        ...options.headers
      }
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async getContacts(page = 1, pageSize = 20) {
    return this.request(`/contacts/?page=${page}&page_size=${pageSize}`);
  }

  async createContact(contactData) {
    return this.request('/contacts/', {
      method: 'POST',
      body: JSON.stringify(contactData)
    });
  }

  async getDeals(stage = null) {
    const endpoint = stage ? `/deals/?stage=${stage}` : '/deals/';
    return this.request(endpoint);
  }

  async createDeal(dealData) {
    return this.request('/deals/', {
      method: 'POST',
      body: JSON.stringify(dealData)
    });
  }
}

// Usage example
const crm = new CRMClient('http://localhost:8000', '<access_token>');

// Get all contacts
crm.getContacts().then(contacts => {
  console.log('Contacts:', contacts.results);
});

// Create a new deal
crm.createDeal({
  title: 'New Opportunity',
  value: 50000,
  contact: 1,
  stage: 'qualified'
}).then(deal => {
  console.log('Created deal:', deal);
});
```

---

**🎉 Congratulations! You now have everything you need to successfully integrate with our CRM API and run tests without any suffering.**

*Built with ❤️ using Django, SOLID principles, and TDD methodology*