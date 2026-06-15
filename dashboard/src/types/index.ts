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

export interface BedForecast {
  id: string
  forecast_date: string
  predicted_occupancy: number
  capacity: number
  status: 'normal' | 'warning' | 'critical'
  model_method: string
  created_at: string
}
