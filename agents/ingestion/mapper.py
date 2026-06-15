"""
FHIR R4 resource → HealthIQ DB row mappers.

All functions are pure (no DB, no network) so they are straightforward to
unit-test with fixture dicts.
"""

from datetime import date, datetime, timezone
from typing import Any

from agents.ingestion.phi import hash_identifier


def _get(obj: Any, *keys, default=None) -> Any:
    for key in keys:
        if not isinstance(obj, (dict, list)):
            return default
        if isinstance(obj, list):
            try:
                obj = obj[int(key)]
            except (IndexError, ValueError, TypeError):
                return default
        else:
            obj = obj.get(key, default)
            if obj is default:
                return default
    return obj


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # Bare date fallback
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def map_patient(resource: dict) -> dict:
    """FHIR Patient → patients table row dict."""
    fhir_id = resource.get("id", "")

    # Name — pick "official" use first, fall back to first entry
    names = resource.get("name", [])
    name = next((n for n in names if n.get("use") == "official"), names[0] if names else {})
    given_raw = " ".join(name.get("given", []))
    family_raw = name.get("family", "")

    # MRN — look for MRN-type identifier
    mrn_raw = None
    for ident in resource.get("identifier", []):
        system = ident.get("system", "").lower()
        type_code = _get(ident, "type", "coding", 0, "code", default="").lower()
        if "mrn" in system or "mr" in type_code or "medical" in system:
            mrn_raw = ident.get("value")
            break

    # Address — city/state kept for geo analytics; line/zip stripped
    addr = resource.get("address", [{}])[0] if resource.get("address") else {}
    state_raw = (addr.get("state") or "")[:2] or None

    # Race / ethnicity from US Core extensions
    race, ethnicity = None, None
    for ext in resource.get("extension", []):
        url = ext.get("url", "")
        if "race" in url:
            for inner in ext.get("extension", []):
                if inner.get("url") == "text":
                    race = inner.get("valueString")
        elif "ethnicity" in url:
            for inner in ext.get("extension", []):
                if inner.get("url") == "text":
                    ethnicity = inner.get("valueString")

    # Birth date
    birth_str = resource.get("birthDate", "")
    try:
        birth_date = date.fromisoformat(birth_str) if birth_str else date(1900, 1, 1)
    except ValueError:
        birth_date = date(1900, 1, 1)

    return {
        "fhir_id": fhir_id,
        "mrn": hash_identifier(mrn_raw),
        # PHI: names are hashed to opaque tokens
        "first_name": hash_identifier(given_raw) or "UNKNOWN",
        "last_name": hash_identifier(family_raw) or "UNKNOWN",
        "birth_date": birth_date,
        "gender": resource.get("gender"),
        "race": race,
        "ethnicity": ethnicity,
        # PHI: address line and postal code stripped; city/state kept for analytics
        "address_line": None,
        "city": addr.get("city"),
        "state": state_raw,
        "postal_code": None,
        # PHI: contact details stripped
        "phone": None,
        "email": None,
        "active": resource.get("active", True),
    }


def map_encounter(resource: dict, patient_fhir_to_db: dict[str, str]) -> dict | None:
    """FHIR Encounter → encounters table row dict. Returns None if patient not in DB."""
    fhir_id = resource.get("id", "")

    patient_ref = _get(resource, "subject", "reference", default="")
    patient_fhir_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
    patient_db_id = patient_fhir_to_db.get(patient_fhir_id)
    if not patient_db_id:
        return None

    # Encounter class (R4 uses "class" as a Coding, not CodeableConcept)
    class_code = _get(resource, "class", "code")

    # Type
    type_codings = _get(resource, "type", 0, "coding", default=[])
    type_code = _get(type_codings, 0, "code") if type_codings else None
    type_display = _get(type_codings, 0, "display") if type_codings else None

    # Reason (FHIR R4: reasonCode)
    reason_codings = _get(resource, "reasonCode", 0, "coding", default=[])
    reason_code = _get(reason_codings, 0, "code") if reason_codings else None
    reason_display = _get(reason_codings, 0, "display") if reason_codings else None

    # Location
    location = _get(resource, "location", 0, "location", "display")

    # Primary practitioner
    practitioner_ref = _get(resource, "participant", 0, "individual", "reference", default="")
    practitioner_id = practitioner_ref.split("/")[-1] if "/" in practitioner_ref else practitioner_ref or None

    return {
        "fhir_id": fhir_id,
        "patient_id": patient_db_id,
        "status": resource.get("status", "unknown"),
        "class_code": class_code,
        "type_code": type_code,
        "type_display": type_display,
        "start_time": _parse_dt(_get(resource, "period", "start")),
        "end_time": _parse_dt(_get(resource, "period", "end")),
        "reason_code": reason_code,
        "reason_display": reason_display,
        "location": location,
        "practitioner_id": practitioner_id,
    }


