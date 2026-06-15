import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from agents.ingestion.agent import IngestionAgent, IngestionConfig
from agents.ingestion.synthea_agent import SyntheaIngestionAgent
from api.config import settings
from api.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingestion"])

_DEFAULT_SYNTHEA_DIR = "/app/data/synthea/output/fhir"


@router.post("/run")
def run_ingestion(
    patient_count: int = 10,
    encounter_count: int = 20,
    observation_count: int = 50,
    db: Session = Depends(get_db),
):
    """Ingest patients from the live HAPI FHIR server."""
    config = IngestionConfig(
        fhir_server_url=settings.fhir_server_url,
        patient_count=patient_count,
        encounter_count=encounter_count,
        observation_count=observation_count,
    )
    summary = IngestionAgent(config, db).run()
    return asdict(summary)


@router.post("/synthea")
def run_synthea_ingestion(
    bundle_dir: str = Query(default=_DEFAULT_SYNTHEA_DIR, description="Path to Synthea FHIR bundle directory"),
    db: Session = Depends(get_db),
):
    """
    Ingest Synthea-generated FHIR R4 bundle JSON files from disk.

    Processes Patient, Encounter, Observation, Condition, and MedicationRequest
    resources. All Patient PHI is de-identified using the same SHA-256 hashing
    as the live HAPI ingestion path. Idempotent — re-running skips already-
    ingested resources by fhir_id.
    """
    try:
        agent = SyntheaIngestionAgent(db=db, bundle_dir=bundle_dir)
        summary = agent.run()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Synthea ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    return {
        "bundle_files_processed": summary.bundle_files,
        "duration_seconds": summary.duration_seconds,
        "patients": asdict(summary.patients),
        "encounters": asdict(summary.encounters),
        "observations": asdict(summary.observations),
        "conditions": asdict(summary.conditions),
        "medications": asdict(summary.medications),
        "errors": len(summary.error_log),
        "error_sample": summary.error_log[:5] if summary.error_log else [],
    }
