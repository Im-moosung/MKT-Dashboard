-- App schema bootstrap (idempotent)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Drizzle will own table DDL. This file only bootstraps DB/extensions.
