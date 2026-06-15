from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from agents.alert.agent import AlertAgent
from api.database import get_db
from api.models.alert import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])

SeverityFilter = Literal["warning", "urgent", "critical"]


@router.post("/check")
def check_alerts(db: Session = Depends(get_db)):
    """Run the Alert Agent across current risk scores and bed forecasts."""
    agent = AlertAgent(db=db)
    result = agent.run()
    return {
        "created": result.created,
        "skipped_duplicates": result.skipped_duplicates,
        "risk_alerts": result.risk_alerts,
        "bed_alerts": result.bed_alerts,
        "alert_ids": result.alert_ids,
    }


@router.get("")
def get_alerts(
    severity: list[SeverityFilter] | None = Query(default=None),
    status: str | None = Query(default="active"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """Return alerts, optionally filtered by severity and/or status."""
    q = db.query(Alert)
    if status:
        q = q.filter(Alert.status == status)
    if severity:
        q = q.filter(Alert.severity.in_(severity))
    rows = q.order_by(Alert.triggered_at.desc()).limit(limit).all()
    return [
        {
            "id": str(a.id),
            "alert_type": a.alert_type,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "status": a.status,
            "patient_id": str(a.patient_id) if a.patient_id else None,
            "risk_score_id": str(a.risk_score_id) if a.risk_score_id else None,
            "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            "metadata": a.metadata_col,
        }
        for a in rows
    ]
