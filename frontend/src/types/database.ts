/**
 * Database state, validation log, and system status types matching FastAPI schemas.
 */

export interface ValidationIssue {
  field?: string;
  rule?: string;
  message: string;
  severity?: 'CRITICAL' | 'WARNING' | 'INFO' | string;
  observed_value?: unknown;
  [key: string]: unknown;
}

export interface ValidationLogRecord {
  id: number;
  metric_id: number | null;
  timestamp: string;
  is_valid: boolean;
  issues_count: number;
  has_errors: boolean;
  issues: ValidationIssue[];
}

export interface DatabaseSummaryResponse {
  database_path: string;
  database_exists: boolean;
  file_size_bytes: number;
  counts: Record<string, number>;
  total_records: number;
  earliest_timestamp: string | null;
  latest_timestamp: string | null;
  retention_days: number | null;
}

export interface SubsystemStatus {
  status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'READY' | 'ACTIVE' | 'IDLE' | 'ERROR' | string;
  detail?: string;
  message?: string;
  mode?: string;
  version?: string;
  count?: number;
  [key: string]: unknown;
}

export interface OperationalStatusResponse {
  timestamp: string;
  overall_status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | string;
  status_color: string;
  headline: string;
  subsystems: Record<string, SubsystemStatus>;
}
