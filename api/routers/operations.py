from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agents.operations.agent import OperationsAgent
from api.database import get_db
from api.models.bed_forecast import BedForecast

router = APIRouter(prefix="/operations", tags=["operations"])


@router.post("/forecast")
def run_forecast(db: Session = Depends(get_db)):
    """Run the Operations Agent: forecast bed demand for the next 7 days."""
    agent = OperationsAgent(db=db)
    result = agent.run()
    return {
        "upserted": result.upserted,
        "capacity": result.capacity,
        "method": result.method,
        "bottlenecks": result.bottlenecks,
        "forecasts": [
            {
                "date": str(f.date),
                "predicted_admissions": f.predicted_admissions,
                "predicted_occupancy": f.predicted_occupancy,
                "capacity": f.capacity,
                "status": f.status,
                "method": f.method,
            }
            for f in result.forecasts
        ],
    }


@router.get("/forecasts")
def get_forecasts(db: Session = Depends(get_db)):
    """Return all stored bed forecasts ordered by date."""
    rows = db.query(BedForecast).order_by(BedForecast.forecast_date).all()
    return [
        {
            "id": str(r.id),
            "forecast_date": str(r.forecast_date),
            "predicted_occupancy": float(r.predicted_occupancy),
            "capacity": r.capacity,
            "status": r.status,
            "model_method": r.model_method,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
