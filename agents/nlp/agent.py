import logging
import time
from dataclasses import dataclass, field

from agents.nlp.extractor import ClinicalExtractor, MissingAPIKeyError
from agents.nlp.schema import ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class NLPResult:
    note_id: str
    extraction: ExtractionResult | None = None
    model: str = ""
    duration_seconds: float = 0.0
    error: str | None = None


class NLPAgent:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self.extractor = ClinicalExtractor(api_key=api_key, model=model)

    def run(self, note_id: str, note_text: str) -> NLPResult:
        t0 = time.monotonic()
        result = NLPResult(note_id=note_id, model=self.extractor.model)
        try:
            result.extraction = self.extractor.extract(note_text)
        except Exception as exc:
            result.error = str(exc)
            logger.exception("NLP extraction failed for note %s", note_id)
        result.duration_seconds = round(time.monotonic() - t0, 2)
        return result
