"""
Unit tests for the Reporting Agent.

All Claude API calls are mocked — no real ANTHROPIC_API_KEY required.
Tests cover:
  - gather_summary() data-gathering logic (mocked DB session)
  - ReportingAgent.run() happy path and error handling (mocked LLM)
  - MissingAPIKeyError guard
  - build_user_prompt() content coverage
"""

import json
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from agents.nlp.extractor import MissingAPIKeyError
from agents.reporting.gatherer import (
    _active_alerts,
    _bed_forecasts,
    _clinical_findings,
    _risk_distribution,
    gather_summary,
)
from agents.reporting.prompts import SYSTEM_PROMPT, build_user_prompt


# ── fixtures ───────────────────────────────────────────────────────────────────

SAMPLE_SUMMARY = {
    "generated_at": "2026-06-15T21:00:00+00:00",
    "risk_distribution": {"critical": 1, "high": 1, "moderate": 2, "low": 6, "total": 10},
    "active_alerts": {
        "by_severity": {"critical": 1, "urgent": 1, "warning": 0},
        "total": 2,
        "recent": [
            {
                "alert_type": "risk-threshold",
                "severity": "critical",
                "title": "Elevated readmission risk (critical)",
                "triggered_at": "2026-06-15T21:47:50+00:00",
            }
        ],
    },
    "bed_forecasts": [
        {"date": "2026-06-16", "predicted_occupancy": 1.0, "capacity": 20, "status": "normal", "model_method": "global_mean"},
    ],
    "clinical_findings": [
        {
            "note_type": "progress_note",
            "note_date": "2024-03-05T00:00:00+00:00",
            "is_synthetic": True,
            "diagnoses": [{"description": "Type 2 Diabetes", "icd10_code": "E11.65"}],
            "medications": ["Metformin"],
            "clinical_events": ["HbA1c 9.4% — elevated"],
        }
    ],
}

MOCK_REPORT_MD = """## HealthIQ Weekly Platform Summary

### Overview
Ten patients are currently tracked...

## Recommended Actions
- Monitor 2 critical/urgent alerts immediately.
"""


# ── gather_summary helpers ─────────────────────────────────────────────────────

def _db_with_risk_rows(rows):
    """Build a mock DB whose risk_scores query returns given (level, count) rows."""
    db = MagicMock()
    db.query.return_value.group_by.return_value.all.return_value = rows
    return db


def test_risk_distribution_counts():
    db = MagicMock()
    db.query.return_value.group_by.return_value.all.return_value = [
        ("critical", 2), ("high", 3), ("low", 5)
    ]
    result = _risk_distribution(db)
    assert result["critical"] == 2
    assert result["high"] == 3
    assert result["low"] == 5
    assert result["moderate"] == 0  # not in rows, defaults to 0


def test_risk_distribution_total():
    db = MagicMock()
    db.query.return_value.group_by.return_value.all.return_value = [
        ("critical", 1), ("high", 2), ("moderate", 3), ("low", 4)
    ]
    result = _risk_distribution(db)
    assert result["total"] == 10


def test_risk_distribution_empty():
    db = MagicMock()
    db.query.return_value.group_by.return_value.all.return_value = []
    result = _risk_distribution(db)
    assert result["total"] == 0
    assert result["critical"] == 0


def test_active_alerts_by_severity():
    db = MagicMock()
    # First query: group by severity
    mock_inner = MagicMock()
    mock_inner.filter.return_value.group_by.return_value.all.return_value = [
        ("critical", 1), ("urgent", 2)
    ]
    mock_inner.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    db.query.return_value = mock_inner

    result = _active_alerts(db)
    assert result["by_severity"]["critical"] == 1
    assert result["by_severity"]["urgent"] == 2
    assert result["by_severity"]["warning"] == 0


