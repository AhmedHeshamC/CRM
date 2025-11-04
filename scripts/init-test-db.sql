-- Initialize test database for CI/CD pipeline
-- Following SOLID principles for database configuration

-- Set database parameters for testing
ALTER DATABASE crm_test SET timezone TO 'UTC';
ALTER DATABASE crm_test SET statement_timeout TO '30000';

-- Create test-specific extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE crm_test TO crm_test;
GRANT ALL PRIVILEGES ON SCHEMA public TO crm_test;

-- Create test indexes for performance (optional)
-- These can help speed up test execution

COMMIT;