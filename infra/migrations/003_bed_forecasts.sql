-- Migration 003: Bed Forecasts + patch alerts.patient_id to allow NULLs
-- Run manually: docker cp + docker exec psql -f 003_bed_forecasts.sql healthiq_db

-- Allow NULL patient_id so the Alert Agent can create system-level alerts
-- (e.g. bed-capacity) that are not tied to a specific patient.
ALTER TABLE alerts ALTER COLUMN patient_id DROP NOT NULL;

-- ── Bed Forecasts ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bed_forecasts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    forecast_date       DATE NOT NULL,
    predicted_occupancy NUMERIC(6, 2) NOT NULL,
    capacity            INTEGER NOT NULL DEFAULT 20,
    status              VARCHAR(16) NOT NULL DEFAULT 'normal',  -- normal|warning|critical
    model_method        VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_bed_forecasts_date ON bed_forecasts(forecast_date);
CREATE INDEX IF NOT EXISTS idx_bed_forecasts_status ON bed_forecasts(status);
