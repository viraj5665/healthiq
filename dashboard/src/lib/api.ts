import type { RiskScore, BedForecast } from '../types'

const BASE = '/api'

export async function fetchRiskScores(limit = 650): Promise<RiskScore[]> {
  const res = await fetch(`${BASE}/risk/scores?limit=${limit}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

export const FEATURE_LABELS: Record<string, string> = {
  num_er_encounters:  'ER Visits',
  age:                'Age (yrs)',
  cholesterol_high:   'High Cholesterol',
  hba1c_high:         'High HbA1c',
  glucose_high:       'High Glucose',
  num_encounters:     'Total Encounters',
  max_los_days:       'Max LOS (days)',
  avg_los_days:       'Avg LOS (days)',
  num_observations:   'Observations',
  num_abnormal_obs:   'Abnormal Obs',
  abnormal_rate:      'Abnormal Rate',
  potassium_abnormal: 'Potassium Abn.',
  gender_male:        'Male',
}

export async function fetchBedForecasts(): Promise<BedForecast[]> {
  const res = await fetch(`${BASE}/operations/forecasts`)
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

export async function runForecast(): Promise<void> {
  const res = await fetch(`${BASE}/operations/forecast`, { method: 'POST' })
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
}

export const RISK_ORDER: Record<string, number> = {
  critical: 4, high: 3, moderate: 2, low: 1,
}
