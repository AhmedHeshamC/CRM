#!/bin/bash

# PostgreSQL Setup Script for CRM Testing
# This script sets up PostgreSQL for the CRM project

echo "🐘 Setting up PostgreSQL for CRM Testing..."

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo "⚠️  PostgreSQL is not running. Please start PostgreSQL service first:"
    echo "   sudo systemctl start postgresql"
    echo "   sudo systemctl enable postgresql"
    exit 1
fi

# Database configuration
DB_NAME="crm_test_db"
DB_USER="crm_test_user"
DB_PASSWORD="crm_test_password"

echo "📋 Database Configuration:"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo "   Host: localhost"
echo "   Port: 5432"

# Create database user
echo "👤 Creating database user..."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "   User $DB_USER already exists"

# Create database
echo "🗄️  Creating database..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "   Database $DB_NAME already exists"

# Grant privileges
echo "🔐 Granting privileges..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Test connection
echo "🔗 Testing database connection..."
if PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME -c "SELECT version();" > /dev/null 2>&1; then
    echo "✅ Database connection successful!"
else
    echo "❌ Database connection failed!"
    exit 1
fi

# Update .env file for PostgreSQL
echo "📝 Updating .env file for PostgreSQL..."
sed -i 's/USE_SQLITE=True/USE_SQLITE=False/' .env
sed -i 's/DB_NAME=crm_test_db.sqlite3/DB_NAME=crm_test_db/' .env

# Uncomment PostgreSQL settings
sed -i 's/# USE_SQLITE=False/# USE_SQLITE=False/' .env
sed -i 's/# DB_NAME=crm_test_db/DB_NAME=crm_test_db/' .env
sed -i 's/# DB_USER=crm_test_user/DB_USER=crm_test_user/' .env
sed -i 's/# DB_PASSWORD=crm_test_password/DB_PASSWORD=crm_test_password/' .env
sed -i 's/# DB_HOST=localhost/DB_HOST=localhost/' .env
sed -i 's/# DB_PORT=5432/DB_PORT=5432/' .env

# Comment out SQLite settings
sed -i 's/DB_NAME=crm_test_db.sqlite3/# DB_NAME=crm_test_db.sqlite3/' .env

echo "✅ PostgreSQL setup completed!"
echo ""
echo "🎯 Next steps:"
echo "   1. Run 'python manage.py makemigrations'"
echo "   2. Run 'python manage.py migrate'"
echo "   3. Run 'python manage.py test'"
echo ""
echo "🔄 To switch back to SQLite:"
echo "   Edit .env file and set USE_SQLITE=True"