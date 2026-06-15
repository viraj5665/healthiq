"""
Unit tests for the NLP extraction layer.

All tests mock the Claude API — no real ANTHROPIC_API_KEY required.
The ClinicalExtractor.parse_response() static method is tested directly
(no LLM needed), and the end-to-end extract() call uses a unittest.mock
patch on ChatAnthropic.invoke.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from agents.nlp.extractor import ClinicalExtractor, MissingAPIKeyError
from agents.nlp.schema import ClinicalEvent, Diagnosis, ExtractionResult, Medication

# ── fixture responses ─────────────────────────────────────────────────────────

DIABETES_JSON = {
    "diagnoses": [
        {"description": "Type 2 Diabetes Mellitus, uncontrolled", "icd10_code": "E11.65"},
        {"description": "Essential hypertension", "icd10_code": "I10"},
        {"description": "Hypokalemia", "icd10_code": "E87.6"},
    ],
    "medications": [
        {"name": "Metformin", "dosage": "1000 mg", "frequency": "twice daily", "route": "oral"},
        {"name": "Semaglutide", "dosage": "0.5 mg", "frequency": "weekly", "route": "subcutaneous"},
        {"name": "Potassium chloride", "dosage": "20 mEq", "frequency": "daily", "route": "oral"},
    ],
    "clinical_events": [
        {"description": "HbA1c 9.4% — elevated", "event_type": "lab_result", "date_mentioned": "2024-03-05"},
        {"description": "Fasting glucose 268 mg/dL", "event_type": "lab_result", "date_mentioned": None},
        {"description": "Referred to certified diabetes education program", "event_type": "referral", "date_mentioned": None},
    ],
    "extraction_notes": None,
}

AFIB_JSON = {
    "diagnoses": [
        {"description": "New onset atrial fibrillation", "icd10_code": "I48.0"},
        {"description": "Essential hypertension, poorly controlled", "icd10_code": "I10"},
        {"description": "Hyperkalemia", "icd10_code": "E87.5"},
    ],
    "medications": [
        {"name": "Metoprolol succinate", "dosage": "25 mg", "frequency": "once daily", "route": "oral"},
        {"name": "Apixaban", "dosage": "5 mg", "frequency": "twice daily", "route": "oral"},
        {"name": "Lisinopril", "dosage": "10 mg", "frequency": "daily", "route": "oral"},
        {"name": "Amlodipine", "dosage": "5 mg", "frequency": "once daily", "route": "oral"},
    ],
    "clinical_events": [
        {"description": "EKG: atrial fibrillation with controlled ventricular response",
         "event_type": "finding", "date_mentioned": None},
        {"description": "Discontinued Lisinopril due to hyperkalemia", "event_type": "medication_change",
         "date_mentioned": None},
        {"description": "Holter monitor ordered", "event_type": "referral", "date_mentioned": None},
    ],
    "extraction_notes": "Lisinopril listed under both current medications and discontinuation.",
}

EMPTY_JSON = {
    "diagnoses": [],
    "medications": [],
    "clinical_events": [],
    "extraction_notes": None,
}

# ── parse_response ─────────────────────────────────────────────────────────────

def test_parse_plain_json():
    result = ClinicalExtractor.parse_response(json.dumps(DIABETES_JSON))
    assert isinstance(result, ExtractionResult)
    assert len(result.diagnoses) == 3
    assert len(result.medications) == 3
    assert len(result.clinical_events) == 3


def test_parse_json_with_markdown_fences():
    wrapped = f"```json\n{json.dumps(DIABETES_JSON)}\n```"
    result = ClinicalExtractor.parse_response(wrapped)
    assert len(result.diagnoses) == 3


def test_parse_json_with_plain_fences():
    wrapped = f"```\n{json.dumps(AFIB_JSON)}\n```"
    result = ClinicalExtractor.parse_response(wrapped)
    assert len(result.diagnoses) == 3


def test_parse_returns_correct_diagnosis_fields():
    result = ClinicalExtractor.parse_response(json.dumps(DIABETES_JSON))
    d = result.diagnoses[0]
    assert d.description == "Type 2 Diabetes Mellitus, uncontrolled"
    assert d.icd10_code == "E11.65"


def test_parse_icd10_can_be_null():
    data = {"diagnoses": [{"description": "Chest pain"}], "medications": [], "clinical_events": []}
    result = ClinicalExtractor.parse_response(json.dumps(data))
    assert result.diagnoses[0].icd10_code is None


def test_parse_medication_fields():
    result = ClinicalExtractor.parse_response(json.dumps(DIABETES_JSON))
    med = result.medications[0]
    assert med.name == "Metformin"
    assert med.dosage == "1000 mg"
    assert med.frequency == "twice daily"
    assert med.route == "oral"


def test_parse_medication_null_fields():
    data = {
        "diagnoses": [],
        "medications": [{"name": "Aspirin", "dosage": None, "frequency": None, "route": None}],
        "clinical_events": [],
    }
    result = ClinicalExtractor.parse_response(json.dumps(data))
    med = result.medications[0]
    assert med.name == "Aspirin"
    assert med.dosage is None
    assert med.frequency is None


def test_parse_clinical_event_fields():
    result = ClinicalExtractor.parse_response(json.dumps(AFIB_JSON))
    evt = result.clinical_events[0]
    assert evt.event_type == "finding"
    assert "atrial fibrillation" in evt.description


def test_parse_event_date_can_be_null():
    result = ClinicalExtractor.parse_response(json.dumps(AFIB_JSON))
    assert result.clinical_events[0].date_mentioned is None


def test_parse_event_date_present():
    result = ClinicalExtractor.parse_response(json.dumps(DIABETES_JSON))
    assert result.clinical_events[0].date_mentioned == "2024-03-05"


def test_parse_empty_arrays():
    result = ClinicalExtractor.parse_response(json.dumps(EMPTY_JSON))
    assert result.diagnoses == []
    assert result.medications == []
    assert result.clinical_events == []


def test_parse_extraction_notes():
    result = ClinicalExtractor.parse_response(json.dumps(AFIB_JSON))
    assert result.extraction_notes is not None
    assert "Lisinopril" in result.extraction_notes


def test_parse_extraction_notes_null():
    result = ClinicalExtractor.parse_response(json.dumps(DIABETES_JSON))
    assert result.extraction_notes is None


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError, match="valid JSON"):
        ClinicalExtractor.parse_response("this is not json")


def test_parse_handles_whitespace():
    padded = "  \n  " + json.dumps(EMPTY_JSON) + "  \n  "
    result = ClinicalExtractor.parse_response(padded)
    assert result.diagnoses == []


# ── MissingAPIKeyError ────────────────────────────────────────────────────────

def test_missing_key_raises():
    with pytest.raises(MissingAPIKeyError):
        ClinicalExtractor(api_key="sk-ant-your-key-here")


def test_empty_key_raises():
    with pytest.raises(MissingAPIKeyError):
        ClinicalExtractor(api_key="")


def test_none_key_raises():
    with pytest.raises(MissingAPIKeyError):
        ClinicalExtractor(api_key=None)


# ── end-to-end extract() with mocked LLM ──────────────────────────────────────

def _mock_extractor(response_json: dict) -> ClinicalExtractor:
    """Build a ClinicalExtractor that never calls the real API."""
    with patch("agents.nlp.extractor.ChatAnthropic") as MockLLM:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = MagicMock(content=json.dumps(response_json))
        MockLLM.return_value = mock_llm_instance
        extractor = ClinicalExtractor(api_key="sk-ant-real-key-placeholder-for-test")
        extractor._llm = mock_llm_instance
    return extractor


def test_extract_calls_llm():
    extractor = _mock_extractor(DIABETES_JSON)
    result = extractor.extract("Patient has diabetes.")
    assert isinstance(result, ExtractionResult)
    extractor._llm.invoke.assert_called_once()


def test_extract_returns_diagnoses():
    extractor = _mock_extractor(DIABETES_JSON)
    result = extractor.extract("Type 2 Diabetes Mellitus, uncontrolled (E11.65)")
    assert len(result.diagnoses) == 3
    assert result.diagnoses[0].icd10_code == "E11.65"


def test_extract_returns_medications():
    extractor = _mock_extractor(DIABETES_JSON)
    result = extractor.extract("Continue Metformin 1000mg twice daily.")
    assert any(m.name == "Metformin" for m in result.medications)


def test_extract_afib_note():
    extractor = _mock_extractor(AFIB_JSON)
    result = extractor.extract("New onset atrial fibrillation.")
    assert any(d.icd10_code == "I48.0" for d in result.diagnoses)
    assert any(m.name == "Apixaban" for m in result.medications)


def test_extract_empty_note():
    extractor = _mock_extractor(EMPTY_JSON)
    result = extractor.extract("Normal physical exam.")
    assert result.diagnoses == []
    assert result.medications == []
