from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.nlp.agent import NLPAgent
from agents.nlp.extractor import MissingAPIKeyError
from agents.nlp.seed import seed_synthetic_notes
from api.config import settings
from api.database import get_db
from api.models.clinical_note import ClinicalNote

router = APIRouter(prefix="/nlp", tags=["nlp"])


@router.post("/seed-synthetic")
def seed_notes(db: Session = Depends(get_db)):
    """Insert 5 synthetic clinical notes linked to existing patients (idempotent)."""
    ids = seed_synthetic_notes(db)
    return {"seeded_note_ids": ids, "count": len(ids)}


@router.post("/extract/{note_id}")
def extract_note(note_id: str, db: Session = Depends(get_db)):
    """Run NLP extraction on a clinical note and persist the result."""
    note = db.query(ClinicalNote).filter(ClinicalNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")

    try:
        agent = NLPAgent(api_key=settings.anthropic_api_key)
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = agent.run(note_id=note_id, note_text=note.note_text)

    if result.error:
        raise HTTPException(status_code=502, detail=f"Extraction failed: {result.error}")

    note.extracted_entities = result.extraction.model_dump()
    note.extraction_model = result.model
    note.extracted_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "note_id": note_id,
        "patient_id": str(note.patient_id),
        "model": result.model,
        "duration_seconds": result.duration_seconds,
        "extracted_entities": result.extraction.model_dump(),
    }


@router.get("/notes/{patient_id}")
def get_patient_notes(patient_id: str, db: Session = Depends(get_db)):
    """Return all clinical notes for a patient, including extracted entities."""
    notes = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.patient_id == patient_id)
        .order_by(ClinicalNote.note_date.desc())
        .all()
    )
    return [
        {
            "id": str(n.id),
            "patient_id": str(n.patient_id),
            "note_type": n.note_type,
            "note_date": n.note_date.isoformat() if n.note_date else None,
            "is_synthetic": n.is_synthetic,
            "extracted_entities": n.extracted_entities,
            "extraction_model": n.extraction_model,
            "extracted_at": n.extracted_at.isoformat() if n.extracted_at else None,
            "note_preview": n.note_text[:200] + "…" if len(n.note_text) > 200 else n.note_text,
        }
        for n in notes
    ]
