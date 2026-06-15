import logging
import time
import uuid
from dataclasses import asdict, dataclass, field

from sqlalchemy.orm import Session

from agents.ingestion.fhir_client import FHIRClient
from agents.ingestion.mapper import map_encounter, map_observation, map_patient
from api.models.encounter import Encounter
from api.models.observation import Observation
from api.models.patient import Patient

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    fhir_server_url: str
    patient_count: int = 10
    encounter_count: int = 20
    observation_count: int = 50


@dataclass
class ResourceSummary:
    fetched: int = 0
    inserted: int = 0
    skipped: int = 0
    errors: int = 0


@dataclass
class IngestionSummary:
    patients: ResourceSummary = field(default_factory=ResourceSummary)
    encounters: ResourceSummary = field(default_factory=ResourceSummary)
    observations: ResourceSummary = field(default_factory=ResourceSummary)
    duration_seconds: float = 0.0
    error_log: list[str] = field(default_factory=list)


class IngestionAgent:
    def __init__(self, config: IngestionConfig, db: Session) -> None:
        self.config = config
        self.db = db

    def run(self) -> IngestionSummary:
        t0 = time.monotonic()
        summary = IngestionSummary()

        with FHIRClient(self.config.fhir_server_url) as client:
            patient_map = self._ingest_patients(client, summary)
            encounter_map = self._ingest_encounters(client, summary, patient_map)
            self._ingest_observations(client, summary, patient_map, encounter_map)

        summary.duration_seconds = round(time.monotonic() - t0, 2)
        return summary

    # ── private helpers ────────────────────────────────────────────────────────

    def _ingest_patients(self, client: FHIRClient, summary: IngestionSummary) -> dict[str, str]:
        """Returns {fhir_id: db_uuid_str}."""
        fhir_to_db: dict[str, str] = {}
        try:
            resources = client.fetch_patients(self.config.patient_count)
        except Exception as exc:
            summary.error_log.append(f"Patient fetch: {exc}")
            return fhir_to_db

        summary.patients.fetched = len(resources)
        for resource in resources:
            try:
                db_id = self._upsert(Patient, map_patient(resource), "fhir_id", summary.patients)
                if db_id:
                    fhir_to_db[resource["id"]] = str(db_id)
            except Exception as exc:
                summary.patients.errors += 1
                summary.error_log.append(f"Patient {resource.get('id')}: {exc}")
                self.db.rollback()
        self.db.commit()
        return fhir_to_db

    def _ingest_encounters(
        self, client: FHIRClient, summary: IngestionSummary, patient_map: dict[str, str]
    ) -> dict[str, str]:
        fhir_to_db: dict[str, str] = {}
        if not patient_map:
            return fhir_to_db
        try:
            per_patient = max(1, self.config.encounter_count // len(patient_map))
            resources = client.fetch_encounters_for_patients(list(patient_map.keys()), per_patient)
        except Exception as exc:
            summary.error_log.append(f"Encounter fetch: {exc}")
            return fhir_to_db

        summary.encounters.fetched = len(resources)
        for resource in resources:
            try:
                mapped = map_encounter(resource, patient_map)
                if mapped is None:
                    summary.encounters.skipped += 1
                    continue
                db_id = self._upsert(Encounter, mapped, "fhir_id", summary.encounters)
                if db_id:
                    fhir_to_db[resource["id"]] = str(db_id)
            except Exception as exc:
                summary.encounters.errors += 1
                summary.error_log.append(f"Encounter {resource.get('id')}: {exc}")
                self.db.rollback()
        self.db.commit()
        return fhir_to_db

    def _ingest_observations(
        self,
        client: FHIRClient,
        summary: IngestionSummary,
        patient_map: dict[str, str],
        encounter_map: dict[str, str],
    ) -> None:
        if not patient_map:
            return
        try:
            per_patient = max(1, self.config.observation_count // len(patient_map))
            resources = client.fetch_observations_for_patients(list(patient_map.keys()), per_patient)
        except Exception as exc:
            summary.error_log.append(f"Observation fetch: {exc}")
            return

        summary.observations.fetched = len(resources)
        for resource in resources:
            try:
                mapped = map_observation(resource, patient_map, encounter_map)
                if mapped is None:
                    summary.observations.skipped += 1
                    continue
                self._upsert(Observation, mapped, "fhir_id", summary.observations)
            except Exception as exc:
                summary.observations.errors += 1
                summary.error_log.append(f"Observation {resource.get('id')}: {exc}")
                self.db.rollback()
        self.db.commit()

    def _upsert(self, model, row: dict, unique_field: str, summary: ResourceSummary) -> uuid.UUID | None:
        fhir_id = row.get(unique_field)
        existing = self.db.query(model).filter(
            getattr(model, unique_field) == fhir_id
        ).first()
        if existing:
            summary.skipped += 1
            return existing.id
        obj = model(**row)
        self.db.add(obj)
        self.db.flush()
        summary.inserted += 1
        return obj.id
