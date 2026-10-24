/**
 * Machine learning predictions, explainable diagnostics, and model status API service.
 */

import { apiClient } from './client';
import type {
  DiagnosticReport,
  ModelStatusResponse,
  PredictionResult,
} from '../types';

export async function getLatestPrediction(): Promise<PredictionResult> {
  return apiClient<PredictionResult>('/ml/prediction/latest');
}

export async function getLatestDiagnostics(): Promise<DiagnosticReport> {
  return apiClient<DiagnosticReport>('/ml/diagnostics/latest');
}

export async function getModelStatus(): Promise<ModelStatusResponse> {
  return apiClient<ModelStatusResponse>('/ml/model/status');
}
