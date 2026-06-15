"""
ClinicalExtractor: wraps the Claude API call and JSON parsing.

Keeping the LLM call and the parse step separate lets us unit-test
parse_response() with fixture strings without mocking the LLM.
"""

import json
import logging
import re

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from agents.nlp.prompts import NOTE_TEMPLATE, SYSTEM_PROMPT
from agents.nlp.schema import ExtractionResult

logger = logging.getLogger(__name__)

_PLACEHOLDER_KEY = "sk-ant-your-key-here"


class MissingAPIKeyError(RuntimeError):
    pass


class ClinicalExtractor:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        if not api_key or api_key == _PLACEHOLDER_KEY:
            raise MissingAPIKeyError(
                "ANTHROPIC_API_KEY is not set. Add your real key to .env and "
                "restart the API container: docker compose restart api"
            )
        self.model = model
        self._llm = ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=0,
            max_tokens=2048,
        )

    def extract(self, note_text: str) -> ExtractionResult:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=NOTE_TEMPLATE.format(note_text=note_text)),
        ]
        logger.info("Sending note to %s for extraction (%d chars)", self.model, len(note_text))
        response = self._llm.invoke(messages)
        return self.parse_response(response.content)

    @staticmethod
    def parse_response(content: str) -> ExtractionResult:
        """Parse Claude's text response into ExtractionResult. Testable without LLM."""
        text = content.strip()
        # Strip markdown code fences if Claude wrapped the JSON
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        text = text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Claude did not return valid JSON: {exc}\nRaw: {text[:200]}") from exc
        return ExtractionResult.model_validate(data)
