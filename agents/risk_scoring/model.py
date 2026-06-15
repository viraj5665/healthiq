"""
XGBoost readmission risk model + SHAP explanations.

SHAP values are computed via XGBoost's built-in pred_contribs (no separate
shap package needed). Each patient row gets a top-3 feature explanation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb
from xgboost import XGBClassifier

from agents.risk_scoring.features import FEATURE_COLS

MODEL_VERSION = "xgb-synthetic-v1"


def train(df: pd.DataFrame) -> XGBClassifier:
    """Train XGBClassifier on synthetic-labelled feature matrix."""
    X = df[FEATURE_COLS].fillna(0).astype(float)
    y = df["lace_label"].astype(int)

    # Disable row/column sampling on tiny datasets — with <20 rows,
    # stochastic sampling produces uninformative trees.
    small = len(df) < 20
    model = XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        subsample=1.0 if small else 0.8,
        colsample_bytree=1.0 if small else 0.8,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )
    model.fit(X, y)
    return model


def predict_with_shap(
    model: XGBClassifier, df: pd.DataFrame
) -> tuple[np.ndarray, list[list[dict]]]:
    """
    Returns
    -------
    probs        : 1-D array of readmission probabilities (0–1)
    explanations : list[list[dict]]  — per patient, top-3 SHAP features
                   [{"feature": str, "shap_value": float, "feature_value": float}, ...]
    """
    X = df[FEATURE_COLS].fillna(0).astype(float)

    probs: np.ndarray = model.predict_proba(X)[:, 1]

    # XGBoost's built-in SHAP (pred_contribs).
    # Returns shape (n_samples, n_features + 1); last column is the bias term.
    booster = model.get_booster()
    dmat = xgb.DMatrix(X.values, feature_names=FEATURE_COLS)
    shap_matrix = booster.predict(dmat, pred_contribs=True)

    explanations: list[list[dict]] = []
    for i, shap_row in enumerate(shap_matrix):
        feature_shap = list(zip(FEATURE_COLS, shap_row[:-1]))  # drop bias
        top3 = sorted(feature_shap, key=lambda t: abs(t[1]), reverse=True)[:3]
        explanations.append([
            {
                "feature": feat,
                "shap_value": round(float(sv), 6),
                "feature_value": round(float(X.iloc[i][feat]), 4),
            }
            for feat, sv in top3
        ])

    return probs, explanations


def classify_risk(prob: float) -> str:
    if prob >= 0.75:  return "critical"
    if prob >= 0.50:  return "high"
    if prob >= 0.25:  return "moderate"
    return "low"