def test_active_alerts_total():
    db = MagicMock()
    mock_inner = MagicMock()
    mock_inner.filter.return_value.group_by.return_value.all.return_value = [
        ("critical", 3), ("urgent", 1), ("warning", 2)
    ]
    mock_inner.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    db.query.return_value = mock_inner
    result = _active_alerts(db)
    assert result["total"] == 6


def test_bed_forecasts_shape():
    db = MagicMock()
    bf = MagicMock()
    bf.forecast_date = date(2026, 6, 16)
    bf.predicted_occupancy = Decimal("1.0")
    bf.capacity = 20
    bf.status = "normal"
    bf.model_method = "global_mean"
    db.query.return_value.order_by.return_value.all.return_value = [bf]

    result = _bed_forecasts(db)
    assert len(result) == 1
    assert result[0]["date"] == "2026-06-16"
    assert result[0]["predicted_occupancy"] == 1.0
    assert result[0]["status"] == "normal"


def test_bed_forecasts_empty():
    db = MagicMock()
    db.query.return_value.order_by.return_value.all.return_value = []
    result = _bed_forecasts(db)
    assert result == []


def test_clinical_findings_extraction():
    db = MagicMock()
    note = MagicMock()
    note.note_type = "progress_note"
    note.note_date = datetime(2024, 3, 5, tzinfo=timezone.utc)
    note.is_synthetic = True
    note.extracted_entities = {
        "diagnoses": [{"description": "Type 2 Diabetes", "icd10_code": "E11.65"}],
        "medications": [{"name": "Metformin", "dosage": "1000mg", "frequency": "bid", "route": "oral"}],
        "clinical_events": [{"description": "HbA1c 9.4%", "event_type": "lab_result", "date_mentioned": None}],
    }
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [note]

    result = _clinical_findings(db)
    assert len(result) == 1
    assert result[0]["note_type"] == "progress_note"
    assert result[0]["diagnoses"][0]["icd10_code"] == "E11.65"
    assert "Metformin" in result[0]["medications"]
    assert "HbA1c 9.4%" in result[0]["clinical_events"]


def test_clinical_findings_empty_entities():
    db = MagicMock()
    note = MagicMock()
    note.note_type = "progress_note"
    note.note_date = datetime(2024, 3, 5, tzinfo=timezone.utc)
    note.is_synthetic = True
    note.extracted_entities = {}
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [note]

    result = _clinical_findings(db)
    assert result[0]["diagnoses"] == []
    assert result[0]["medications"] == []


def test_clinical_findings_no_notes():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    assert _clinical_findings(db) == []


# ── gather_summary structure ───────────────────────────────────────────────────

def test_gather_summary_has_required_keys():
    db = MagicMock()
    # Patch all four helpers so we don't need a fully wired mock DB
    with (
        patch("agents.reporting.gatherer._risk_distribution", return_value={"total": 0}),
        patch("agents.reporting.gatherer._active_alerts", return_value={"total": 0, "by_severity": {}, "recent": []}),
        patch("agents.reporting.gatherer._bed_forecasts", return_value=[]),
        patch("agents.reporting.gatherer._clinical_findings", return_value=[]),
    ):
        result = gather_summary(db)

    assert "generated_at" in result
    assert "risk_distribution" in result
    assert "active_alerts" in result
    assert "bed_forecasts" in result
    assert "clinical_findings" in result


def test_gather_summary_generated_at_is_iso():
    db = MagicMock()
    with (
        patch("agents.reporting.gatherer._risk_distribution", return_value={}),
        patch("agents.reporting.gatherer._active_alerts", return_value={}),
        patch("agents.reporting.gatherer._bed_forecasts", return_value=[]),
        patch("agents.reporting.gatherer._clinical_findings", return_value=[]),
    ):
        result = gather_summary(db)
    # Should be parseable as ISO datetime
    datetime.fromisoformat(result["generated_at"])


# ── prompts ───────────────────────────────────────────────────────────────────

