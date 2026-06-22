import type { RiskScore, BedForecast, Alert, ReportMeta, ReportFull, ManualPatientIn, ManualPatientResult } from '../types'

// In dev: Vite proxy rewrites /api/* → localhost:8000/*
// In prod: set VITE_API_BASE=https://your-railway-app.up.railway.app in Vercel env vars
const BASE = import.meta.env.VITE_API_BASE ?? '/api'

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

export async function createManualPatient(body: ManualPatientIn): Promise<ManualPatientResult> {
  const res = await fetch(`${BASE}/patients/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data?.detail ?? `${res.status} ${res.statusText}`)
  return data
}

export async function fetchAlerts(limit = 200): Promise<Alert[]> {
  const res = await fetch(`${BASE}/alerts?status=active&limit=${limit}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

export async function runAlertCheck(): Promise<{ created: number; skipped_duplicates: number }> {
  const res = await fetch(`${BASE}/alerts/check`, { method: 'POST' })
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

export async function fetchReports(): Promise<ReportMeta[]> {
  const res = await fetch(`${BASE}/reports`)
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

export async function fetchReport(id: string): Promise<ReportFull> {
  const res = await fetch(`${BASE}/reports/${id}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

export async function generateReport(): Promise<ReportFull> {
  const res = await fetch(`${BASE}/reports/generate`, { method: 'POST' })
  const body = await res.json()
  if (!res.ok) {
    const detail = body?.detail ?? `${res.status} ${res.statusText}`
    throw new Error(detail)
  }
  return body
}

export async function fetchHealth(): Promise<{ status: string; latency_ms: number }> {
  const res = await fetch(`${BASE}/health`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export const RISK_ORDER: Record<string, number> = {
  critical: 4, high: 3, moderate: 2, low: 1,
}
