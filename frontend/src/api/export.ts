/**
 * RFC-4180 CSV Export service.
 * Connects directly to FastAPI backend export endpoints:
 * /api/export/metrics.csv, /api/export/anomalies.csv, /api/export/features.csv
 */

import { API_BASE_URL, ApiException } from './client';

export function getExportMetricsUrl(params?: {
  limit?: number;
  start_time?: string;
  end_time?: string;
}): string {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.start_time) query.set('start_time', params.start_time);
  if (params?.end_time) query.set('end_time', params.end_time);

  const qs = query.toString();
  return `${API_BASE_URL}/export/metrics.csv${qs ? `?${qs}` : ''}`;
}

export function getExportAnomaliesUrl(params?: {
  limit?: number;
  anomalies_only?: boolean;
}): string {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.anomalies_only !== undefined) {
    query.set('anomalies_only', String(params.anomalies_only));
  }

  const qs = query.toString();
  return `${API_BASE_URL}/export/anomalies.csv${qs ? `?${qs}` : ''}`;
}

export function getExportFeaturesUrl(params?: {
  limit?: number;
  start_time?: string;
  end_time?: string;
}): string {
  const query = new URLSearchParams();
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.start_time) query.set('start_time', params.start_time);
  if (params?.end_time) query.set('end_time', params.end_time);

  const qs = query.toString();
  return `${API_BASE_URL}/export/features.csv${qs ? `?${qs}` : ''}`;
}

export async function downloadCsv(url: string, fallbackFilename: string): Promise<void> {
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Accept: 'text/csv',
    },
  });

  if (!response.ok) {
    throw new ApiException(
      response.status,
      `CSV Export Failed (${response.status}): ${response.statusText}`,
      'Could not download CSV export file from server.'
    );
  }

  let filename = fallbackFilename;
  const disposition = response.headers.get('content-disposition');
  if (disposition && disposition.includes('filename=')) {
    const match = disposition.match(/filename="?([^"]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.URL.revokeObjectURL(blobUrl);
}
