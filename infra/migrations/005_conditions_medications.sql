-- Migration 005: Conditions + MedicationRequests tables (from Synthea FHIR bundles)

-- ── Conditions ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS conditions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fhir_id         VARCHAR(64) UNIQUE,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    encounter_id    UUID REFERENCES encounters(id) ON DELETE SET NULL,
    clinical_status VARCHAR(32),
    code            VARCHAR(64) NOT NULL,
    code_system     VARCHAR(128),
    display         VARCHAR(512),
    category        VARCHAR(64),
    onset_date      TIMESTAMPTZ,
    abatement_date  TIMESTAMPTZ,
    recorded_date   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conditions_patient ON conditions(patient_id);
CREATE INDEX IF NOT EXISTS idx_conditions_code    ON conditions(code);
CREATE INDEX IF NOT EXISTS idx_conditions_status  ON conditions(clinical_status);

-- ── Medication Requests ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS medication_requests (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fhir_id             VARCHAR(64) UNIQUE,
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    encounter_id        UUID REFERENCES encounters(id) ON DELETE SET NULL,
    status              VARCHAR(32),
    intent              VARCHAR(32),
    medication_code     VARCHAR(64) NOT NULL,
    medication_system   VARCHAR(128),
    medication_display  VARCHAR(512),
    authored_on         TIMESTAMPTZ,
    dosage_text         TEXT,
    dosage_route        VARCHAR(128),
    dosage_timing       VARCHAR(64),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_med_requests_patient ON medication_requests(patient_id);
CREATE INDEX IF NOT EXISTS idx_med_requests_code    ON medication_requests(medication_code);
CREATE INDEX IF NOT EXISTS idx_med_requests_status  ON medication_requests(status);
