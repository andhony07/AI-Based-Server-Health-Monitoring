/**
 * Anomaly simulation studio types matching FastAPI schemas.
 */

import type { DiagnosticReport, PredictionResult } from './ml';

export interface ScenarioProfile {
  scenario: string;
  name: string;
  description: string;
  stress_subsystem: string;
  expected_risk: string;
  is_anomaly_expected: boolean;
}

export interface SimulationRunRequest {
  scenario: string;
  seed?: number;
  persist?: boolean;
  overrides?: Record<string, unknown>;
}

export interface SimulatedMetricSummary {
  timestamp: string;
  cpu: {
    utilization_percent: number;
    logical_cores: number;
  };
  memory: {
    utilization_percent: number;
    used_mb: number;
    total_mb: number;
  };
  disk: {
    utilization_percent: number;
    used_gb: number;
    total_gb: number;
  };
  network: {
    upload_kbps: number;
    download_kbps: number;
  };
  process_count: number;
}

export interface SimulationRunResponse {
  scenario: string;
  profile: ScenarioProfile;
  persisted: boolean;
  metric_id: number | null;
  feature_id: number | null;
  simulated_metrics: SimulatedMetricSummary;
  features_count: number;
  prediction: PredictionResult;
  diagnostics: DiagnosticReport;
}
