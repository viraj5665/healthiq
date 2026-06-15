"""Pydantic schemas for NLP extraction output."""

from pydantic import BaseModel, Field


class Diagnosis(BaseModel):
    description: str = Field(description="Diagnosis name exactly as stated in the note")
    icd10_code: str | None = Field(None, description="ICD-10 code if explicitly written in the note")


class Medication(BaseModel):
    name: str = Field(description="Medication name")
    dosage: str | None = Field(None, description="Dosage string (e.g. '500mg')")
    frequency: str | None = Field(None, description="Frequency (e.g. 'twice daily')")
    route: str | None = Field(None, description="Route of administration (e.g. 'oral', 'IV')")


class ClinicalEvent(BaseModel):
    description: str = Field(description="Concise description of the clinical event")
    event_type: str = Field(
        description="One of: admission | discharge | procedure | symptom | finding | "
                    "medication_change | lab_result | referral | other"
    )
    date_mentioned: str | None = Field(None, description="Date string as written in note, or null")


class ExtractionResult(BaseModel):
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    clinical_events: list[ClinicalEvent] = Field(default_factory=list)
    extraction_notes: str | None = Field(
        None, description="Any important caveats about this extraction"
    )
