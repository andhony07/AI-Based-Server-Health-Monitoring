/**
 * Monitoring daemon and background worker lifecycle API service.
 */

import { apiClient } from './client';
import type { MonitoringStatusResponse } from '../types';

export async function getMonitoringStatus(): Promise<MonitoringStatusResponse> {
  return apiClient<MonitoringStatusResponse>('/monitoring/status');
}

export async function startMonitoring(interval?: number): Promise<MonitoringStatusResponse> {
  return apiClient<MonitoringStatusResponse>('/monitoring/start', {
    method: 'POST',
    body: JSON.stringify({ interval: interval ?? null }),
  });
}

export async function stopMonitoring(): Promise<MonitoringStatusResponse> {
  return apiClient<MonitoringStatusResponse>('/monitoring/stop', {
    method: 'POST',
  });
}