def map_condition(
    resource: dict,
    patient_fhir_to_db: dict[str, str],
    encounter_fhir_to_db: dict[str, str],
) -> dict | None:
    """FHIR Condition → conditions table row dict. Returns None if patient not in DB or no code."""
    fhir_id = resource.get("id", "")

    # Code — required (SNOMED-CT in Synthea)
    codings = _get(resource, "code", "coding", default=[])
    code = _get(codings, 0, "code") if codings else None
    if not code:
        return None
    code_system = _get(codings, 0, "system")
    display = (_get(codings, 0, "display") or _get(resource, "code", "text", default=""))[:512] or None

    # Patient — required
    patient_ref = _get(resource, "subject", "reference", default="")
    patient_fhir_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
    patient_db_id = patient_fhir_to_db.get(patient_fhir_id)
    if not patient_db_id:
        return None

    # Encounter — optional
    encounter_ref = _get(resource, "encounter", "reference", default="")
    encounter_fhir_id = encounter_ref.split("/")[-1] if "/" in encounter_ref else encounter_ref
    encounter_db_id = encounter_fhir_to_db.get(encounter_fhir_id)

    # Clinical status
    status_codings = _get(resource, "clinicalStatus", "coding", default=[])
    clinical_status = _get(status_codings, 0, "code") if status_codings else None

    # Category
    cat_codings = _get(resource, "category", 0, "coding", default=[])
    category = _get(cat_codings, 0, "code") if cat_codings else None

    # Onset — try DateTime then Period
    onset_raw = resource.get("onsetDateTime") or _get(resource, "onsetPeriod", "start")
    # Abatement
    abatement_raw = resource.get("abatementDateTime") or _get(resource, "abatementPeriod", "end")

    return {
        "fhir_id": fhir_id,
        "patient_id": patient_db_id,
        "encounter_id": encounter_db_id,
        "clinical_status": clinical_status,
        "code": code,
        "code_system": code_system,
        "display": display,
        "category": category,
        "onset_date": _parse_dt(onset_raw),
        "abatement_date": _parse_dt(abatement_raw),
        "recorded_date": _parse_dt(resource.get("recordedDate")),
    }


def map_medication_request(
    resource: dict,
    patient_fhir_to_db: dict[str, str],
    encounter_fhir_to_db: dict[str, str],
) -> dict | None:
    """FHIR MedicationRequest → medication_requests table row dict."""
    fhir_id = resource.get("id", "")

    # Medication code — prefer medicationCodeableConcept
    med_code = med_system = med_display = None
    if "medicationCodeableConcept" in resource:
        med_codings = _get(resource, "medicationCodeableConcept", "coding", default=[])
        med_code = _get(med_codings, 0, "code") if med_codings else None
        med_system = _get(med_codings, 0, "system") if med_codings else None
        med_display = (
            _get(med_codings, 0, "display")
            or _get(resource, "medicationCodeableConcept", "text")
        )
        if med_display:
            med_display = med_display[:512]
    if not med_code:
        return None

    # Patient — required
    patient_ref = _get(resource, "subject", "reference", default="")
    patient_fhir_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
    patient_db_id = patient_fhir_to_db.get(patient_fhir_id)
    if not patient_db_id:
        return None

    # Encounter — optional
    encounter_ref = _get(resource, "encounter", "reference", default="")
    encounter_fhir_id = encounter_ref.split("/")[-1] if "/" in encounter_ref else encounter_ref
    encounter_db_id = encounter_fhir_to_db.get(encounter_fhir_id)

    # Dosage (first instruction)
    dosage = _get(resource, "dosageInstruction", 0, default={})
    dosage_text = dosage.get("text") if isinstance(dosage, dict) else None
    dosage_route = (
        _get(dosage, "route", "coding", 0, "display")
        or _get(dosage, "route", "text")
    ) if isinstance(dosage, dict) else None
    dosage_timing = (
        _get(dosage, "timing", "code", "text")
    ) if isinstance(dosage, dict) else None

    return {
        "fhir_id": fhir_id,
        "patient_id": patient_db_id,
        "encounter_id": encounter_db_id,
        "status": resource.get("status", "unknown"),
        "intent": resource.get("intent", "order"),
        "medication_code": med_code,
        "medication_system": med_system,
        "medication_display": med_display,
        "authored_on": _parse_dt(resource.get("authoredOn")),
        "dosage_text": dosage_text,
        "dosage_route": str(dosage_route)[:128] if dosage_route else None,
        "dosage_timing": str(dosage_timing)[:64] if dosage_timing else None,
    }


