"""
Bed demand forecasting — pure functions, no DB dependency.

Strategy (documented openly as ⚠ SYNTHETIC / SPARSE DATA approach):
  - If fewer than SPARSE_THRESHOLD distinct days have admission data, fall
    back to a "global mean" forecast: all 7 days get the same predicted
    value equal to the mean daily admissions across all available history.
  - If enough history exists, use a 7-day trailing moving average of the
    last 14 data points (adequate for weekly seasonality).

Occupancy estimate = predicted_admissions × avg_los_days.
  This is a rough proxy for bed-days; a production system would use a
  census-based model that tracks concurrent occupancy, not just new
  admissions.

⚠ NOTE: With <5 real encounters in the DB the model will always fall back
  to "global_mean". The architecture is ready for real data — swap in
  Prophet or statsmodels when volume grows to >30 days of history.
"""

from dataclasses import dataclass
from datetime import date, timedelta

SPARSE_THRESHOLD = 14   # days with admission data required for moving average
WARNING_UTILIZATION = 0.80   # fraction of capacity → warning
CRITICAL_UTILIZATION = 1.00  # fraction of capacity → critical


@dataclass
class DayForecast:
    date: date
    predicted_admissions: float
    predicted_occupancy: float
    capacity: int
    status: str   # normal | warning | critical
    method: str   # global_mean | moving_average_7d | no_data


def classify_status(occupancy: float, capacity: int) -> str:
    if capacity <= 0:
        return "critical"
    util = occupancy / capacity
    if util >= CRITICAL_UTILIZATION:
        return "critical"
    if util >= WARNING_UTILIZATION:
        return "warning"
    return "normal"


def compute_forecasts(
    daily_counts: dict[date, int],
    avg_los_days: float,
    capacity: int = 20,
    horizon_days: int = 7,
    reference_date: date | None = None,
) -> list[DayForecast]:
    """
    Return a DayForecast for each of the next `horizon_days` days.

    Args:
        daily_counts: {date: admission_count} — historical admissions per day.
        avg_los_days: mean length of stay (converts admissions → occupancy).
        capacity:     total bed count (default 20; set via env/config in agent).
        horizon_days: number of days to forecast (default 7).
        reference_date: "today" anchor for tests; defaults to date.today().
    """
    ref = reference_date or date.today()
    forecast_dates = [ref + timedelta(days=i + 1) for i in range(horizon_days)]
    los = max(avg_los_days, 1.0)  # at least 1 day to avoid 0 occupancy

    if not daily_counts:
        return [
            DayForecast(
                date=d,
                predicted_admissions=0.0,
                predicted_occupancy=0.0,
                capacity=capacity,
                status="normal",
                method="no_data",
            )
            for d in forecast_dates
        ]

    sorted_counts = [daily_counts[k] for k in sorted(daily_counts)]

    if len(sorted_counts) < SPARSE_THRESHOLD:
        mean_admissions = sum(sorted_counts) / len(sorted_counts)
        daily_pred = mean_admissions
        method = "global_mean"
    else:
        window = sorted_counts[-14:]
        daily_pred = sum(window) / len(window)
        method = "moving_average_7d"

    results = []
    for d in forecast_dates:
        occupancy = round(daily_pred * los, 2)
        results.append(
            DayForecast(
                date=d,
                predicted_admissions=round(daily_pred, 2),
                predicted_occupancy=occupancy,
                capacity=capacity,
                status=classify_status(occupancy, capacity),
                method=method,
            )
        )
    return results
