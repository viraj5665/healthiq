from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agents.ingestion.agent import IngestionAgent, IngestionConfig
from api.config import settings
from api.database import get_db

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/run")
def run_ingestion(
    patient_count: int = 10,
    encounter_count: int = 20,
    observation_count: int = 50,
    db: Session = Depends(get_db),
):
    config = IngestionConfig(
        fhir_server_url=settings.fhir_server_url,
        patient_count=patient_count,
        encounter_count=encounter_count,
        observation_count=observation_count,
    )
    summary = IngestionAgent(config, db).run()
    return asdict(summary)
