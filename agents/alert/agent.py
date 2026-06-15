"""
Alert Agent — monitors risk scores and bed forecasts for threshold breaches.

Severity mapping:
  risk_level critical  → alert severity "critical"
  risk_level high      → alert severity "urgent"
  risk_level moderate  → alert severity "warning"

  bed status critical  → alert severity "critical"
  bed status warning   → alert severity "warning"

Deduplication:
  - Risk alerts: one active alert per risk_score row (checked via risk_score_id).
  - Bed alerts:  one active alert per forecast_date (stored in metadata).

Future integration points (⚠ NOT implemented here — log-only for now):
  - PagerDuty: POST /incidents for critical/urgent alerts
  - Twilio SMS: send_message() for on-call team
  - Slack webhook: notify #clinical-ops channel
"""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from api.models.alert import Alert
from api.models.bed_forecast import BedForecast
from api.models.risk_score import RiskScore

_RISK_SEVERITY = {
    "critical": "critical",
    "high": "urgent",
    "moderate": "warning",
}

_BED_SEVERITY = {
    "critical": "critical",
    "warning": "warning",
}


@dataclass
class AlertResult:
    created: int
    skipped_duplicates: int
    risk_alerts: int
    bed_alerts: int
    alert_ids: list[str] = field(default_factory=list)


class AlertAgent:
    def __init__(self, db: Session):
        self._db = db

    def run(self) -> AlertResult:
        result = AlertResult(created=0, skipped_duplicates=0, risk_alerts=0, bed_alerts=0)
        self._check_risk_scores(result)
        self._check_bed_forecasts(result)
        self._db.commit()
        return result

    # ── risk score monitoring ──────────────────────────────────────────────────

    def _check_risk_scores(self, result: AlertResult) -> None:
        scores = (
            self._db.query(RiskScore)
            .filter(RiskScore.risk_level.in_(["critical", "high", "moderate"]))
            .all()
        )
        for score in scores:
            severity = _RISK_SEVERITY.get(score.risk_level)
            if not severity:
                continue
            if self._risk_alert_exists(score.id):
                result.skipped_duplicates += 1
                continue
            alert = Alert(
                patient_id=score.patient_id,
                risk_score_id=score.id,
                alert_type="risk-threshold",
                severity=severity,
                title=f"Elevated readmission risk ({score.risk_level})",
                message=(
                    f"Risk score {float(score.score):.2%} — level: {score.risk_level}. "
                    f"Model: {score.model_version}. Top features available in risk score record."
                ),
                status="active",
                metadata_col={"risk_score": float(score.score), "risk_level": score.risk_level},
            )
            self._db.add(alert)
            self._db.flush()
            result.alert_ids.append(str(alert.id))
            result.created += 1
            result.risk_alerts += 1

    def _risk_alert_exists(self, risk_score_id) -> bool:
        return (
            self._db.query(Alert)
            .filter(
                Alert.risk_score_id == risk_score_id,
                Alert.status == "active",
            )
            .first()
        ) is not None

    # ── bed forecast monitoring ────────────────────────────────────────────────

    def _check_bed_forecasts(self, result: AlertResult) -> None:
        forecasts = (
            self._db.query(BedForecast)
            .filter(BedForecast.status.in_(["warning", "critical"]))
            .all()
        )
        for forecast in forecasts:
            severity = _BED_SEVERITY.get(forecast.status)
            if not severity:
                continue
            if self._bed_alert_exists(forecast.forecast_date):
                result.skipped_duplicates += 1
                continue
            alert = Alert(
                patient_id=None,
                alert_type="bed-capacity",
                severity=severity,
                title=f"Bed capacity {forecast.status}: {forecast.forecast_date}",
                message=(
                    f"Forecasted occupancy {float(forecast.predicted_occupancy):.1f} / "
                    f"{forecast.capacity} beds on {forecast.forecast_date}."
                ),
                status="active",
                metadata_col={
                    "forecast_date": str(forecast.forecast_date),
                    "predicted_occupancy": float(forecast.predicted_occupancy),
                    "capacity": forecast.capacity,
                },
            )
            self._db.add(alert)
            self._db.flush()
            result.alert_ids.append(str(alert.id))
            result.created += 1
            result.bed_alerts += 1

    def _bed_alert_exists(self, forecast_date: date) -> bool:
        """Check for active bed-capacity alert on the same forecast_date."""
        existing = (
            self._db.query(Alert)
            .filter(
                Alert.alert_type == "bed-capacity",
                Alert.status == "active",
            )
            .all()
        )
        for a in existing:
            if a.metadata_col and a.metadata_col.get("forecast_date") == str(forecast_date):
                return True
        return False
