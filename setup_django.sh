#!/bin/bash

# Django Setup Script for CRM Project
# This script sets up the Django environment and runs initial migrations

echo "🚀 Setting up Django CRM Project..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "📋 Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo "✅ Virtual environment created successfully"
    else
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing requirements..."
pip install -r requirements.txt
if [ $? -eq 0 ]; then
    echo "✅ Requirements installed successfully"
else
    echo "❌ Failed to install requirements"
    exit 1
fi

# Change to Django project directory
echo "📂 Changing to Django project directory..."
cd src/django/crm

# Check Django configuration
echo "🔍 Checking Django configuration..."
python manage.py check
if [ $? -eq 0 ]; then
    echo "✅ Django configuration is valid"
else
    echo "⚠️  Django configuration has warnings (this may be expected)"
fi

# Create migrations
echo "🔧 Creating migrations..."
python manage.py makemigrations
if [ $? -eq 0 ]; then
    echo "✅ Migrations created successfully"
else
    echo "⚠️  Migration creation had issues (this may be expected)"
fi

# Apply migrations
echo "🗄️  Applying migrations..."
python manage.py migrate
if [ $? -eq 0 ]; then
    echo "✅ Migrations applied successfully"
else
    echo "❌ Failed to apply migrations"
    exit 1
fi

# Create superuser (optional)
echo "👤 Do you want to create a superuser? (y/n)"
read -r create_superuser
if [ "$create_superuser" = "y" ] || [ "$create_superuser" = "Y" ]; then
    python manage.py createsuperuser
fi

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput
if [ $? -eq 0 ]; then
    echo "✅ Static files collected successfully"
else
    echo "⚠️  Static files collection had issues"
fi

# Run Django checks
echo "🔍 Running final Django checks..."
python manage.py check --deploy
if [ $? -eq 0 ]; then
    echo "✅ Django is ready for deployment"
else
    echo "⚠️  Django has deployment warnings"
fi

# Test server
echo "🌐 Do you want to start the development server? (y/n)"
read -r start_server
if [ "$start_server" = "y" ] || [ "$start_server" = "Y" ]; then
    echo "🚀 Starting development server on http://127.0.0.1:8000"
    echo "📖 API Documentation: http://127.0.0.1:8000/api/docs/"
    echo "🔧 Admin Interface: http://127.0.0.1:8000/admin/"
    echo "❤️  Health Check: http://127.0.0.1:8000/health/"
    echo ""
    echo "Press Ctrl+C to stop the server"
    python manage.py runserver 0.0.0.0:8000
fi

echo ""
echo "🎉 Django CRM setup completed!"
echo ""
echo "📋 Quick Start Commands:"
echo "   Activate virtual environment: source venv/bin/activate"
echo "   Run development server: cd src/django/crm && python manage.py runserver"
echo "   Create superuser: python manage.py createsuperuser"
echo "   Run tests: python manage.py test"
echo "   Collect static files: python manage.py collectstatic"
echo ""
echo "🔗 Useful URLs:"
echo "   API Documentation: http://127.0.0.1:8000/api/docs/"
echo "   Admin Interface: http://127.0.0.1:8000/admin/"
echo "   Health Check: http://127.0.0.1:8000/health/"
echo "   API Schema: http://127.0.0.1:8000/api/v1/schema/"