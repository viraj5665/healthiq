-- HealthIQ Core Schema — FHIR R4 aligned
-- Run once on first container start via docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- fuzzy text search on names

-- ── Patients ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fhir_id         VARCHAR(64) UNIQUE,               -- FHIR resource id
    mrn             VARCHAR(32) UNIQUE,               -- Medical Record Number
    first_name      VARCHAR(128) NOT NULL,
    last_name       VARCHAR(128) NOT NULL,
    birth_date      DATE NOT NULL,
    gender          VARCHAR(16),                      -- FHIR gender codes
    race            VARCHAR(64),
    ethnicity       VARCHAR(64),
    address_line    VARCHAR(256),
    city            VARCHAR(128),
    state           VARCHAR(2),
    postal_code     VARCHAR(10),
    phone           VARCHAR(20),
    email           VARCHAR(256),
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_patients_mrn       ON patients(mrn);
CREATE INDEX IF NOT EXISTS idx_patients_last_name ON patients USING gin(last_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_patients_birth     ON patients(birth_date);

-- ── Encounters ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS encounters (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fhir_id         VARCHAR(64) UNIQUE,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    status          VARCHAR(32) NOT NULL,             -- planned|arrived|in-progress|finished|cancelled
    class_code      VARCHAR(32),                      -- AMB|EMER|IMP|SS|VR
    type_code       VARCHAR(64),
    type_display    VARCHAR(256),
    start_time      TIMESTAMPTZ,
    end_time        TIMESTAMPTZ,
    reason_code     VARCHAR(64),
    reason_display  VARCHAR(256),
    location        VARCHAR(256),
    practitioner_id VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_encounters_patient   ON encounters(patient_id);
CREATE INDEX IF NOT EXISTS idx_encounters_status    ON encounters(status);
CREATE INDEX IF NOT EXISTS idx_encounters_start     ON encounters(start_time DESC);

-- ── Observations ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS observations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fhir_id         VARCHAR(64) UNIQUE,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    encounter_id    UUID REFERENCES encounters(id) ON DELETE SET NULL,
    status          VARCHAR(32) NOT NULL,             -- registered|preliminary|final|amended
    category        VARCHAR(64),                      -- vital-signs|laboratory|imaging|...
    code_system     VARCHAR(128),                     -- LOINC, SNOMED
    code            VARCHAR(64) NOT NULL,
    display         VARCHAR(256),
    value_quantity  NUMERIC,
    value_unit      VARCHAR(32),
    value_string    TEXT,
    value_boolean   BOOLEAN,
    reference_low   NUMERIC,
    reference_high  NUMERIC,
    interpretation  VARCHAR(32),                      -- H|L|N|A|AA
    effective_time  TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_observations_patient   ON observations(patient_id);
CREATE INDEX IF NOT EXISTS idx_observations_encounter ON observations(encounter_id);
CREATE INDEX IF NOT EXISTS idx_observations_code      ON observations(code);
CREATE INDEX IF NOT EXISTS idx_observations_time      ON observations(effective_time DESC);
CREATE INDEX IF NOT EXISTS idx_observations_category  ON observations(category);

-- ── Risk Scores ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_scores (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    score_type      VARCHAR(64) NOT NULL,             -- readmission|sepsis|deterioration|...
    score           NUMERIC(5,4) NOT NULL,            -- 0.0000–1.0000
    risk_level      VARCHAR(16) NOT NULL,             -- low|moderate|high|critical
    model_version   VARCHAR(32),
    features        JSONB,                            -- feature vector snapshot
    explanation     JSONB,                            -- SHAP values or similar
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    encounter_id    UUID REFERENCES encounters(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_risk_scores_patient   ON risk_scores(patient_id);
CREATE INDEX IF NOT EXISTS idx_risk_scores_type      ON risk_scores(score_type);
CREATE INDEX IF NOT EXISTS idx_risk_scores_level     ON risk_scores(risk_level);
CREATE INDEX IF NOT EXISTS idx_risk_scores_computed  ON risk_scores(computed_at DESC);

-- ── Alerts ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    encounter_id    UUID REFERENCES encounters(id) ON DELETE SET NULL,
    risk_score_id   UUID REFERENCES risk_scores(id) ON DELETE SET NULL,
    alert_type      VARCHAR(64) NOT NULL,             -- risk-threshold|vital-sign|lab-critical|...
    severity        VARCHAR(16) NOT NULL,             -- info|warning|critical
    title           VARCHAR(256) NOT NULL,
    message         TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'active',  -- active|acknowledged|resolved|dismissed
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(128),
    resolved_at     TIMESTAMPTZ,
    metadata        JSONB
);

CREATE INDEX IF NOT EXISTS idx_alerts_patient   ON alerts(patient_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status    ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity  ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered ON alerts(triggered_at DESC);

-- ── Updated-at trigger ────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_patients_updated_at ON patients;
CREATE TRIGGER trg_patients_updated_at
    BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trg_encounters_updated_at ON encounters;
CREATE TRIGGER trg_encounters_updated_at
    BEFORE UPDATE ON encounters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
