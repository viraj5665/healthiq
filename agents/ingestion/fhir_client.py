import logging

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_HEADERS = {"Accept": "application/fhir+json"}


class FHIRClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=_TIMEOUT, headers=_HEADERS)

    def _fetch_page(self, resource_type: str, count: int, extra_params: dict | None = None) -> list[dict]:
        url = f"{self.base_url}/{resource_type}"
        params = {"_count": count, "_format": "json", **(extra_params or {})}
        resp = self._http.get(url, params=params)
        resp.raise_for_status()
        bundle = resp.json()
        resources = [
            entry["resource"]
            for entry in bundle.get("entry", [])
            if "resource" in entry and entry["resource"].get("id")
        ]
        logger.info("FHIR %s: fetched %d resources", resource_type, len(resources))
        return resources

    def fetch_patients(self, count: int = 10) -> list[dict]:
        return self._fetch_page("Patient", count)

    def fetch_encounters_for_patients(self, patient_fhir_ids: list[str], per_patient: int = 3) -> list[dict]:
        """Fetch encounters scoped to the given patients so FK links are guaranteed."""
        results: list[dict] = []
        for pid in patient_fhir_ids:
            try:
                page = self._fetch_page("Encounter", per_patient, extra_params={"subject": f"Patient/{pid}"})
                results.extend(page)
            except Exception:
                logger.warning("Encounter fetch failed for patient %s", pid)
        return results

    def fetch_observations_for_patients(self, patient_fhir_ids: list[str], per_patient: int = 5) -> list[dict]:
        """Fetch observations scoped to the given patients."""
        results: list[dict] = []
        for pid in patient_fhir_ids:
            try:
                page = self._fetch_page("Observation", per_patient, extra_params={"subject": f"Patient/{pid}"})
                results.extend(page)
            except Exception:
                logger.warning("Observation fetch failed for patient %s", pid)
        return results

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
