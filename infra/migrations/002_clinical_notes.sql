-- Migration 002: clinical notes + NLP extraction storage
-- Run with: docker exec healthiq_db psql -U healthiq -d healthiq_db -f /migrations/002_clinical_notes.sql

CREATE TABLE IF NOT EXISTS clinical_notes (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id       UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    note_type        VARCHAR(64) NOT NULL DEFAULT 'progress_note',
    note_date        TIMESTAMPTZ,
    note_text        TEXT NOT NULL,
    is_synthetic     BOOLEAN NOT NULL DEFAULT FALSE,
    extracted_entities JSONB,          -- NLP Agent output
    extraction_model VARCHAR(64),      -- model that produced extraction
    extracted_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clinical_notes_patient ON clinical_notes(patient_id);
CREATE INDEX IF NOT EXISTS idx_clinical_notes_date    ON clinical_notes(note_date DESC);
CREATE INDEX IF NOT EXISTS idx_clinical_notes_synth   ON clinical_notes(is_synthetic);
