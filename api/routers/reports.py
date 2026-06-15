from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agents.nlp.extractor import MissingAPIKeyError
from agents.reporting.agent import ReportingAgent
from agents.reporting.gatherer import gather_summary
from api.config import settings
from api.database import get_db
from api.models.report import Report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate")
def generate_report(db: Session = Depends(get_db)):
    """Run the Reporting Agent: gather data, call Claude, store the markdown report."""
    try:
        agent = ReportingAgent(db=db, api_key=settings.anthropic_api_key)
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = agent.run()

    if result.error:
        raise HTTPException(
            status_code=502,
            detail=f"Report generation failed: {result.error}",
        )

    return {
        "report_id": result.report_id,
        "model": result.model,
        "duration_seconds": result.duration_seconds,
        "report_markdown": result.report_markdown,
        "summary_data": result.summary_data,
    }


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Return the current data summary snapshot without calling Claude."""
    return gather_summary(db)


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    """List all generated reports (metadata only, no markdown body)."""
    rows = db.query(Report).order_by(Report.generated_at.desc()).all()
    return [
        {
            "id": str(r.id),
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "model_version": r.model_version,
            "duration_seconds": float(r.duration_seconds) if r.duration_seconds else None,
        }
        for r in rows
    ]


@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    """Retrieve a specific report including its full markdown content."""
    row = db.query(Report).filter(Report.id == report_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return {
        "id": str(row.id),
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "model_version": row.model_version,
        "duration_seconds": float(row.duration_seconds) if row.duration_seconds else None,
        "report_markdown": row.report_markdown,
        "summary_data": row.summary_data,
    }
