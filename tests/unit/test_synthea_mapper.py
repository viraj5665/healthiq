"""
Unit tests for map_condition() and map_medication_request() —
the two new FHIR resource mappers added for Synthea ingestion.

Tests use synthetic fixture dicts that match Synthea's FHIR R4 bundle format.
All tests are pure (no DB, no network).

Key behaviour tested:
  - urn:uuid: reference resolution (Synthea uses these intra-bundle)
  - Patient/Encounter FK resolution (returns None when not in map)
  - Field extraction: code, system, display, dates, dosage
  - Boundary cases: missing codes, missing patient ref, null fields
"""

from datetime import timezone

import pytest

from agents.ingestion.mapper import map_condition, map_medication_request

# ── shared fixtures ────────────────────────────────────────────────────────────

PATIENT_FHIR_ID = "aaaaaaaa-0000-0000-0000-000000000001"
ENCOUNTER_FHIR_ID = "bbbbbbbb-0000-0000-0000-000000000002"
PATIENT_DB_ID = "cccccccc-0000-0000-0000-000000000003"
ENCOUNTER_DB_ID = "dddddddd-0000-0000-0000-000000000004"

# Maps covering both bare ID and urn:uuid: reference formats
PATIENT_MAP = {
    PATIENT_FHIR_ID: PATIENT_DB_ID,
    f"urn:uuid:{PATIENT_FHIR_ID}": PATIENT_DB_ID,
}
ENCOUNTER_MAP = {
    ENCOUNTER_FHIR_ID: ENCOUNTER_DB_ID,
    f"urn:uuid:{ENCOUNTER_FHIR_ID}": ENCOUNTER_DB_ID,
}


def _condition(
    subject_ref: str | None = None,
    encounter_ref: str | None = None,
    code: str = "73211009",
    system: str = "http://snomed.info/sct",
    display: str = "Diabetes mellitus (disorder)",
    clinical_status: str = "active",
    onset: str | None = "2020-01-15",
    abatement: str | None = None,
    recorded: str | None = "2020-01-15",
) -> dict:
    if subject_ref is None:
        subject_ref = f"urn:uuid:{PATIENT_FHIR_ID}"
    resource: dict = {
        "resourceType": "Condition",
        "id": "cond-001",
        "clinicalStatus": {
            "coding": [{"code": clinical_status, "system": "http://terminology.hl7.org/CodeSystem/condition-clinical"}]
        },
        "code": {
            "coding": [{"code": code, "system": system, "display": display}],
            "text": display,
        },
        "subject": {"reference": subject_ref},
        "category": [
            {"coding": [{"code": "encounter-diagnosis", "system": "http://terminology.hl7.org/CodeSystem/condition-category"}]}
        ],
    }
    if encounter_ref is not None:
        resource["encounter"] = {"reference": encounter_ref}
    if onset:
        resource["onsetDateTime"] = onset
    if abatement:
        resource["abatementDateTime"] = abatement
    if recorded:
        resource["recordedDate"] = recorded
    return resource


def _med_request(
    subject_ref: str | None = None,
    encounter_ref: str | None = None,
    med_code: str = "860975",
    med_system: str = "http://www.nlm.nih.gov/research/umls/rxnorm",
    med_display: str = "Metformin 500 MG Oral Tablet",
    status: str = "active",
    intent: str = "order",
    authored_on: str | None = "2021-03-10",
    dosage_text: str | None = "Take 1 tablet twice daily",
    dosage_route: str | None = "Oral",
    dosage_timing: str | None = "BID",
) -> dict:
    if subject_ref is None:
        subject_ref = f"urn:uuid:{PATIENT_FHIR_ID}"
    resource: dict = {
        "resourceType": "MedicationRequest",
        "id": "med-001",
        "status": status,
        "intent": intent,
        "medicationCodeableConcept": {
            "coding": [{"code": med_code, "system": med_system, "display": med_display}],
            "text": med_display,
        },
        "subject": {"reference": subject_ref},
    }
    if encounter_ref is not None:
        resource["encounter"] = {"reference": encounter_ref}
    if authored_on:
        resource["authoredOn"] = authored_on
    dosage: dict = {}
    if dosage_text:
        dosage["text"] = dosage_text
    if dosage_route:
        dosage["route"] = {"coding": [{"display": dosage_route}]}
    if dosage_timing:
        dosage["timing"] = {"code": {"text": dosage_timing}}
    if dosage:
        resource["dosageInstruction"] = [dosage]
    return resource


# ── map_condition: happy path ──────────────────────────────────────────────────

def test_condition_returns_dict():
    result = map_condition(_condition(), PATIENT_MAP, ENCOUNTER_MAP)
    assert isinstance(result, dict)


