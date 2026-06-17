import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from agents.risk_scoring.features import FEATURE_COLS, build_feature_matrix, load_patient_data
from agents.risk_scoring.labels import add_lace_labels
from agents.risk_scoring.model import MODEL_VERSION, classify_risk, predict_with_shap, train

logger = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    patients_scored: int = 0
    inserted: int = 0
    updated: int = 0
    errors: int = 0
    model_version: str = ""
    lace_label_distribution: dict = field(default_factory=dict)
    risk_level_distribution: dict = field(default_factory=dict)
    duration_seconds: float = 0.0
    error_log: list[str] = field(default_factory=list)


class RiskScoringAgent:
    def run(self, db: Session, patient_id: str | None = None,
            write_only_patient_id: str | None = None) -> ScoringResult:
        from api.models.risk_score import RiskScore

        t0 = time.monotonic()
        result = ScoringResult()

        # ── 1. load data ───────────────────────────────────────────────────
        # Always load all patients for training (write_only_patient_id limits
        # which score rows are written, but training uses the full dataset).
        patients, encounters, observations = load_patient_data(db, patient_id)

        if not patients:
            result.error_log.append("No active patients found — run ingestion first.")
            result.duration_seconds = round(time.monotonic() - t0, 2)
            return result

        if len(patients) < 2:
            result.error_log.append("Need ≥ 2 patients to train. Run ingestion first.")
            result.duration_seconds = round(time.monotonic() - t0, 2)
            return result

        # ── 2. feature engineering ─────────────────────────────────────────
        df = build_feature_matrix(patients, encounters, observations)
        df = add_lace_labels(df)
        result.lace_label_distribution = {
            str(k): int(v) for k, v in df["lace_label"].value_counts().items()
        }
        logger.info("Scoring %d patients. LACE distribution: %s",
                    len(df), result.lace_label_distribution)

        # ── 3. train + score ───────────────────────────────────────────────
        try:
            model = train(df)
            probs, explanations = predict_with_shap(model, df)
        except Exception as exc:
            result.error_log.append(f"Model training failed: {exc}")
            result.duration_seconds = round(time.monotonic() - t0, 2)
            return result

        version = f"{MODEL_VERSION}-{len(df)}pts"
        result.model_version = version

        # ── 4. write risk_scores ───────────────────────────────────────────
        risk_level_counts: dict[str, int] = {}
        for i, row in df.iterrows():
            if write_only_patient_id and str(row["patient_id"]) != write_only_patient_id:
                continue
            try:
                prob = float(probs[i])
                level = classify_risk(prob)
                risk_level_counts[level] = risk_level_counts.get(level, 0) + 1
                features_dict = {c: round(float(row[c]), 6) for c in FEATURE_COLS}

                existing = (
                    db.query(RiskScore)
                    .filter_by(patient_id=row["patient_id"], score_type="readmission")
                    .first()
                )
                if existing:
                    existing.score = prob
                    existing.risk_level = level
                    existing.model_version = version
                    existing.features = features_dict
                    existing.explanation = explanations[i]
                    existing.computed_at = datetime.now(timezone.utc)
                    result.updated += 1
                else:
                    rs = RiskScore(
                        patient_id=row["patient_id"],
                        score_type="readmission",
                        score=prob,
                        risk_level=level,
                        model_version=version,
                        features=features_dict,
                        explanation=explanations[i],
                    )
                    db.add(rs)
                    result.inserted += 1

                result.patients_scored += 1
            except Exception as exc:
                result.errors += 1
                result.error_log.append(f"Patient {row.get('patient_fhir_id')}: {exc}")
                logger.exception("Score write error")

        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            result.error_log.append(f"Commit failed: {exc}")

        result.risk_level_distribution = risk_level_counts
        result.duration_seconds = round(time.monotonic() - t0, 2)
        return result
