/**
 * Machine learning, prediction, and diagnostic report types matching FastAPI schemas.
 */

export type RiskCategory = 'Nominal' | 'Moderate' | 'Elevated' | 'Critical' | string;

export interface AnomalyResult {
  is_anomaly: boolean;
  raw_score: number;
  normalized_score: number;
  threshold: number;
}

export interface HealthScoreResult {
  score: number | null;
  status: string;
  contributing_factors: Record<string, number>;
  explanation: string;
}

export interface PredictionResult {
  timestamp: string;
  is_anomaly: boolean;
  anomaly_score: number;
  raw_decision_score: number;
  health_score: number | null;
  risk_category: RiskCategory;
  model_name: string;
  model_version: string;
  warnings: string[];
}

export interface DiagnosticEvidence {
  metric_name: string;
  observed_value: unknown;
  threshold: string;
  level: 'CRITICAL' | 'WARNING' | 'INFO' | string;
  description: string;
}

export interface DiagnosticRecommendation {
  id: string;
  category: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO' | string;
  title: string;
  summary: string;
  root_cause_hypothesis: string;
  evidence: DiagnosticEvidence[];
  remediation_steps: string[];
  target_component: string | null;
}

export interface DiagnosticReport {
  timestamp: string;
  overall_health_score: number | null;
  risk_category: RiskCategory;
  anomaly_score: number;
  is_anomaly: boolean;
  summary_headline: string;
  primary_concern: string | null;
  critical_count: number;
  warning_count: number;
  recommendations: DiagnosticRecommendation[];
}

export interface ModelStatusResponse {
  is_trained: boolean;
  model_name: string;
  version: string;
  mode: string;
  expected_features: number;
  training_samples_count: number | null;
  hyperparameters: Record<string, unknown>;
  metrics: Record<string, unknown>;
}

export interface AnomalyAuditItem {
  feature_id: number;
  metric_id: number | null;
  timestamp: string;
  anomaly_score: number;
  is_anomaly: boolean;
  health_score: number | null;
  risk_category: RiskCategory;
  model_name: string;
  is_trained_model: boolean;
  cpu_percent: number | null;
  memory_percent: number | null;
  disk_percent: number | null;
  network_kbps: number | null;
}

export interface HistoricalAnomaliesResponse {
  count: number;
  limit: number;
  anomalies: AnomalyAuditItem[];
}
