"""
Unit tests for risk-scoring feature engineering, label generation, and model logic.

No database or live XGBoost training in most tests.
The one model-path test trains on 6 synthetic rows (~milliseconds).
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from agents.risk_scoring.features import FEATURE_COLS, _age, build_feature_matrix
from agents.risk_scoring.labels import _LACE_THRESHOLD, add_lace_labels, compute_lace_score
from agents.risk_scoring.model import classify_risk, predict_with_shap, train

# ── helpers ───────────────────────────────────────────────────────────────────

def _pt(pid, birth_date=date(1960, 1, 1), gender="male"):
    return SimpleNamespace(id=pid, fhir_id=f"fhir-{pid}", birth_date=birth_date, gender=gender)

def _enc(eid, pid, class_code="AMB", start=None, end=None):
    return SimpleNamespace(id=eid, patient_id=pid, class_code=class_code,
                           start_time=start, end_time=end)

def _obs(oid, pid, code, value=None, interp=None):
    return SimpleNamespace(id=oid, patient_id=pid, code=code,
                           value_quantity=Decimal(str(value)) if value is not None else None,
                           interpretation=interp)

_DT = lambda s: datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

# ── age helper ────────────────────────────────────────────────────────────────

def test_age_known_dob():
    dob = date(1974, 5, 12)
    a = _age(dob)
    assert 50 < a < 55

def test_age_sentinel_returns_zero():
    assert _age(date(1900, 1, 1)) == 0.0

# ── build_feature_matrix ──────────────────────────────────────────────────────

def _two_patient_df():
    p1, p2 = _pt("p1", date(1960, 1, 1), "male"), _pt("p2", date(1985, 6, 15), "female")
    encs = [
        _enc("e1", "p1", "AMB", _DT("2024-01-01T08:00:00"), _DT("2024-01-03T08:00:00")),  # 2 days
        _enc("e2", "p1", "EMER"),
    ]
    obs = [
        _obs("o1", "p1", "4548-4", 9.4),        # HbA1c high
        _obs("o2", "p1", "2345-7", 268),          # glucose high
        _obs("o3", "p1", "2093-3", 245),          # cholesterol high
        _obs("o4", "p2", "2823-3", 6.0, "H"),    # potassium abnormal + interpretation H
    ]
    return build_feature_matrix([p1, p2], encs, obs)

def test_returns_correct_columns():
    df = _two_patient_df()
    for col in ["patient_id", "patient_fhir_id"] + FEATURE_COLS:
        assert col in df.columns

def test_row_count_matches_patients():
    df = _two_patient_df()
    assert len(df) == 2

def test_p1_encounter_features():
    df = _two_patient_df().set_index("patient_id")
    row = df.loc["p1"]
    assert row["num_encounters"] == 2
    assert row["num_er_encounters"] == 1
    assert abs(row["avg_los_days"] - 2.0) < 0.1

def test_p1_max_los():
    df = _two_patient_df().set_index("patient_id")
    assert abs(df.loc["p1"]["max_los_days"] - 2.0) < 0.1

def test_p1_lab_flags():
    df = _two_patient_df().set_index("patient_id")
    row = df.loc["p1"]
    assert row["hba1c_high"] == 1
    assert row["glucose_high"] == 1
    assert row["cholesterol_high"] == 1
    assert row["potassium_abnormal"] == 0

def test_p2_potassium_flag():
    df = _two_patient_df().set_index("patient_id")
    assert df.loc["p2"]["potassium_abnormal"] == 1

def test_p2_abnormal_interpretation():
    df = _two_patient_df().set_index("patient_id")
    row = df.loc["p2"]
    assert row["num_abnormal_obs"] == 1
    assert abs(row["abnormal_rate"] - 1.0) < 0.01

def test_gender_encoding():
    df = _two_patient_df().set_index("patient_id")
    assert df.loc["p1"]["gender_male"] == 1
    assert df.loc["p2"]["gender_male"] == 0

def test_no_observations_gives_zero_rates():
    df = _two_patient_df().set_index("patient_id")
    row = df.loc["p2"]
    # p2 has 1 observation (o4) but let's check a fresh empty case
    p = _pt("px", date(1970, 1, 1))
    df2 = build_feature_matrix([p], [], [])
    assert df2.iloc[0]["num_observations"] == 0
    assert df2.iloc[0]["abnormal_rate"] == 0.0

# ── compute_lace_score ────────────────────────────────────────────────────────

def _row(**kwargs):
    defaults = dict(
        avg_los_days=0, num_er_encounters=0, hba1c_high=0,
        glucose_high=0, cholesterol_high=0, potassium_abnormal=0,
        abnormal_rate=0.0, age=50,
    )
    defaults.update(kwargs)
    return pd.Series(defaults)

def test_lace_zero_for_healthy():
    assert compute_lace_score(_row()) == 0

def test_lace_long_stay():
    assert compute_lace_score(_row(avg_los_days=14)) >= 7

def test_lace_er_visit():
    s = compute_lace_score(_row(num_er_encounters=1))
    assert s >= 2  # acuity + E

def test_lace_multiple_er():
    assert compute_lace_score(_row(num_er_encounters=4)) >= 7

def test_lace_diabetes_markers():
    s = compute_lace_score(_row(hba1c_high=1, glucose_high=1))
    assert s >= 3

def test_lace_elderly():
    assert compute_lace_score(_row(age=75)) >= 2

def test_lace_max_capped_at_19():
    s = compute_lace_score(_row(
        avg_los_days=14, num_er_encounters=4, hba1c_high=1,
        glucose_high=1, cholesterol_high=1, potassium_abnormal=1,
        abnormal_rate=0.9, age=80,
    ))
    assert s <= 19

def test_lace_unknown_age_no_penalty():
    s0 = compute_lace_score(_row(age=0))
    s50 = compute_lace_score(_row(age=50))
    assert s0 == s50  # age=0 → unknown, no extra points vs 50-year-old

# ── add_lace_labels ───────────────────────────────────────────────────────────

def _minimal_df(n=6):
    rows = []
    for i in range(n):
        rows.append({c: float(i % 3) for c in FEATURE_COLS})
        rows[-1]["patient_id"] = f"p{i}"
        rows[-1]["patient_fhir_id"] = f"fhir-{i}"
    return pd.DataFrame(rows)

def test_add_lace_labels_both_classes_exist():
    df = add_lace_labels(_minimal_df(6))
    assert df["lace_label"].nunique() == 2

def test_add_lace_labels_score_column_added():
    df = add_lace_labels(_minimal_df(6))
    assert "lace_score" in df.columns
    assert (df["lace_score"] >= 0).all()

def test_add_lace_labels_label_is_binary():
    df = add_lace_labels(_minimal_df(6))
    assert set(df["lace_label"].unique()).issubset({0, 1})

# ── classify_risk ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("prob,expected", [
    (0.0,  "low"),
    (0.24, "low"),
    (0.25, "moderate"),
    (0.49, "moderate"),
    (0.50, "high"),
    (0.74, "high"),
    (0.75, "critical"),
    (1.0,  "critical"),
])
def test_classify_risk(prob, expected):
    assert classify_risk(prob) == expected

# ── train + predict_with_shap (tiny end-to-end) ───────────────────────────────

def _make_training_df():
    """20-row fixture with clear high/low risk separation so XGBoost can learn."""
    high = [
        {"age": a, "gender_male": 1, "num_encounters": e, "num_er_encounters": er,
         "avg_los_days": los, "max_los_days": los, "num_observations": n,
         "num_abnormal_obs": ab, "abnormal_rate": ab / max(n, 1),
         "hba1c_high": 1, "glucose_high": 1, "cholesterol_high": 1,
         "potassium_abnormal": 1, "lace_label": 1}
        for a, e, er, los, n, ab in [
            (72, 6, 3, 8, 8, 5), (68, 5, 2, 6, 7, 4), (75, 7, 4, 10, 9, 6),
            (70, 6, 3, 7, 8, 5), (65, 4, 2, 5, 6, 4), (80, 8, 5, 12, 10, 7),
            (71, 5, 3, 9, 7, 5), (67, 6, 2, 6, 8, 4), (73, 7, 4, 8, 9, 6),
            (69, 5, 2, 7, 7, 5),
        ]
    ]
    low = [
        {"age": a, "gender_male": 0, "num_encounters": e, "num_er_encounters": 0,
         "avg_los_days": 0, "max_los_days": 0, "num_observations": n,
         "num_abnormal_obs": 0, "abnormal_rate": 0.0,
         "hba1c_high": 0, "glucose_high": 0, "cholesterol_high": 0,
         "potassium_abnormal": 0, "lace_label": 0}
        for a, e, n in [
            (28, 1, 1), (32, 1, 2), (25, 0, 0), (35, 2, 2), (30, 1, 1),
            (27, 0, 0), (33, 1, 1), (29, 1, 2), (31, 0, 0), (26, 1, 1),
        ]
    ]
    rows = high + low
    for i, r in enumerate(rows):
        r["patient_id"] = f"p{i}"
        r["patient_fhir_id"] = f"fhir-{i}"
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def tiny_model():
    df = _make_training_df()
    return train(df), df


def test_train_returns_xgb_model(tiny_model):
    model, _ = tiny_model
    assert hasattr(model, "predict_proba")


def test_predict_proba_range(tiny_model):
    model, df = tiny_model
    probs, _ = predict_with_shap(model, df)
    assert len(probs) == len(df)
    assert all(0.0 <= p <= 1.0 for p in probs)


def test_shap_top3_structure(tiny_model):
    model, df = tiny_model
    _, explanations = predict_with_shap(model, df)
    assert len(explanations) == len(df)
    for exp in explanations:
        assert len(exp) == 3
        for entry in exp:
            assert "feature" in entry
            assert "shap_value" in entry
            assert "feature_value" in entry
            assert entry["feature"] in FEATURE_COLS


def test_shap_features_are_valid(tiny_model):
    model, df = tiny_model
    _, explanations = predict_with_shap(model, df)
    valid_features = set(FEATURE_COLS)
    for exp in explanations:
        for entry in exp:
            assert entry["feature"] in valid_features


def test_high_risk_scores_higher_than_low(tiny_model):
    model, df = tiny_model
    probs, _ = predict_with_shap(model, df)
    high_risk_mean = probs[df["lace_label"] == 1].mean()
    low_risk_mean = probs[df["lace_label"] == 0].mean()
    assert high_risk_mean > low_risk_mean
