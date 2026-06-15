"""
PHI de-identification helpers.

Current approach: deterministic SHA-256 hashing for identifiers that must
remain linkable (names, MRN), null-out for contact fields not needed for
analytics (address line, postal code, phone, email).

PRESIDIO HOOK — to swap in Microsoft Presidio:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    _analyzer = AnalyzerEngine()
    _anonymizer = AnonymizerEngine()

    def deidentify_text(text: str) -> str:
        results = _analyzer.analyze(text=text, language="en")
        return _anonymizer.anonymize(text=text, analyzer_results=results).text

Replace hash_identifier() calls with deidentify_text() and configure
operators per entity type (PERSON → replace, PHONE_NUMBER → redact, etc.).
"""

import hashlib
import os

_SALT = os.getenv("PHI_HASH_SALT", "healthiq-dev-v1")


def hash_identifier(value: str | None) -> str | None:
    """Deterministic pseudonymisation. Same input always yields same token."""
    if not value:
        return None
    digest = hashlib.sha256(f"{_SALT}:{value.strip()}".encode()).hexdigest()[:20]
    return f"PHI_{digest}"
