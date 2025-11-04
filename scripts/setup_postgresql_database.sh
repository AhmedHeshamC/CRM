#!/bin/bash
# PostgreSQL Database Setup Script for CRM Project
# Following SOLID and KISS principles
# Single Responsibility: Database initialization

set -e  # Exit on any error

# Default configuration
DB_NAME=${DB_NAME:-"crm_db"}
DB_USER=${DB_USER:-"crm_user"}
DB_PASSWORD=${DB_PASSWORD:-"crm_password"}
DB_HOST=${DB_HOST:-"localhost"}
DB_PORT=${DB_PORT:-"5432"}
POSTGRES_USER=${POSTGRES_USER:-"postgres"}

echo "🚀 Setting up PostgreSQL database for CRM Project..."
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $DB_HOST:$DB_PORT"

# Function to check if PostgreSQL is running
check_postgres() {
    pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" > /dev/null 2>&1
}

# Function to create database and user
setup_database() {
    echo "📦 Creating database and user..."

    # Create database user
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -c "
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
                CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD';
            END IF;
        END
        \$\$;
    " || {
        echo "❌ Failed to create database user"
        exit 1
    }

    # Create database
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -c "
        SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec
    " || {
        echo "❌ Failed to create database"
        exit 1
    }

    # Grant privileges
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$POSTGRES_USER" -c "
        GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
    " || {
        echo "❌ Failed to grant privileges"
        exit 1
    }

    echo "✅ Database setup completed successfully!"
}

# Function to run Django migrations
run_migrations() {
    echo "🔄 Running Django migrations..."

    cd /Users/m/Desktop/crm/src/django/crm
    export PYTHONPATH="/Users/m/Desktop/crm/src"
    export DJANGO_SETTINGS_MODULE="crm.settings_production"

    python manage.py migrate --noinput || {
        echo "❌ Migration failed"
        exit 1
    }

    echo "✅ Migrations completed successfully!"
}

# Function to create superuser (optional)
create_superuser() {
    if [ "$CREATE_SUPERUSER" = "true" ]; then
        echo "👤 Creating Django superuser..."

        python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@crm.com').exists():
    User.objects.create_superuser(
        email='admin@crm.com',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    print('Superuser created successfully')
else:
    print('Superuser already exists')
EOF
    fi
}

# Function to test database connection
test_connection() {
    echo "🔍 Testing database connection..."

    python manage.py shell << EOF
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT version()')
        version = cursor.fetchone()[0]
        print(f'✅ Database connection successful!')
        print(f'PostgreSQL version: {version}')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
EOF
}

# Main execution
main() {
    echo "🎯 Starting PostgreSQL database setup..."

    # Check if PostgreSQL is running
    if ! check_postgres; then
        echo "❌ PostgreSQL is not running or not accessible"
        echo "Please start PostgreSQL service and try again"
        exit 1
    fi

    # Setup database and user
    setup_database

    # Run migrations
    run_migrations

    # Create superuser if requested
    create_superuser

    # Test connection
    test_connection

    echo ""
    echo "🎉 PostgreSQL database setup completed successfully!"
    echo ""
    echo "📋 Connection Details:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo ""
    echo "🔧 Environment Variables:"
    echo "  export DB_NAME=\"$DB_NAME\""
    echo "  export DB_USER=\"$DB_USER\""
    echo "  export DB_PASSWORD=\"$DB_PASSWORD\""
    echo "  export DB_HOST=\"$DB_HOST\""
    echo "  export DB_PORT=\"$DB_PORT\""
    echo ""
    echo "🚀 You can now start the CRM application!"
}

# Run main function
main "$@"