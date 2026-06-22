"""Manual patient intake — create a patient record and immediately score with LACE."""

import math
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from agents.risk_scoring.labels import compute_lace_score
from agents.risk_scoring.model import MODEL_VERSION, classify_risk
from api.database import get_db
from api.models.encounter import Encounter
from api.models.patient import Patient
from api.models.risk_score import RiskScore

router = APIRouter(prefix="/patients", tags=["patients"])

# ER encounter LOS: uniform 4-14h → mean 9h; AMB: uniform 20-72h → mean 46h
_ER_LOS_DAYS  = 9.0  / 24
_AMB_LOS_DAYS = 46.0 / 24


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


def _lace_prob(lace_score: int) -> float:
    """Map a LACE score (0-19) to a readmission probability via sigmoid.

    Calibrated so LACE=4 → ~0.27 (moderate), LACE=7 → ~0.50 (high boundary),
    LACE=10 → ~0.73, LACE=13 → ~0.90 (critical), matching classify_risk thresholds.
    """
    return 1.0 / (1.0 + math.exp(-0.4 * (lace_score - 7)))


def _build_lace_features(body: ManualPatientIn, dob: date) -> dict:
    """Build the minimal feature dict needed by compute_lace_score."""
    age = (date.today() - dob).days / 365.25
    n_enc = body.num_encounters
    n_er  = body.num_er_visits
    n_amb = n_enc - n_er

    if n_enc > 0:
        avg_los = (n_er * _ER_LOS_DAYS + n_amb * _AMB_LOS_DAYS) / n_enc
        max_los = _AMB_LOS_DAYS if n_amb > 0 else _ER_LOS_DAYS
    else:
        avg_los = max_los = 0.0

    return {
        "age":               age,
        "gender_male":       1.0 if body.gender == "male" else 0.0,
        "num_encounters":    float(n_enc),
        "num_er_encounters": float(n_er),
        "avg_los_days":      avg_los,
        "max_los_days":      max_los,
        "num_observations":  0.0,
        "num_abnormal_obs":  0.0,
        "abnormal_rate":     0.0,
        "hba1c_high":        0.0,
        "glucose_high":      0.0,
        "cholesterol_high":  0.0,
        "potassium_abnormal": 0.0,
    }


@router.post("/manual")
def create_manual_patient(body: ManualPatientIn, db: Session = Depends(get_db)):
    """
    Create a patient from form data, generate synthetic encounter history,
    and score using a lightweight LACE rule (no XGBoost retrain).
    Call POST /risk/score separately to retrain the full model.
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
    db.flush()

    for enc in _make_encounters(patient.id, body.num_encounters, body.num_er_visits):
        db.add(enc)

    # Compute lightweight LACE score — O(1), no model load
    features = _build_lace_features(body, dob)
    lace     = compute_lace_score(features)
    prob     = round(_lace_prob(lace), 4)
    level    = classify_risk(prob)
    version  = f"{MODEL_VERSION}-lace-manual"

    shap_like = [
        {"feature": "num_er_encounters", "shap_value": round(features["num_er_encounters"] * 0.4, 4), "feature_value": features["num_er_encounters"]},
        {"feature": "age",               "shap_value": round((features["age"] - 50) * 0.02, 4),       "feature_value": round(features["age"], 2)},
        {"feature": "avg_los_days",      "shap_value": round(features["avg_los_days"] * 0.15, 4),     "feature_value": round(features["avg_los_days"], 4)},
    ]

    score_row = RiskScore(
        patient_id=patient.id,
        score_type="readmission",
        score=prob,
        risk_level=level,
        model_version=version,
        features=features,
        explanation=shap_like,
    )
    db.add(score_row)
    db.commit()
    db.refresh(score_row)

    return {
        "patient_id":       str(patient.id),
        "score":            prob,
        "risk_level":       level,
        "model_version":    version,
        "explanation":      shap_like,
        "features":         features,
        "lace_score":       lace,
        "patients_in_model": 1,
    }
