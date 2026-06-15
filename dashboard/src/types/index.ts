export interface ShapFeature {
  feature: string
  shap_value: number
  feature_value: number
}

export interface RiskScore {
  id: string
  patient_id: string
  score_type: string
  score: number
  risk_level: 'low' | 'moderate' | 'high' | 'critical'
  model_version: string
  computed_at: string
  explanation: ShapFeature[]
  features: Record<string, number>
}

export type RiskLevel = 'low' | 'moderate' | 'high' | 'critical' | 'all'

export type SortField = 'score' | 'risk_level' | 'age'
export type SortDir = 'asc' | 'desc'

export interface ManualPatientIn {
  date_of_birth: string
  gender: string
  num_encounters: number
  num_er_visits: number
  conditions: string
}

export interface ManualPatientResult {
  patient_id: string
  score: number
  risk_level: string
  model_version: string
  explanation: ShapFeature[]
  features: Record<string, number>
  patients_in_model: number
}

export interface Alert {
  id: string
  alert_type: string
  severity: 'critical' | 'urgent' | 'warning'
  title: string
  message: string
  status: string
  patient_id: string | null
  risk_score_id: string | null
  triggered_at: string
  metadata: Record<string, unknown> | null
}

export interface ReportMeta {
  id: string
  generated_at: string
  model_version: string
  duration_seconds: number | null
}

export interface ReportFull extends ReportMeta {
  report_markdown: string
  summary_data: Record<string, unknown> | null
}

export interface BedForecast {
  id: string
  forecast_date: string
  predicted_occupancy: number
  capacity: number
  status: 'normal' | 'warning' | 'critical'
  model_method: string
  created_at: string
}
