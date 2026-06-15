"""
Unit tests for the Operations Agent forecaster — pure function tests, no DB.

⚠ SPARSE DATA NOTE: With < 14 historical data points (our real DB has ~5
encounters) the forecaster always falls back to "global_mean". Tests verify
both code paths explicitly.
"""

from datetime import date, timedelta

import pytest

from agents.operations.forecaster import (
    SPARSE_THRESHOLD,
    DayForecast,
    classify_status,
    compute_forecasts,
)

TODAY = date(2026, 6, 15)  # fixed anchor so tests are deterministic


# ── classify_status ───────────────────────────────────────────────────────────

def test_classify_normal():
    assert classify_status(10.0, 20) == "normal"  # 50% utilisation


def test_classify_warning_boundary():
    # exactly 80% → warning
    assert classify_status(16.0, 20) == "warning"


def test_classify_critical_boundary():
    # exactly 100% → critical
    assert classify_status(20.0, 20) == "critical"


def test_classify_over_capacity():
    assert classify_status(25.0, 20) == "critical"


def test_classify_zero_capacity():
    # guard against division by zero
    assert classify_status(1.0, 0) == "critical"


def test_classify_zero_occupancy():
    assert classify_status(0.0, 20) == "normal"


# ── compute_forecasts: no data ────────────────────────────────────────────────

def test_no_data_returns_seven_days():
    forecasts = compute_forecasts({}, avg_los_days=2.0, capacity=20, reference_date=TODAY)
    assert len(forecasts) == 7


def test_no_data_all_normal():
    forecasts = compute_forecasts({}, avg_los_days=2.0, capacity=20, reference_date=TODAY)
    assert all(f.status == "normal" for f in forecasts)


def test_no_data_method_no_data():
    forecasts = compute_forecasts({}, avg_los_days=1.0, capacity=20, reference_date=TODAY)
    assert all(f.method == "no_data" for f in forecasts)


def test_no_data_dates_are_tomorrow_onwards():
    forecasts = compute_forecasts({}, avg_los_days=1.0, capacity=20, reference_date=TODAY)
    assert forecasts[0].date == TODAY + timedelta(days=1)
    assert forecasts[-1].date == TODAY + timedelta(days=7)


# ── compute_forecasts: sparse fallback (< SPARSE_THRESHOLD days) ──────────────

def _sparse_counts(n: int) -> dict[date, int]:
    """Generate n distinct days each with 2 admissions."""
    return {TODAY - timedelta(days=i): 2 for i in range(1, n + 1)}


def test_sparse_uses_global_mean():
    counts = _sparse_counts(5)  # well below threshold
    forecasts = compute_forecasts(counts, avg_los_days=1.0, capacity=20, reference_date=TODAY)
    assert all(f.method == "global_mean" for f in forecasts)


def test_sparse_prediction_equals_mean():
    # 3 days × 2 admissions = mean 2.0; los=1 → occupancy=2.0
    counts = {TODAY - timedelta(days=1): 2, TODAY - timedelta(days=2): 4}
    forecasts = compute_forecasts(counts, avg_los_days=1.0, capacity=20, reference_date=TODAY)
    assert all(f.predicted_admissions == 3.0 for f in forecasts)
    assert all(f.predicted_occupancy == 3.0 for f in forecasts)


def test_sparse_los_multiplied():
    counts = {TODAY - timedelta(days=1): 4}
    forecasts = compute_forecasts(counts, avg_los_days=3.0, capacity=20, reference_date=TODAY)
    # 4 admissions × 3 LOS days = 12 occupancy
    assert all(f.predicted_occupancy == 12.0 for f in forecasts)


def test_sparse_los_minimum_one():
    counts = {TODAY - timedelta(days=1): 5}
    forecasts = compute_forecasts(counts, avg_los_days=0.0, capacity=20, reference_date=TODAY)
    # LOS clamped to 1 → occupancy = 5 × 1 = 5
    assert all(f.predicted_occupancy == 5.0 for f in forecasts)


def test_sparse_warning_status():
    # 4 admissions × 4 LOS → 16 occupancy / 20 cap = 80% → warning
    counts = {TODAY - timedelta(days=1): 4}
    forecasts = compute_forecasts(counts, avg_los_days=4.0, capacity=20, reference_date=TODAY)
    assert all(f.status == "warning" for f in forecasts)


def test_sparse_critical_status():
    # 5 admissions × 5 LOS → 25 occupancy / 20 cap > 100% → critical
    counts = {TODAY - timedelta(days=1): 5}
    forecasts = compute_forecasts(counts, avg_los_days=5.0, capacity=20, reference_date=TODAY)
    assert all(f.status == "critical" for f in forecasts)


def test_sparse_horizon_customizable():
    counts = _sparse_counts(3)
    forecasts = compute_forecasts(counts, avg_los_days=1.0, capacity=20, horizon_days=3, reference_date=TODAY)
    assert len(forecasts) == 3


# ── compute_forecasts: moving average path (≥ SPARSE_THRESHOLD days) ──────────

def _adequate_counts(n: int) -> dict[date, int]:
    """Generates n days of data: alternating 2 and 4 to produce a clear mean."""
    counts = {}
    for i in range(1, n + 1):
        day = TODAY - timedelta(days=i)
        counts[day] = 2 if i % 2 == 0 else 4
    return counts


def test_adequate_uses_moving_average():
    counts = _adequate_counts(SPARSE_THRESHOLD)
    forecasts = compute_forecasts(counts, avg_los_days=1.0, capacity=20, reference_date=TODAY)
    assert all(f.method == "moving_average_7d" for f in forecasts)


def test_adequate_uses_last_14_window():
    # 20 days of data: oldest 6 days have 100 admissions, most-recent 14 have 2
    counts = {}
    for i in range(1, 15):   # days 1–14 ago → count 2
        counts[TODAY - timedelta(days=i)] = 2
    for i in range(15, 21):  # days 15–20 ago → count 100
        counts[TODAY - timedelta(days=i)] = 100
    forecasts = compute_forecasts(counts, avg_los_days=1.0, capacity=200, reference_date=TODAY)
    # sorted_counts[-14:] = the 14 most-recent entries, all 2 → mean = 2.0
    assert all(f.predicted_admissions == 2.0 for f in forecasts)


def test_adequate_returns_seven_forecasts():
    counts = _adequate_counts(SPARSE_THRESHOLD + 5)
    forecasts = compute_forecasts(counts, avg_los_days=1.0, capacity=20, reference_date=TODAY)
    assert len(forecasts) == 7


# ── DayForecast structure ─────────────────────────────────────────────────────

def test_forecast_has_required_fields():
    counts = {TODAY - timedelta(days=1): 2}
    f = compute_forecasts(counts, avg_los_days=1.0, capacity=20, reference_date=TODAY)[0]
    assert isinstance(f, DayForecast)
    assert f.date == TODAY + timedelta(days=1)
    assert isinstance(f.predicted_admissions, float)
    assert isinstance(f.predicted_occupancy, float)
    assert f.capacity == 20
    assert f.status in ("normal", "warning", "critical")
    assert f.method in ("global_mean", "moving_average_7d", "no_data")
