-- Bootstrap script executed by the postgres image on first start.
-- Creates one role + one schema per service and grants ownership.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'auth_user') THEN
        CREATE ROLE auth_user LOGIN PASSWORD 'auth_pass_change_me';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'users_user') THEN
        CREATE ROLE users_user LOGIN PASSWORD 'users_pass_change_me';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tests_user') THEN
        CREATE ROLE tests_user LOGIN PASSWORD 'tests_pass_change_me';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'llm_user') THEN
        CREATE ROLE llm_user LOGIN PASSWORD 'llm_pass_change_me';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'reports_user') THEN
        CREATE ROLE reports_user LOGIN PASSWORD 'reports_pass_change_me';
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS auth    AUTHORIZATION auth_user;
CREATE SCHEMA IF NOT EXISTS users   AUTHORIZATION users_user;
CREATE SCHEMA IF NOT EXISTS tests   AUTHORIZATION tests_user;
CREATE SCHEMA IF NOT EXISTS llm     AUTHORIZATION llm_user;
CREATE SCHEMA IF NOT EXISTS reports AUTHORIZATION reports_user;

GRANT CONNECT ON DATABASE education TO auth_user, users_user, tests_user, llm_user, reports_user;

-- Each role can only access its own schema.
GRANT ALL ON SCHEMA auth    TO auth_user;
GRANT ALL ON SCHEMA users   TO users_user;
GRANT ALL ON SCHEMA tests   TO tests_user;
GRANT ALL ON SCHEMA llm     TO llm_user;
GRANT ALL ON SCHEMA reports TO reports_user;
