"""Manual patient intake — create a patient record and immediately risk-score them."""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from agents.risk_scoring.agent import RiskScoringAgent
from api.database import get_db
from api.models.encounter import Encounter
from api.models.patient import Patient
from api.models.risk_score import RiskScore

router = APIRouter(prefix="/patients", tags=["patients"])


class ManualPatientIn(BaseModel):
    date_of_birth: str        # YYYY-MM-DD
    gender: str               # male | female | other
    num_encounters: int       # total prior encounters
    num_er_visits: int        # ER visits (≤ num_encounters)
    conditions: str = ""      # free-text note, not used for scoring

    @field_validator("date_of_birth")
    @classmethod
    def dob_in_past(cls, v: str) -> str:
        try:
            d = date.fromisoformat(v)
        except ValueError:
            raise ValueError("date_of_birth must be YYYY-MM-DD")
        if d >= date.today():
            raise ValueError("date_of_birth must be in the past")
        return v

    @field_validator("num_er_visits")
    @classmethod
    def er_lte_total(cls, v: int, info) -> int:
        total = info.data.get("num_encounters", 0)
        if v > total:
            raise ValueError("num_er_visits cannot exceed num_encounters")
        return v


def _make_encounters(patient_id: uuid.UUID, num_total: int, num_er: int) -> list[Encounter]:
    """Synthetic encounters spread over the past 2 years."""
    import random
    rng = random.Random(str(patient_id))
    now = datetime.now(tz=timezone.utc)
    encounters = []
    for i in range(num_total):
        is_er = i < num_er
        days_ago = rng.randint(1, 730)
        start = now - timedelta(days=days_ago, hours=rng.randint(0, 23))
        hours = rng.uniform(4, 14) if is_er else rng.uniform(20, 72)
        end = start + timedelta(hours=hours)
        encounters.append(Encounter(
            patient_id=patient_id,
            status="finished",
            class_code="EMER" if is_er else "AMB",
            type_display="Emergency Room Visit" if is_er else "Ambulatory Encounter",
            start_time=start,
            end_time=end,
        ))
    return encounters


@router.post("/manual")
def create_manual_patient(body: ManualPatientIn, db: Session = Depends(get_db)):
    """
    Create a patient from form data, generate synthetic encounter history,
    retrain the risk model on all patients, and return the new patient's score.
    """
    dob = date.fromisoformat(body.date_of_birth)

    patient = Patient(
        first_name="Manual",
        last_name="Patient",
        birth_date=dob,
        gender=body.gender,
        active=True,
    )
    db.add(patient)
    db.flush()  # get patient.id before adding encounters

    for enc in _make_encounters(patient.id, body.num_encounters, body.num_er_visits):
        db.add(enc)
    db.commit()

    # Retrain on all patients (including the new one) and write scores
    result = RiskScoringAgent().run(db)
    if result.error_log and not result.patients_scored:
        raise HTTPException(status_code=500, detail="; ".join(result.error_log))

    # Return the new patient's risk score
    score_row = (
        db.query(RiskScore)
        .filter_by(patient_id=patient.id, score_type="readmission")
        .first()
    )
    if not score_row:
        raise HTTPException(status_code=500, detail="Scoring succeeded but no score found for new patient")

    return {
        "patient_id": str(patient.id),
        "score": float(score_row.score),
        "risk_level": score_row.risk_level,
        "model_version": score_row.model_version,
        "explanation": score_row.explanation,
        "features": score_row.features,
        "patients_in_model": result.patients_scored,
    }