def map_observation(
    resource: dict,
    patient_fhir_to_db: dict[str, str],
    encounter_fhir_to_db: dict[str, str],
) -> dict | None:
    """FHIR Observation → observations table row dict. Returns None if patient not in DB or no code."""
    fhir_id = resource.get("id", "")

    # Code — required
    codings = _get(resource, "code", "coding", default=[])
    code = _get(codings, 0, "code") if codings else None
    if not code:
        return None
    code_system = _get(codings, 0, "system")
    display = _get(codings, 0, "display")

    # Patient — required
    patient_ref = _get(resource, "subject", "reference", default="")
    patient_fhir_id = patient_ref.split("/")[-1] if "/" in patient_ref else patient_ref
    patient_db_id = patient_fhir_to_db.get(patient_fhir_id)
    if not patient_db_id:
        return None

    # Encounter — optional
    encounter_ref = _get(resource, "encounter", "reference", default="")
    encounter_fhir_id = encounter_ref.split("/")[-1] if "/" in encounter_ref else encounter_ref
    encounter_db_id = encounter_fhir_to_db.get(encounter_fhir_id)

    # Category
    cat_codings = _get(resource, "category", 0, "coding", default=[])
    category = _get(cat_codings, 0, "code") if cat_codings else None

    # Value — try each polymorphic type in order
    value_quantity = value_unit = value_string = value_boolean = None
    if "valueQuantity" in resource:
        value_quantity = resource["valueQuantity"].get("value")
        value_unit = resource["valueQuantity"].get("unit") or resource["valueQuantity"].get("code")
    elif "valueString" in resource:
        value_string = resource["valueString"]
    elif "valueBoolean" in resource:
        value_boolean = resource["valueBoolean"]
    elif "valueCodeableConcept" in resource:
        vcc_codings = _get(resource, "valueCodeableConcept", "coding", default=[])
        value_string = (
            _get(vcc_codings, 0, "display")
            or resource["valueCodeableConcept"].get("text")
        )

    # Reference range
    reference_low = _get(resource, "referenceRange", 0, "low", "value")
    reference_high = _get(resource, "referenceRange", 0, "high", "value")

    # Interpretation (first code)
    int_codings = _get(resource, "interpretation", 0, "coding", default=[])
    interpretation = _get(int_codings, 0, "code") if int_codings else None

    # Effective time
    effective_time = None
    if "effectiveDateTime" in resource:
        effective_time = _parse_dt(resource["effectiveDateTime"])
    elif "effectivePeriod" in resource:
        effective_time = _parse_dt(_get(resource, "effectivePeriod", "start"))
    elif "effectiveInstant" in resource:
        effective_time = _parse_dt(resource["effectiveInstant"])
    if effective_time is None:
        effective_time = datetime.now(timezone.utc)

    return {
        "fhir_id": fhir_id,
        "patient_id": patient_db_id,
        "encounter_id": encounter_db_id,
        "status": resource.get("status", "final"),
        "category": category,
        "code_system": code_system,
        "code": code,
        "display": display,
        "value_quantity": value_quantity,
        "value_unit": value_unit,
        "value_string": value_string,
        "value_boolean": value_boolean,
        "reference_low": reference_low,
        "reference_high": reference_high,
        "interpretation": interpretation,
        "effective_time": effective_time,
    }
