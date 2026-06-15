"""
Data gatherer for the Reporting Agent — pure DB-query logic, no LLM.

Keeping this separate from agent.py makes it unit-testable with mock
sessions without touching the LLM layer.
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.alert import Alert
from api.models.bed_forecast import BedForecast
from api.models.clinical_note import ClinicalNote
from api.models.risk_score import RiskScore


def gather_summary(db: Session) -> dict:
    """
    Collect a structured snapshot of the current platform state.

    Returns a dict with four sections:
      - risk_distribution: counts by risk level
      - active_alerts: counts by severity + 5 most-recent details
      - bed_forecasts: all stored forecasts ordered by date
      - clinical_findings: up to 3 most-recent extracted notes (with entities)
    """
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "risk_distribution": _risk_distribution(db),
        "active_alerts": _active_alerts(db),
        "bed_forecasts": _bed_forecasts(db),
        "clinical_findings": _clinical_findings(db),
    }


# ── private helpers ────────────────────────────────────────────────────────────

def _risk_distribution(db: Session) -> dict:
    rows = (
        db.query(RiskScore.risk_level, func.count(RiskScore.id))
        .group_by(RiskScore.risk_level)
        .all()
    )
    dist = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
    for level, count in rows:
        if level in dist:
            dist[level] = count
    dist["total"] = sum(dist.values())
    return dist


def _active_alerts(db: Session) -> dict:
    rows = (
        db.query(Alert.severity, func.count(Alert.id))
        .filter(Alert.status == "active")
        .group_by(Alert.severity)
        .all()
    )
    by_severity = {"critical": 0, "urgent": 0, "warning": 0}
    for severity, count in rows:
        if severity in by_severity:
            by_severity[severity] = count

    recent = (
        db.query(Alert)
        .filter(Alert.status == "active")
        .order_by(Alert.triggered_at.desc())
        .limit(5)
        .all()
    )
    return {
        "by_severity": by_severity,
        "total": sum(by_severity.values()),
        "recent": [
            {
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
            }
            for a in recent
        ],
    }


def _bed_forecasts(db: Session) -> list[dict]:
    rows = db.query(BedForecast).order_by(BedForecast.forecast_date).all()
    return [
        {
            "date": str(r.forecast_date),
            "predicted_occupancy": float(r.predicted_occupancy),
            "capacity": r.capacity,
            "status": r.status,
            "model_method": r.model_method,
        }
        for r in rows
    ]


def _clinical_findings(db: Session) -> list[dict]:
    notes = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.extracted_entities.isnot(None))
        .order_by(ClinicalNote.note_date.desc())
        .limit(3)
        .all()
    )
    findings = []
    for n in notes:
        entities = n.extracted_entities or {}
        findings.append(
            {
                "note_type": n.note_type,
                "note_date": n.note_date.isoformat() if n.note_date else None,
                "is_synthetic": n.is_synthetic,
                "diagnoses": [
                    {"description": d.get("description"), "icd10_code": d.get("icd10_code")}
                    for d in entities.get("diagnoses", [])
                ],
                "medications": [m.get("name") for m in entities.get("medications", [])],
                "clinical_events": [
                    e.get("description") for e in entities.get("clinical_events", [])
                ],
            }
        )
    return findings
