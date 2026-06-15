-- Migration 004: Reports table for Reporting Agent output
CREATE TABLE IF NOT EXISTS reports (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    report_markdown  TEXT NOT NULL,
    summary_data     JSONB NOT NULL,
    model_version    VARCHAR(64),
    duration_seconds NUMERIC(6, 2)
);

CREATE INDEX IF NOT EXISTS idx_reports_generated ON reports(generated_at DESC);
