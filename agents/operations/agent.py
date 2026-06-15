"""Operations Agent — bed demand forecasting and bottleneck detection."""

import os
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from agents.operations.forecaster import DayForecast, compute_forecasts
from api.models.bed_forecast import BedForecast
from api.models.encounter import Encounter

BED_CAPACITY = int(os.getenv("BED_CAPACITY", "20"))


@dataclass
class OperationsResult:
    forecasts: list[DayForecast]
    upserted: int
    bottlenecks: list[str]
    capacity: int
    method: str


class OperationsAgent:
    def __init__(self, db: Session, capacity: int = BED_CAPACITY):
        self._db = db
        self._capacity = capacity

    def run(self) -> OperationsResult:
        daily_counts, avg_los = self._pull_encounter_stats()
        forecasts = compute_forecasts(
            daily_counts=daily_counts,
            avg_los_days=avg_los,
            capacity=self._capacity,
        )
        upserted = self._upsert_forecasts(forecasts)
        bottlenecks = [
            f"{f.date}: predicted {f.predicted_occupancy:.1f}/{f.capacity} beds ({f.status})"
            for f in forecasts
            if f.status in ("warning", "critical")
        ]
        return OperationsResult(
            forecasts=forecasts,
            upserted=upserted,
            bottlenecks=bottlenecks,
            capacity=self._capacity,
            method=forecasts[0].method if forecasts else "no_data",
        )

    def _pull_encounter_stats(self) -> tuple[dict[date, int], float]:
        encounters = (
            self._db.query(Encounter)
            .filter(Encounter.start_time.isnot(None))
            .all()
        )
        daily_counts: dict[date, int] = {}
        total_los = 0.0
        los_count = 0

        for enc in encounters:
            day = enc.start_time.date()
            daily_counts[day] = daily_counts.get(day, 0) + 1

            if enc.end_time and enc.start_time:
                los = (enc.end_time - enc.start_time).total_seconds() / 86400
                if los > 0:
                    total_los += los
                    los_count += 1

        avg_los = (total_los / los_count) if los_count > 0 else 1.0
        return daily_counts, avg_los

    def _upsert_forecasts(self, forecasts: list[DayForecast]) -> int:
        count = 0
        for f in forecasts:
            existing = (
                self._db.query(BedForecast)
                .filter(BedForecast.forecast_date == f.date)
                .first()
            )
            if existing:
                existing.predicted_occupancy = f.predicted_occupancy
                existing.capacity = f.capacity
                existing.status = f.status
                existing.model_method = f.method
            else:
                self._db.add(
                    BedForecast(
                        forecast_date=f.date,
                        predicted_occupancy=f.predicted_occupancy,
                        capacity=f.capacity,
                        status=f.status,
                        model_method=f.method,
                    )
                )
            count += 1
        self._db.commit()
        return count
