/**
 * Database state and operational system status API service.
 */

import { apiClient } from './client';
import type {
  DatabaseSummaryResponse,
  OperationalStatusResponse,
  ValidationLogRecord,
} from '../types';

export async function getSystemStatus(): Promise<OperationalStatusResponse> {
  return apiClient<OperationalStatusResponse>('/system/status');
}

export async function getDatabaseSummary(): Promise<DatabaseSummaryResponse> {
  return apiClient<DatabaseSummaryResponse>('/database/summary');
}

export async function getValidationLogs(limit = 50): Promise<ValidationLogRecord[]> {
  return apiClient<ValidationLogRecord[]>(`/database/validation-logs?limit=${limit}`);
}
