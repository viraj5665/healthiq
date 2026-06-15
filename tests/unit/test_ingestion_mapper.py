"""
Unit tests for the FHIR → DB mapping layer.

No database or network calls — mapper functions are pure Python.
"""

from datetime import date, datetime, timezone

import pytest

from agents.ingestion.mapper import map_encounter, map_observation, map_patient
from agents.ingestion.phi import hash_identifier

# ── fixtures ──────────────────────────────────────────────────────────────────

PATIENT = {
    "resourceType": "Patient",
    "id": "test-patient-001",
    "active": True,
    "name": [{"use": "official", "family": "Smith", "given": ["John", "A"]}],
    "gender": "male",
    "birthDate": "1985-03-15",
    "identifier": [
        {"system": "http://hospital.example/mrn", "value": "MRN001",
         "type": {"coding": [{"code": "MR"}]}}
    ],
    "address": [
        {"line": ["123 Main St"], "city": "Springfield", "state": "IL", "postalCode": "62701"}
    ],
    "telecom": [
        {"system": "phone", "value": "555-0100"},
        {"system": "email", "value": "john@example.com"},
    ],
}

ENCOUNTER = {
    "resourceType": "Encounter",
    "id": "test-encounter-001",
    "status": "finished",
    "class": {"code": "AMB", "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode"},
    "type": [{"coding": [{"code": "11429006", "display": "Consultation"}]}],
    "subject": {"reference": "Patient/test-patient-001"},
    "period": {"start": "2024-01-15T09:00:00Z", "end": "2024-01-15T10:00:00Z"},
    "reasonCode": [{"coding": [{"code": "195967001", "display": "Asthma"}]}],
    "location": [{"location": {"reference": "Location/1", "display": "Clinic A"}}],
    "participant": [{"individual": {"reference": "Practitioner/prac-001"}}],
}

OBSERVATION = {
    "resourceType": "Observation",
    "id": "test-obs-001",
    "status": "final",
    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                               "code": "vital-signs"}]}],
    "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6",
                          "display": "Systolic blood pressure"}]},
    "subject": {"reference": "Patient/test-patient-001"},
    "encounter": {"reference": "Encounter/test-encounter-001"},
    "effectiveDateTime": "2024-01-15T09:30:00Z",
    "valueQuantity": {"value": 120.0, "unit": "mmHg"},
    "referenceRange": [{"low": {"value": 90.0}, "high": {"value": 140.0}}],
    "interpretation": [{"coding": [{"code": "N", "display": "Normal"}]}],
}

# ── patient mapping ────────────────────────────────────────────────────────────

def test_map_patient_fhir_id():
    assert map_patient(PATIENT)["fhir_id"] == "test-patient-001"


def test_map_patient_demographics():
    row = map_patient(PATIENT)
    assert row["gender"] == "male"
    assert row["birth_date"] == date(1985, 3, 15)
    assert row["active"] is True


def test_map_patient_city_state_kept():
    row = map_patient(PATIENT)
    assert row["city"] == "Springfield"
    assert row["state"] == "IL"


def test_map_patient_names_are_hashed():
    row = map_patient(PATIENT)
    assert row["first_name"] != "John A"
    assert row["first_name"].startswith("PHI_")
    assert row["last_name"] != "Smith"
    assert row["last_name"].startswith("PHI_")


def test_map_patient_mrn_hashed():
    row = map_patient(PATIENT)
    assert row["mrn"] is not None
    assert row["mrn"].startswith("PHI_")
    assert "MRN001" not in row["mrn"]


def test_map_patient_contact_stripped():
    row = map_patient(PATIENT)
    assert row["address_line"] is None
    assert row["postal_code"] is None
    assert row["phone"] is None
    assert row["email"] is None


def test_map_patient_phi_is_deterministic():
    """Same input must yield same hash across calls."""
    r1 = map_patient(PATIENT)
    r2 = map_patient(PATIENT)
    assert r1["first_name"] == r2["first_name"]
    assert r1["last_name"] == r2["last_name"]


def test_map_patient_missing_name_defaults():
    row = map_patient({**PATIENT, "name": []})
    assert row["first_name"] == "UNKNOWN"
    assert row["last_name"] == "UNKNOWN"


def test_map_patient_bad_birth_date_defaults():
    row = map_patient({**PATIENT, "birthDate": "not-a-date"})
    assert row["birth_date"] == date(1900, 1, 1)


# ── encounter mapping ─────────────────────────────────────────────────────────

def test_map_encounter_basic():
    patient_map = {"test-patient-001": "db-uuid-001"}
    row = map_encounter(ENCOUNTER, patient_map)
    assert row is not None
    assert row["fhir_id"] == "test-encounter-001"
    assert row["status"] == "finished"
    assert row["class_code"] == "AMB"
    assert row["patient_id"] == "db-uuid-001"


