"""
Unit tests for the Alert Agent — all tests use MagicMock DB sessions.
No real database required.
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

import pytest

from agents.alert.agent import AlertAgent, AlertResult, _BED_SEVERITY, _RISK_SEVERITY


# ── helpers ───────────────────────────────────────────────────────────────────

def _mock_risk_score(risk_level: str, score: float = 0.8):
    rs = MagicMock()
    rs.id = uuid.uuid4()
    rs.patient_id = uuid.uuid4()
    rs.risk_level = risk_level
    rs.score = Decimal(str(score))
    rs.model_version = "xgb-synthetic-v1"
    return rs


def _mock_bed_forecast(status: str, occupancy: float = 18.0, capacity: int = 20):
    from datetime import date
    bf = MagicMock()
    bf.forecast_date = date(2026, 6, 20)
    bf.status = status
    bf.predicted_occupancy = Decimal(str(occupancy))
    bf.capacity = capacity
    return bf


def _build_agent_with_mocks(risk_scores=None, bed_forecasts=None, existing_alerts=None):
    """
    Wire up a mock DB session so AlertAgent.run() exercises the logic
    without touching a real database.
    """
    db = MagicMock()
    alert_agent = AlertAgent(db=db)

    risk_scores = risk_scores or []
    bed_forecasts = bed_forecasts or []
    existing_alerts = existing_alerts or []

    # Each db.query(...).filter(...).all() call needs to return the right list.
    # We use side_effect to distinguish by the first model class queried.
    query_mock = MagicMock()
    filter_mock = MagicMock()
    all_mock = MagicMock()

    call_count = {"risk": 0, "bed": 0, "alert": 0}

    def query_side_effect(model):
        from api.models.alert import Alert
        from api.models.bed_forecast import BedForecast
        from api.models.risk_score import RiskScore

        inner = MagicMock()

        if model is RiskScore:
            inner.filter.return_value.all.return_value = risk_scores
        elif model is BedForecast:
            inner.filter.return_value.all.return_value = bed_forecasts
        elif model is Alert:
            # alert existence checks always return empty (no duplicates)
            inner.filter.return_value.first.return_value = None
            inner.filter.return_value.all.return_value = existing_alerts
        return inner

    db.query.side_effect = query_side_effect
    db.flush = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()

    return alert_agent, db


# ── severity mapping ──────────────────────────────────────────────────────────

def test_risk_severity_mapping():
    assert _RISK_SEVERITY["critical"] == "critical"
    assert _RISK_SEVERITY["high"] == "urgent"
    assert _RISK_SEVERITY["moderate"] == "warning"


def test_bed_severity_mapping():
    assert _BED_SEVERITY["critical"] == "critical"
    assert _BED_SEVERITY["warning"] == "warning"


# ── no data → no alerts ───────────────────────────────────────────────────────

def test_no_risk_scores_no_alerts():
    agent, db = _build_agent_with_mocks(risk_scores=[], bed_forecasts=[])
    result = agent.run()
    assert result.created == 0
    assert result.risk_alerts == 0


def test_no_bed_forecasts_no_bed_alerts():
    agent, db = _build_agent_with_mocks(risk_scores=[], bed_forecasts=[])
    result = agent.run()
    assert result.bed_alerts == 0


# ── risk score alerts ─────────────────────────────────────────────────────────

def test_critical_risk_creates_alert():
    agent, db = _build_agent_with_mocks(risk_scores=[_mock_risk_score("critical")])
    result = agent.run()
    assert result.risk_alerts == 1
    assert result.created == 1
    db.add.assert_called_once()


def test_high_risk_creates_urgent_alert():
    agent, db = _build_agent_with_mocks(risk_scores=[_mock_risk_score("high")])
    result = agent.run()
    added = db.add.call_args[0][0]
    assert added.severity == "urgent"
    assert added.alert_type == "risk-threshold"


def test_moderate_risk_creates_warning_alert():
    agent, db = _build_agent_with_mocks(risk_scores=[_mock_risk_score("moderate")])
    result = agent.run()
    added = db.add.call_args[0][0]
    assert added.severity == "warning"


def test_low_risk_no_alert():
    agent, db = _build_agent_with_mocks(risk_scores=[_mock_risk_score("low", score=0.1)])
    result = agent.run()
    assert result.risk_alerts == 0
    assert result.created == 0


def test_multiple_risk_scores_multiple_alerts():
    scores = [
        _mock_risk_score("critical"),
        _mock_risk_score("high"),
        _mock_risk_score("moderate"),
    ]
    agent, db = _build_agent_with_mocks(risk_scores=scores)
    result = agent.run()
    assert result.risk_alerts == 3
    assert result.created == 3


def test_risk_alert_has_patient_id():
    rs = _mock_risk_score("critical")
    agent, db = _build_agent_with_mocks(risk_scores=[rs])
    agent.run()
    added = db.add.call_args[0][0]
    assert added.patient_id == rs.patient_id


def test_risk_alert_has_risk_score_id():
    rs = _mock_risk_score("critical")
    agent, db = _build_agent_with_mocks(risk_scores=[rs])
    agent.run()
    added = db.add.call_args[0][0]
    assert added.risk_score_id == rs.id


def test_risk_alert_metadata_contains_score():
    rs = _mock_risk_score("critical", score=0.91)
    agent, db = _build_agent_with_mocks(risk_scores=[rs])
    agent.run()
    added = db.add.call_args[0][0]
    assert added.metadata_col["risk_score"] == pytest.approx(0.91)
    assert added.metadata_col["risk_level"] == "critical"


# ── bed forecast alerts ───────────────────────────────────────────────────────

def test_critical_bed_creates_alert():
    agent, db = _build_agent_with_mocks(bed_forecasts=[_mock_bed_forecast("critical", 22.0)])
    result = agent.run()
    assert result.bed_alerts == 1
    assert result.created == 1


def test_warning_bed_creates_warning_alert():
    agent, db = _build_agent_with_mocks(bed_forecasts=[_mock_bed_forecast("warning", 17.0)])
    result = agent.run()
    added = db.add.call_args[0][0]
    assert added.severity == "warning"
    assert added.alert_type == "bed-capacity"


def test_normal_bed_no_alert():
    agent, db = _build_agent_with_mocks(bed_forecasts=[_mock_bed_forecast("normal", 10.0)])
    result = agent.run()
    assert result.bed_alerts == 0


def test_bed_alert_patient_id_is_none():
    agent, db = _build_agent_with_mocks(bed_forecasts=[_mock_bed_forecast("critical")])
    agent.run()
    added = db.add.call_args[0][0]
    assert added.patient_id is None


def test_bed_alert_metadata_contains_forecast_date():
    agent, db = _build_agent_with_mocks(bed_forecasts=[_mock_bed_forecast("warning")])
    agent.run()
    added = db.add.call_args[0][0]
    assert "forecast_date" in added.metadata_col


def test_bed_alert_metadata_contains_occupancy():
    agent, db = _build_agent_with_mocks(bed_forecasts=[_mock_bed_forecast("warning", 16.0)])
    agent.run()
    added = db.add.call_args[0][0]
    assert added.metadata_col["predicted_occupancy"] == pytest.approx(16.0)


# ── deduplication ─────────────────────────────────────────────────────────────

def test_duplicate_risk_alert_skipped():
    rs = _mock_risk_score("critical")
    db = MagicMock()
    agent = AlertAgent(db=db)

    from api.models.alert import Alert
    from api.models.bed_forecast import BedForecast
    from api.models.risk_score import RiskScore

    def query_side_effect(model):
        inner = MagicMock()
        if model is RiskScore:
            inner.filter.return_value.all.return_value = [rs]
        elif model is BedForecast:
            inner.filter.return_value.all.return_value = []
        elif model is Alert:
            # Simulate an existing active alert for this risk_score_id
            existing = MagicMock()
            inner.filter.return_value.first.return_value = existing
            inner.filter.return_value.all.return_value = []
        return inner

    db.query.side_effect = query_side_effect
    db.commit = MagicMock()

    result = agent.run()
    assert result.skipped_duplicates == 1
    assert result.created == 0


# ── commit is always called ───────────────────────────────────────────────────

def test_commit_called_even_with_no_alerts():
    agent, db = _build_agent_with_mocks()
    agent.run()
    db.commit.assert_called_once()


# ── AlertResult structure ─────────────────────────────────────────────────────

def test_result_is_alert_result():
    agent, db = _build_agent_with_mocks()
    result = agent.run()
    assert isinstance(result, AlertResult)


def test_result_alert_ids_list():
    agent, db = _build_agent_with_mocks(risk_scores=[_mock_risk_score("critical")])
    result = agent.run()
    assert isinstance(result.alert_ids, list)
    assert len(result.alert_ids) == 1