def test_system_prompt_forbids_invention():
    assert "EXCLUSIVELY" in SYSTEM_PROMPT
    assert "Do NOT invent" in SYSTEM_PROMPT


def test_system_prompt_requires_recommended_actions():
    assert "Recommended Actions" in SYSTEM_PROMPT


def test_build_user_prompt_includes_json_data():
    prompt = build_user_prompt(SAMPLE_SUMMARY)
    assert "risk_distribution" in prompt
    assert "active_alerts" in prompt
    assert "bed_forecasts" in prompt
    assert "clinical_findings" in prompt


def test_build_user_prompt_embeds_json_fence():
    prompt = build_user_prompt(SAMPLE_SUMMARY)
    assert "```json" in prompt


def test_build_user_prompt_numbers_serialised():
    prompt = build_user_prompt(SAMPLE_SUMMARY)
    assert '"total": 10' in prompt


# ── ReportingAgent ─────────────────────────────────────────────────────────────

def _make_agent(response_text: str = MOCK_REPORT_MD):
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()

    # Patch gather_summary so we don't need a fully wired DB mock
    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        with patch("agents.reporting.agent.ChatAnthropic") as MockLLM:
            mock_llm_instance = MagicMock()
            mock_llm_instance.invoke.return_value = MagicMock(content=response_text)
            MockLLM.return_value = mock_llm_instance

            from agents.reporting.agent import ReportingAgent
            agent = ReportingAgent(db=db, api_key="sk-ant-real-key-test")
            agent._llm = mock_llm_instance
    return agent, db


def test_missing_key_raises():
    db = MagicMock()
    with pytest.raises(MissingAPIKeyError):
        from agents.reporting.agent import ReportingAgent
        ReportingAgent(db=db, api_key="sk-ant-your-key-here")


def test_empty_key_raises():
    db = MagicMock()
    with pytest.raises(MissingAPIKeyError):
        from agents.reporting.agent import ReportingAgent
        ReportingAgent(db=db, api_key="")


def test_run_returns_report_result():
    from agents.reporting.agent import ReportResult
    agent, db = _make_agent()
    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        result = agent.run()
    assert isinstance(result, ReportResult)


def test_run_report_markdown_contains_content():
    agent, db = _make_agent()
    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        result = agent.run()
    assert "HealthIQ" in result.report_markdown or len(result.report_markdown) > 10


def test_run_calls_llm_once():
    agent, db = _make_agent()
    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        agent.run()
    agent._llm.invoke.assert_called_once()


def test_run_persists_to_db():
    agent, db = _make_agent()
    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        agent.run()
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_run_duration_positive():
    agent, db = _make_agent()
    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        result = agent.run()
    assert result.duration_seconds >= 0


def test_run_summary_data_populated():
    agent, db = _make_agent()
    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        result = agent.run()
    assert result.summary_data == SAMPLE_SUMMARY


def test_run_error_when_llm_raises():
    db = MagicMock()
    with patch("agents.reporting.agent.ChatAnthropic") as MockLLM:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = RuntimeError("API timeout")
        MockLLM.return_value = mock_llm_instance
        from agents.reporting.agent import ReportingAgent
        agent = ReportingAgent(db=db, api_key="sk-ant-real-key-test")
        agent._llm = mock_llm_instance

    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        result = agent.run()

    assert result.error is not None
    assert "API timeout" in result.error
    db.add.assert_not_called()  # should not persist on error


def test_run_no_db_write_on_error():
    db = MagicMock()
    with patch("agents.reporting.agent.ChatAnthropic") as MockLLM:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = Exception("timeout")
        MockLLM.return_value = mock_llm_instance
        from agents.reporting.agent import ReportingAgent
        agent = ReportingAgent(db=db, api_key="sk-ant-real-key-test")
        agent._llm = mock_llm_instance

    with patch("agents.reporting.agent.gather_summary", return_value=SAMPLE_SUMMARY):
        agent.run()

    db.commit.assert_not_called()
