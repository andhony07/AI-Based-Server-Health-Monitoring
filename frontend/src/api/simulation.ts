/**
 * Anomaly simulation studio API service.
 */

import { apiClient } from './client';
import type {
  ScenarioProfile,
  SimulationRunRequest,
  SimulationRunResponse,
} from '../types';

export async function listScenarios(): Promise<ScenarioProfile[]> {
  return apiClient<ScenarioProfile[]>('/simulation/scenarios');
}

export async function runSimulation(
  payload: SimulationRunRequest
): Promise<SimulationRunResponse> {
  return apiClient<SimulationRunResponse>('/simulation/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
