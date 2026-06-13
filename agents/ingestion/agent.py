"""
Ingestion Agent — pulls FHIR R4 resources (Patient, Encounter, Observation)
from a FHIR server and persists them to PostgreSQL.

Day 1 stub: structure only. Implementation in Day 2.
"""
from dataclasses import dataclass


@dataclass
class IngestionConfig:
    fhir_server_url: str
    batch_size: int = 100


class IngestionAgent:
    def __init__(self, config: IngestionConfig) -> None:
        self.config = config

    def run(self) -> None:
        raise NotImplementedError("Implemented in Day 2")
