/**
 * Telemetry and hardware metric API service.
 */

import { apiClient } from './client';
import type {
  HistoricalTelemetryResponse,
  LatestTelemetryResponse,
  SnapshotResponse,
} from '../types';

export async function getLatestTelemetry(): Promise<LatestTelemetryResponse> {
  return apiClient<LatestTelemetryResponse>('/telemetry/latest');
}

export async function captureSnapshot(persist = true): Promise<SnapshotResponse> {
  return apiClient<SnapshotResponse>(`/telemetry/snapshot?persist=${persist}`, {
    method: 'POST',
  });
}

export interface TelemetryHistoryQuery {
  limit?: number;
  start_time?: string;
  end_time?: string;
}

export async function getTelemetryHistory(
  params: TelemetryHistoryQuery = {}
): Promise<HistoricalTelemetryResponse> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  if (params.start_time) query.set('start_time', params.start_time);
  if (params.end_time) query.set('end_time', params.end_time);

  const qs = query.toString();
  return apiClient<HistoricalTelemetryResponse>(`/telemetry/history${qs ? `?${qs}` : ''}`);
}
