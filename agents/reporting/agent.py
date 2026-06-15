"""
Reporting Agent — generates a markdown weekly summary report for hospital administrators.

Uses the Claude API (claude-haiku-4-5-20251001) to synthesise the data snapshot
collected by gatherer.gather_summary() into a readable narrative report.

Same pattern as the NLP Agent (Day 4):
  - MissingAPIKeyError raised at construction time if key is placeholder/empty
  - LLM call is isolated so unit tests can mock ChatAnthropic
  - Report persisted to the reports table after generation
"""

import logging
import time
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from agents.nlp.extractor import MissingAPIKeyError
from agents.reporting.gatherer import gather_summary
from agents.reporting.prompts import SYSTEM_PROMPT, build_user_prompt
from api.models.report import Report

logger = logging.getLogger(__name__)

_PLACEHOLDER_KEY = "sk-ant-your-key-here"
_DEFAULT_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class ReportResult:
    report_id: str | None
    report_markdown: str
    summary_data: dict
    model: str
    duration_seconds: float
    error: str | None = None


class ReportingAgent:
    def __init__(self, db: Session, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        if not api_key or api_key == _PLACEHOLDER_KEY:
            raise MissingAPIKeyError(
                "ANTHROPIC_API_KEY is not set. Add your real key to .env and "
                "restart the API container: docker compose restart api"
            )
        self._db = db
        self.model = model
        self._llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0.3,   # slight creativity for prose, still grounded
            max_tokens=3000,
        )

    def run(self) -> ReportResult:
        t0 = time.monotonic()
        summary = gather_summary(self._db)
        result = ReportResult(
            report_id=None,
            report_markdown="",
            summary_data=summary,
            model=self.model,
            duration_seconds=0.0,
        )
        try:
            result.report_markdown = self._call_llm(summary)
        except Exception as exc:
            result.error = str(exc)
            logger.exception("Reporting Agent LLM call failed")
            result.duration_seconds = round(time.monotonic() - t0, 2)
            return result

        result.duration_seconds = round(time.monotonic() - t0, 2)
        report_row = Report(
            report_markdown=result.report_markdown,
            summary_data=summary,
            model_version=self.model,
            duration_seconds=result.duration_seconds,
        )
        self._db.add(report_row)
        self._db.commit()
        self._db.refresh(report_row)
        result.report_id = str(report_row.id)
        return result

    def _call_llm(self, summary: dict) -> str:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=build_user_prompt(summary)),
        ]
        logger.info("Calling %s to generate weekly report", self.model)
        response = self._llm.invoke(messages)
        return response.content.strip()