def test_map_encounter_type_and_reason():
    row = map_encounter(ENCOUNTER, {"test-patient-001": "db-uuid-001"})
    assert row["type_code"] == "11429006"
    assert row["type_display"] == "Consultation"
    assert row["reason_code"] == "195967001"
    assert row["reason_display"] == "Asthma"


def test_map_encounter_period():
    row = map_encounter(ENCOUNTER, {"test-patient-001": "db-uuid-001"})
    assert row["start_time"] == datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)
    assert row["end_time"] == datetime(2024, 1, 15, 10, 0, tzinfo=timezone.utc)


def test_map_encounter_practitioner():
    row = map_encounter(ENCOUNTER, {"test-patient-001": "db-uuid-001"})
    assert row["practitioner_id"] == "prac-001"


def test_map_encounter_returns_none_for_unknown_patient():
    assert map_encounter(ENCOUNTER, {}) is None


def test_map_encounter_returns_none_for_missing_patient_ref():
    enc = {**ENCOUNTER, "subject": {}}
    assert map_encounter(enc, {"test-patient-001": "db-uuid-001"}) is None


# ── observation mapping ────────────────────────────────────────────────────────

def test_map_observation_basic():
    patient_map = {"test-patient-001": "p-uuid"}
    encounter_map = {"test-encounter-001": "e-uuid"}
    row = map_observation(OBSERVATION, patient_map, encounter_map)
    assert row is not None
    assert row["fhir_id"] == "test-obs-001"
    assert row["code"] == "8480-6"
    assert row["code_system"] == "http://loinc.org"
    assert row["display"] == "Systolic blood pressure"


def test_map_observation_value():
    row = map_observation(OBSERVATION, {"test-patient-001": "p-uuid"}, {})
    assert row["value_quantity"] == 120.0
    assert row["value_unit"] == "mmHg"


def test_map_observation_reference_range():
    row = map_observation(OBSERVATION, {"test-patient-001": "p-uuid"}, {})
    assert row["reference_low"] == 90.0
    assert row["reference_high"] == 140.0


def test_map_observation_interpretation():
    row = map_observation(OBSERVATION, {"test-patient-001": "p-uuid"}, {})
    assert row["interpretation"] == "N"


def test_map_observation_category():
    row = map_observation(OBSERVATION, {"test-patient-001": "p-uuid"}, {})
    assert row["category"] == "vital-signs"


def test_map_observation_links_encounter():
    row = map_observation(OBSERVATION, {"test-patient-001": "p-uuid"}, {"test-encounter-001": "e-uuid"})
    assert row["encounter_id"] == "e-uuid"


def test_map_observation_encounter_optional():
    row = map_observation(OBSERVATION, {"test-patient-001": "p-uuid"}, {})
    assert row["encounter_id"] is None


def test_map_observation_returns_none_unknown_patient():
    assert map_observation(OBSERVATION, {}, {}) is None


def test_map_observation_returns_none_no_code():
    obs = {**OBSERVATION, "code": {}}
    assert map_observation(obs, {"test-patient-001": "p-uuid"}, {}) is None


def test_map_observation_effective_time_parsed():
    row = map_observation(OBSERVATION, {"test-patient-001": "p-uuid"}, {})
    assert row["effective_time"] == datetime(2024, 1, 15, 9, 30, tzinfo=timezone.utc)


def test_map_observation_effective_time_defaults_to_now_when_missing():
    obs = {k: v for k, v in OBSERVATION.items() if k != "effectiveDateTime"}
    row = map_observation(obs, {"test-patient-001": "p-uuid"}, {})
    assert row is not None
    assert isinstance(row["effective_time"], datetime)


def test_map_observation_value_string():
    obs = {**OBSERVATION}
    obs.pop("valueQuantity", None)
    obs["valueString"] = "Positive"
    row = map_observation(obs, {"test-patient-001": "p-uuid"}, {})
    assert row["value_string"] == "Positive"
    assert row["value_quantity"] is None


# ── phi helpers ────────────────────────────────────────────────────────────────

def test_hash_identifier_none_input():
    assert hash_identifier(None) is None


def test_hash_identifier_empty_string():
    assert hash_identifier("") is None


def test_hash_identifier_format():
    result = hash_identifier("John Smith")
    assert result.startswith("PHI_")
    assert len(result) == 24  # "PHI_" + 20 hex chars


def test_hash_identifier_deterministic():
    assert hash_identifier("test") == hash_identifier("test")


def test_hash_identifier_different_inputs_differ():
    assert hash_identifier("Alice") != hash_identifier("Bob")
