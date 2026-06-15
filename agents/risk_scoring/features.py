"""
Feature engineering: patient + encounter + observation → numeric feature matrix.

Pure Python/pandas — no DB calls here so functions are unit-testable with
SimpleNamespace mocks.
"""

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

FEATURE_COLS = [
    "age",               # years (0 when birth_date is sentinel 1900-01-01)
    "gender_male",       # 1 = male, 0 = other/unknown
    "num_encounters",    # total historical encounters
    "num_er_encounters", # encounters with class_code EMER / ER / emergency
    "avg_los_days",      # mean (end−start) across encounters with both times
    "max_los_days",      # longest single encounter in days
    "num_observations",  # total observations
    "num_abnormal_obs",  # obs with interpretation code H/L/A/AA/HH/LL
    "abnormal_rate",     # num_abnormal / num_obs (0.0 when 0 obs)
    "hba1c_high",        # LOINC 4548-4 > 7.5 %
    "glucose_high",      # LOINC 2345-7 > 200 mg/dL
    "cholesterol_high",  # LOINC 2093-3 > 240 mg/dL
    "potassium_abnormal",# LOINC 2823-3 > 5.5 mmol/L
]

_ABNORMAL_INTERPS = {"H", "L", "A", "AA", "HH", "LL", "HU", "LU"}
_ER_CODES = {"EMER", "ER", "emergency", "Emergency"}

_SENTINEL_DOB = date(1900, 1, 1)


def _age(birth_date: date) -> float:
    if birth_date == _SENTINEL_DOB:
        return 0.0
    today = date.today()
    return (today - birth_date).days / 365.25


def _fval(v) -> float | None:
    """Safe float coercion for Decimal/int/float DB values."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def build_feature_matrix(patients, encounters, observations) -> pd.DataFrame:
    """
    Parameters
    ----------
    patients     : iterable of Patient ORM objects (or SimpleNamespace mocks)
    encounters   : iterable of Encounter ORM objects
    observations : iterable of Observation ORM objects

    Returns
    -------
    pd.DataFrame with columns = ['patient_id', 'patient_fhir_id'] + FEATURE_COLS
    """
    # Group by patient_id
    enc_by_pt: dict = defaultdict(list)
    for e in encounters:
        enc_by_pt[e.patient_id].append(e)

    obs_by_pt: dict = defaultdict(list)
    for o in observations:
        obs_by_pt[o.patient_id].append(o)

    rows = []
    for p in patients:
        pid = p.id
        encs = enc_by_pt.get(pid, [])
        obs = obs_by_pt.get(pid, [])

        # ── encounter features ──────────────────────────────────────────────
        er_enc = sum(1 for e in encs if (e.class_code or "") in _ER_CODES)

        los_days = []
        for e in encs:
            if e.start_time and e.end_time:
                delta = (e.end_time - e.start_time).total_seconds() / 86_400
                if delta >= 0:
                    los_days.append(delta)
        avg_los = sum(los_days) / len(los_days) if los_days else 0.0
        max_los = max(los_days, default=0.0)

        # ── observation features ────────────────────────────────────────────
        n_obs = len(obs)
        n_abnormal = sum(1 for o in obs if (o.interpretation or "") in _ABNORMAL_INTERPS)
        abnormal_rate = n_abnormal / n_obs if n_obs else 0.0

        hba1c_high = any(
            o.code == "4548-4" and (_fval(o.value_quantity) or 0) > 7.5 for o in obs
        )
        glucose_high = any(
            o.code == "2345-7" and (_fval(o.value_quantity) or 0) > 200 for o in obs
        )
        cholesterol_high = any(
            o.code == "2093-3" and (_fval(o.value_quantity) or 0) > 240 for o in obs
        )
        potassium_abnormal = any(
            o.code == "2823-3" and (_fval(o.value_quantity) or 0) > 5.5 for o in obs
        )

        rows.append({
            "patient_id": str(pid),
            "patient_fhir_id": p.fhir_id,
            "age": _age(p.birth_date),
            "gender_male": 1 if p.gender == "male" else 0,
            "num_encounters": len(encs),
            "num_er_encounters": er_enc,
            "avg_los_days": avg_los,
            "max_los_days": max_los,
            "num_observations": n_obs,
            "num_abnormal_obs": n_abnormal,
            "abnormal_rate": abnormal_rate,
            "hba1c_high": int(hba1c_high),
            "glucose_high": int(glucose_high),
            "cholesterol_high": int(cholesterol_high),
            "potassium_abnormal": int(potassium_abnormal),
        })

    return pd.DataFrame(rows)


def load_patient_data(db, patient_id: str | None = None):
    """Query patients + encounters + observations from DB."""
    from api.models.encounter import Encounter
    from api.models.observation import Observation
    from api.models.patient import Patient

    q = db.query(Patient).filter_by(active=True)
    if patient_id:
        q = q.filter(Patient.id == patient_id)
    patients = q.all()

    if not patients:
        return [], [], []

    pids = [p.id for p in patients]
    encounters = db.query(Encounter).filter(Encounter.patient_id.in_(pids)).all()
    observations = db.query(Observation).filter(Observation.patient_id.in_(pids)).all()
    return patients, encounters, observations
