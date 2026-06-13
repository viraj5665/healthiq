from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.database import get_db

router = APIRouter(tags=["system"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "ok"
    db_latency_ms = None
    try:
        t0 = datetime.now(timezone.utc)
        db.execute(text("SELECT 1"))
        db_latency_ms = round((datetime.now(timezone.utc) - t0).total_seconds() * 1000, 2)
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.1.0",
        "services": {
            "database": {"status": db_status, "latency_ms": db_latency_ms},
        },
    }
