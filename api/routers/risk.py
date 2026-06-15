from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.risk_scoring.agent import RiskScoringAgent
from api.database import get_db
from api.models.risk_score import RiskScore

router = APIRouter(prefix="/risk", tags=["risk-scoring"])


@router.post("/score")
def run_scoring(patient_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Train XGBoost on synthetic LACE labels and write scores to risk_scores table.

    Pass ?patient_id=<uuid> to score a single patient; omit to score all.
    """
    result = RiskScoringAgent().run(db, patient_id=patient_id)
    return asdict(result)


@router.get("/scores")
def get_scores(
    patient_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Return current risk scores with SHAP explanations."""
    q = db.query(RiskScore)
    if patient_id:
        q = q.filter(RiskScore.patient_id == patient_id)
    if risk_level:
        q = q.filter(RiskScore.risk_level == risk_level)
    scores = q.order_by(RiskScore.score.desc()).limit(limit).all()

    return [
        {
            "id": str(s.id),
            "patient_id": str(s.patient_id),
            "score_type": s.score_type,
            "score": float(s.score),
            "risk_level": s.risk_level,
            "model_version": s.model_version,
            "computed_at": s.computed_at.isoformat(),
            "explanation": s.explanation,
            "features": s.features,
        }
        for s in scores
    ]
