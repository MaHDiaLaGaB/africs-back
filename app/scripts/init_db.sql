-- Create admin and user roles if they don't exist
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin') THEN
        CREATE ROLE admin WITH LOGIN SUPERUSER PASSWORD 'postgres';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'postgres';
    END IF;
END
$$;

-- Create the database (not in a DO block)
-- Replace 'wasata_db' if needed
SELECT 'CREATE DATABASE wasata_db OWNER admin'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = 'wasata_db'
)\gexec
