/**
 * Hardware telemetry and metric collection types matching FastAPI schemas.
 */

import type { PredictionResult } from './ml';

export interface CPUMetrics {
  utilization_percent: number;
  logical_cores: number;
  physical_cores?: number | null;
  per_core_percent: number[];
}

export interface MemoryMetrics {
  total_bytes: number;
  available_bytes: number;
  used_bytes: number;
  utilization_percent: number;
  total_mb?: number | null;
  used_mb?: number | null;
  available_mb?: number | null;
}

export interface DiskPartitionMetrics {
  mount_point: string;
  total_bytes: number;
  used_bytes: number;
  free_bytes: number;
  utilization_percent: number;
  device?: string | null;
  fstype?: string | null;
  total_gb?: number | null;
  used_gb?: number | null;
  free_gb?: number | null;
}

export interface NetworkMetrics {
  bytes_sent: number;
  bytes_recv: number;
  packets_sent: number;
  packets_recv: number;
  upload_kbps: number;
  download_kbps: number;
}

export interface ProcessMetrics {
  pid: number;
  name: string;
  cpu_percent: number;
  memory_percent: number;
  status?: string | null;
  memory_bytes?: number | null;
  num_threads?: number | null;
}

export interface SystemMetricRecord {
  id: number;
  timestamp: string;
  cpu_percent: number | null;
  cpu_logical_cores: number | null;
  cpu_physical_cores: number | null;
  memory_total_bytes: number | null;
  memory_used_bytes: number | null;
  memory_available_bytes: number | null;
  memory_percent: number | null;
  disk_total_bytes: number | null;
  disk_used_bytes: number | null;
  disk_free_bytes: number | null;
  disk_percent: number | null;
  network_bytes_sent: number | null;
  network_bytes_recv: number | null;
  network_bytes_sent_per_sec: number | null;
  network_bytes_recv_per_sec: number | null;
  process_count: number | null;
  top_process_pid: number | null;
  top_process_name: string | null;
  top_process_cpu_percent: number | null;
  top_process_memory_percent: number | null;
  raw_payload?: Record<string, unknown>;
}

export interface FeatureVectorRecord {
  id: number;
  metric_id: number | null;
  timestamp: string;
  features: Record<string, number>;
  metadata?: Record<string, unknown>;
}

export interface LatestTelemetryResponse {
  metrics: SystemMetricRecord | null;
  features: FeatureVectorRecord | null;
  prediction: PredictionResult | null;
  collector_status: string;
  timestamp: string;
}

export interface HistoricalTelemetryResponse {
  count: number;
  limit: number;
  records: SystemMetricRecord[];
}

export interface SnapshotResponse {
  success: boolean;
  persisted: boolean;
  metrics: SystemMetricRecord | null;
  prediction: PredictionResult | null;
  error: string | null;
}

export interface MonitoringStatusResponse {
  is_running: boolean;
  sample_interval: number;
  message: string;
  telemetry_freshness?: 'FRESH' | 'WARM' | 'STALE' | 'NO_DATA' | string | null;
  seconds_since_last_sample?: number | null;
}

export interface MonitoringControlRequest {
  interval?: number;
}
