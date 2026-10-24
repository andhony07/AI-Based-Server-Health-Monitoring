/**
 * Anomaly audit log API service.
 */

import { apiClient } from './client';
import type { HistoricalAnomaliesResponse } from '../types';

export interface AnomaliesHistoryQuery {
  limit?: number;
  anomalies_only?: boolean;
}

export async function getAnomaliesHistory(
  params: AnomaliesHistoryQuery = {}
): Promise<HistoricalAnomaliesResponse> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.anomalies_only !== undefined) query.set('anomalies_only', String(params.anomalies_only));

  const qs = query.toString();
  return apiClient<HistoricalAnomaliesResponse>(`/anomalies/history${qs ? `?${qs}` : ''}`);
}
