-- Step 3a: a read-only database user for the AI assistant.
-- It can only SELECT from the analytics schema. It cannot see raw or staging, and cannot write anything.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'assistant_ro') THEN
        CREATE ROLE assistant_ro LOGIN PASSWORD 'assistant_pw';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE firewall TO assistant_ro;
GRANT USAGE ON SCHEMA analytics TO assistant_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO assistant_ro;

-- Tables are dropped and rebuilt on every pipeline run, so grant on future tables too
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO assistant_ro;

REVOKE ALL ON SCHEMA raw FROM assistant_ro;
REVOKE ALL ON SCHEMA staging FROM assistant_ro;

-- Safety limits that apply to every session of this user
ALTER ROLE assistant_ro SET default_transaction_read_only = on;
ALTER ROLE assistant_ro SET statement_timeout = '5s';
ALTER ROLE assistant_ro SET search_path = analytics;