def test_condition_fhir_id():
    result = map_condition(_condition(), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["fhir_id"] == "cond-001"


def test_condition_patient_id_resolved():
    result = map_condition(_condition(), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["patient_id"] == PATIENT_DB_ID


def test_condition_urn_uuid_patient_ref():
    # Synthea uses urn:uuid: references — must resolve correctly
    ref = f"urn:uuid:{PATIENT_FHIR_ID}"
    result = map_condition(_condition(subject_ref=ref), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["patient_id"] == PATIENT_DB_ID


def test_condition_bare_patient_ref():
    # Also handle REST-style Patient/<id> references
    ref = f"Patient/{PATIENT_FHIR_ID}"
    result = map_condition(_condition(subject_ref=ref), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["patient_id"] == PATIENT_DB_ID


def test_condition_encounter_resolved():
    ref = f"urn:uuid:{ENCOUNTER_FHIR_ID}"
    result = map_condition(_condition(encounter_ref=ref), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["encounter_id"] == ENCOUNTER_DB_ID


def test_condition_encounter_optional():
    result = map_condition(_condition(encounter_ref=None), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["encounter_id"] is None


def test_condition_code():
    result = map_condition(_condition(code="73211009"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["code"] == "73211009"


def test_condition_code_system():
    result = map_condition(_condition(system="http://snomed.info/sct"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["code_system"] == "http://snomed.info/sct"


def test_condition_display():
    result = map_condition(_condition(display="Diabetes mellitus (disorder)"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["display"] == "Diabetes mellitus (disorder)"


def test_condition_clinical_status():
    result = map_condition(_condition(clinical_status="resolved"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["clinical_status"] == "resolved"


def test_condition_onset_date_parsed():
    result = map_condition(_condition(onset="2020-01-15"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["onset_date"] is not None
    assert result["onset_date"].year == 2020


def test_condition_abatement_date_parsed():
    result = map_condition(_condition(abatement="2021-06-01"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["abatement_date"] is not None
    assert result["abatement_date"].year == 2021


def test_condition_abatement_none_when_absent():
    result = map_condition(_condition(abatement=None), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["abatement_date"] is None


def test_condition_recorded_date():
    result = map_condition(_condition(recorded="2020-01-15"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["recorded_date"] is not None


def test_condition_category():
    result = map_condition(_condition(), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["category"] == "encounter-diagnosis"


# ── map_condition: None cases ─────────────────────────────────────────────────

def test_condition_returns_none_unknown_patient():
    result = map_condition(_condition(subject_ref="urn:uuid:unknown"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result is None


def test_condition_returns_none_no_code():
    resource = _condition()
    resource.pop("code")
    result = map_condition(resource, PATIENT_MAP, ENCOUNTER_MAP)
    assert result is None


def test_condition_returns_none_no_coding():
    resource = _condition()
    resource["code"] = {"text": "some condition"}  # no coding array
    result = map_condition(resource, PATIENT_MAP, ENCOUNTER_MAP)
    assert result is None


# ── map_medication_request: happy path ────────────────────────────────────────

def test_med_returns_dict():
    result = map_medication_request(_med_request(), PATIENT_MAP, ENCOUNTER_MAP)
    assert isinstance(result, dict)


def test_med_fhir_id():
    result = map_medication_request(_med_request(), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["fhir_id"] == "med-001"


def test_med_patient_id_resolved():
    result = map_medication_request(_med_request(), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["patient_id"] == PATIENT_DB_ID


def test_med_urn_uuid_patient_ref():
    ref = f"urn:uuid:{PATIENT_FHIR_ID}"
    result = map_medication_request(_med_request(subject_ref=ref), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["patient_id"] == PATIENT_DB_ID


def test_med_encounter_resolved():
    ref = f"urn:uuid:{ENCOUNTER_FHIR_ID}"
    result = map_medication_request(_med_request(encounter_ref=ref), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["encounter_id"] == ENCOUNTER_DB_ID


def test_med_encounter_optional():
    result = map_medication_request(_med_request(encounter_ref=None), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["encounter_id"] is None


def test_med_code():
    result = map_medication_request(_med_request(med_code="860975"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["medication_code"] == "860975"


def test_med_system():
    result = map_medication_request(_med_request(), PATIENT_MAP, ENCOUNTER_MAP)
    assert "rxnorm" in result["medication_system"]


def test_med_display():
    result = map_medication_request(_med_request(med_display="Metformin 500 MG Oral Tablet"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["medication_display"] == "Metformin 500 MG Oral Tablet"


def test_med_status():
    result = map_medication_request(_med_request(status="stopped"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["status"] == "stopped"


def test_med_intent():
    result = map_medication_request(_med_request(intent="plan"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["intent"] == "plan"


def test_med_authored_on_parsed():
    result = map_medication_request(_med_request(authored_on="2021-03-10"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["authored_on"] is not None
    assert result["authored_on"].year == 2021


def test_med_authored_on_none():
    result = map_medication_request(_med_request(authored_on=None), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["authored_on"] is None


def test_med_dosage_text():
    result = map_medication_request(_med_request(dosage_text="Take with food"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["dosage_text"] == "Take with food"


def test_med_dosage_route():
    result = map_medication_request(_med_request(dosage_route="Oral"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["dosage_route"] == "Oral"


def test_med_dosage_timing():
    result = map_medication_request(_med_request(dosage_timing="BID"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result["dosage_timing"] == "BID"


def test_med_dosage_fields_none_when_absent():
    resource = _med_request()
    resource.pop("dosageInstruction", None)
    result = map_medication_request(resource, PATIENT_MAP, ENCOUNTER_MAP)
    assert result["dosage_text"] is None
    assert result["dosage_route"] is None
    assert result["dosage_timing"] is None


# ── map_medication_request: None cases ────────────────────────────────────────

def test_med_returns_none_unknown_patient():
    result = map_medication_request(_med_request(subject_ref="urn:uuid:unknown"), PATIENT_MAP, ENCOUNTER_MAP)
    assert result is None


def test_med_returns_none_no_medication_code():
    resource = _med_request()
    resource.pop("medicationCodeableConcept")
    result = map_medication_request(resource, PATIENT_MAP, ENCOUNTER_MAP)
    assert result is None


def test_med_dosage_route_truncated_at_128():
    long_route = "x" * 200
    result = map_medication_request(_med_request(dosage_route=long_route), PATIENT_MAP, ENCOUNTER_MAP)
    assert len(result["dosage_route"]) == 128


def test_med_dosage_timing_truncated_at_64():
    long_timing = "y" * 100
    result = map_medication_request(_med_request(dosage_timing=long_timing), PATIENT_MAP, ENCOUNTER_MAP)
    assert len(result["dosage_timing"]) == 64
