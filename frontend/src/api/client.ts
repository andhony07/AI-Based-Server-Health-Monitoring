/**
 * Centralized HTTP Client for the FastAPI REST API backend.
 * Uses Fetch API with typed envelopes, standard error normalizations,
 * and Vite environment-driven base URL configuration.
 */

import type { ApiError } from '../types';

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL;
// Default to '/api' for Vite development proxy
export const API_BASE_URL = (rawBaseUrl !== undefined && rawBaseUrl !== '')
  ? rawBaseUrl.replace(/\/+$/, '')
  : '/api';

export class ApiException extends Error implements ApiError {
  status: number;
  detail?: string;
  raw?: unknown;

  constructor(status: number, message: string, detail?: string, raw?: unknown) {
    super(message);
    this.name = 'ApiException';
    this.status = status;
    this.detail = detail;
    this.raw = raw;
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${normalizedEndpoint}`;

  const headers = new Headers(options.headers || {});
  if (!headers.has('Accept')) {
    headers.set('Accept', 'application/json');
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : 'Network request failed';
    throw new ApiException(
      0,
      `Network Error: Failed to communicate with server at ${url}. ${errorMsg}`,
      'Connection refused or network unreachable. Ensure the FastAPI backend is running on http://127.0.0.1:8000.'
    );
  }

  // Handle No Content response
  if (response.status === 204) {
    return {} as T;
  }

  let data: unknown;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = null;
    }
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    let detail = response.statusText;
    if (typeof data === 'object' && data !== null) {
      const maybeObj = data as Record<string, unknown>;
      if (typeof maybeObj.detail === 'string') {
        detail = maybeObj.detail;
      } else if (typeof maybeObj.message === 'string') {
        detail = maybeObj.message;
      } else if (Array.isArray(maybeObj.detail)) {
        // FastAPI / Pydantic validation errors
        detail = maybeObj.detail
          .map((d: Record<string, unknown>) => {
            const loc = Array.isArray(d.loc) ? d.loc.join('.') : '';
            return `${loc ? `[${loc}] ` : ''}${d.msg || JSON.stringify(d)}`;
          })
          .join('; ');
      }
    }
    throw new ApiException(
      response.status,
      `API Error (${response.status}): ${detail}`,
      detail,
      data
    );
  }

  return data as T;
}
