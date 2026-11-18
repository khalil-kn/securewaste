-- SCRUM-45: make risk optional and add server-side employee attribution.

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
--
-- Apply AFTER 000_schema_migrations.sql. Idempotent: safe to re-run.
-- Existing rows keep their risk value; rows without identity get NULL (unattributed).
-- Never fabricates employee attribution for historical records.

-- 1. risk becomes nullable (overall risk deferred to Sprint 4).
-- Guarded so the migration is repeatable (idempotent).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'scan_events'
          AND column_name = 'risk'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE scan_events ALTER COLUMN risk DROP NOT NULL;
    END IF;
END $$;

-- Replace the old strict check constraint with a nullable-aware one.
ALTER TABLE scan_events
    DROP CONSTRAINT IF EXISTS scan_events_risk_check;
ALTER TABLE scan_events
    ADD CONSTRAINT scan_events_risk_check
    CHECK (risk IS NULL OR risk IN ('Low', 'Medium', 'High'));

-- 2. Add employee_id (nullable, populated server-side from verified auth).
ALTER TABLE scan_events
    ADD COLUMN IF NOT EXISTS employee_id UUID;

-- 3. Index for owner-scoped reads.
CREATE INDEX IF NOT EXISTS scan_events_employee_id_idx
    ON scan_events (employee_id);

-- Record this migration.
INSERT INTO schema_migrations (version)
VALUES ('001_scrum45_employee_and_nullable_risk')
ON CONFLICT (version) DO NOTHING;