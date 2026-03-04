-- PostgreSQL + TimescaleDB Initialization Script
-- This script runs automatically when the Docker container starts

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create application user if not exists
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'stock_user') THEN
        CREATE USER stock_user WITH PASSWORD 'secure_password_123';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE stock_picking_system TO stock_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO stock_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO stock_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO stock_user;

-- Create schema
CREATE SCHEMA IF NOT EXISTS public;
GRANT USAGE ON SCHEMA public TO stock_user;

-- Log initialization
SELECT 'TimescaleDB initialized successfully' as status;
