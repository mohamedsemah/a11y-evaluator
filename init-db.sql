-- Database initialization script for LLM Analyzer
-- This ensures proper setup and prevents foreign key constraint issues

-- Create database if it doesn't exist (PostgreSQL Docker image handles this via POSTGRES_DB)
-- But we can ensure extensions are available

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a function to generate UUIDs consistently
CREATE OR REPLACE FUNCTION generate_uuid() RETURNS UUID AS $$
BEGIN
    RETURN uuid_generate_v4();
END;
$$ LANGUAGE plpgsql;

-- Ensure proper permissions
GRANT ALL PRIVILEGES ON DATABASE llm_analyzer TO postgres;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database llm_analyzer initialized successfully';
    RAISE NOTICE 'UUID extension enabled';
    RAISE NOTICE 'Ready for table creation';
END $$;