"""
Synthetic readmission-risk labels for training.

⚠  SYNTHETIC PLACEHOLDER — these labels are derived from a rule-based
   LACE-inspired heuristic, NOT from actual 30-day readmission outcomes.
   Replace df['lace_label'] with real outcome data (e.g. from claims,
   EHR readmission flags) before using this model in production.

LACE index reference:
  L = Length of stay   (0–7 pts)
  A = Acuity via ED    (0–3 pts)
  C = Comorbidities    (0–5 pts, approximated via lab abnormalities)
  E = ED visits ≤6 mo  (0–4 pts, approximated from total ER encounters)

We use a simplified version (max ≈ 16 pts) with threshold=4.
Patients with ≥1 clinical risk factor (high HbA1c, high glucose, etc.)
and multiple encounters are more likely to receive label=1.
"""

import pandas as pd


def compute_lace_score(row) -> int:
    score = 0

    # L — length of stay
    los = row["avg_los_days"]
    if los >= 14:   score += 7
    elif los >= 7:  score += 5
    elif los >= 4:  score += 4
    elif los >= 3:  score += 3
    elif los >= 2:  score += 2
    elif los >= 1:  score += 1

    # A — acuity (ED admission)
    er = int(row["num_er_encounters"])
    if er >= 4:    score += 3
    elif er >= 1:  score += 1

    # C — comorbidities (lab-based approximation)
    if row["hba1c_high"]:         score += 2  # uncontrolled diabetes
    if row["glucose_high"]:       score += 1
    if row["cholesterol_high"]:   score += 1
    if row["potassium_abnormal"]: score += 1  # electrolyte imbalance
    ar = float(row["abnormal_rate"])
    if ar >= 0.5:    score += 2
    elif ar >= 0.2:  score += 1

    # E — ED visits (separate from acuity; count multiple ER visits)
    if er >= 4:    score += 4
    elif er == 3:  score += 3
    elif er == 2:  score += 2
    elif er == 1:  score += 1

    # Age risk factor
    age = float(row["age"])
    if age >= 75:    score += 2
    elif age >= 65:  score += 1
    elif age <= 0:   pass  # unknown age — no penalty

    return min(score, 19)


# Threshold chosen so ~20-40 % of patients score positive on typical
# synthetic FHIR data (few hospital stays but some abnormal labs).
_LACE_THRESHOLD = 4


def add_lace_labels(df: pd.DataFrame, threshold: int = _LACE_THRESHOLD) -> pd.DataFrame:
    """
    Adds 'lace_score' and 'lace_label' columns to the feature DataFrame.

    If all patients end up with the same label (common when dataset is tiny
    and homogeneous), the top-quartile by lace_score are flipped to the
    minority class so XGBoost can always train.
    """
    df = df.copy()
    df["lace_score"] = df.apply(compute_lace_score, axis=1)
    df["lace_label"] = (df["lace_score"] >= threshold).astype(int)

    if df["lace_label"].nunique() < 2:
        # Force at least 1 sample per class
        n_flip = max(1, len(df) // 4)
        majority = df["lace_label"].iloc[0]
        minority = 1 - majority
        # Flip the patients most likely to be mis-labelled (highest score if
        # majority=0, lowest if majority=1)
        if majority == 0:
            idx = df["lace_score"].nlargest(n_flip).index
        else:
            idx = df["lace_score"].nsmallest(n_flip).index
        df.loc[idx, "lace_label"] = minority

    return df
