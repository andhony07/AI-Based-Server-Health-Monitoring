import React, { useEffect, useRef, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Camera,
  CheckCircle2,
  Clock,
  Cpu,
  HardDrive,
  Network as NetIcon,
  Play,
  Square,
  Zap,
} from 'lucide-react';
import {
  captureSnapshot,
  getLatestTelemetry,
  getMonitoringStatus,
  getTelemetryHistory,
  startMonitoring,
  stopMonitoring,
} from '../api';
import {
  NetworkChart,
  TelemetryTimeseriesChart,
} from '../components/charts';
import {
  Button,
  Card,
  LoadingState,
  MetricCard,
  StatusBadge,
} from '../components/common';
import type {
  LatestTelemetryResponse,
  MonitoringStatusResponse,
  SystemMetricRecord,
} from '../types';

export const RealTimeMonitoringView: React.FC = () => {
  const [telemetry, setTelemetry] = useState<LatestTelemetryResponse | null>(null);
  const [history, setHistory] = useState<SystemMetricRecord[]>([]);
  const [workerStatus, setWorkerStatus] = useState<MonitoringStatusResponse | null>(null);

  // Polling controls
  const [pollingActive, setPollingActive] = useState<boolean>(true);
  const [pollIntervalSec, setPollIntervalSec] = useState<number>(3);

  // Operation flags
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSnapshotting, setIsSnapshotting] = useState<boolean>(false);
  const [isTogglingWorker, setIsTogglingWorker] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [snapshotMessage, setSnapshotMessage] = useState<string | null>(null);

  // Duplicate request prevention ref
  const inFlightRef = useRef<boolean>(false);
  const unmountedRef = useRef<boolean>(false);

  // Poll tick
  const pollTick = async () => {
    if (inFlightRef.current || unmountedRef.current) return;
    try {
      inFlightRef.current = true;
      const [latestData, historyData, statusData] = await Promise.all([
        getLatestTelemetry(),
        getTelemetryHistory({ limit: 40 }).catch(() => ({ records: [], count: 0, limit: 40 })),
        getMonitoringStatus().catch(() => null),
      ]);

      if (!unmountedRef.current) {
        setTelemetry(latestData);
        if (historyData.records) setHistory(historyData.records);
        if (statusData) setWorkerStatus(statusData);
        setError(null);
      }
    } catch (err: unknown) {
      if (!unmountedRef.current) {
        const msg = err instanceof Error ? err.message : 'Polling error occurred.';
        setError(msg);
      }
    } finally {
      inFlightRef.current = false;
      if (!unmountedRef.current) {
        setIsLoading(false);
      }
    }
  };

  // Setup interval & cleanup on unmount
  useEffect(() => {
    unmountedRef.current = false;
    pollTick(); // Initial tick

    let intervalId: ReturnType<typeof setInterval> | null = null;
    if (pollingActive) {
      intervalId = setInterval(() => {
        pollTick();
      }, pollIntervalSec * 1000);
    }

    return () => {
      unmountedRef.current = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [pollingActive, pollIntervalSec]);

  // Capture live on-demand snapshot
  const handleSnapshot = async () => {
    try {
      setIsSnapshotting(true);
      setSnapshotMessage(null);
      setError(null);
      const res = await captureSnapshot(true);
      if (res.success) {
        setSnapshotMessage('On-demand live snapshot captured & persisted to SQLite database!');
        // Refresh telemetry immediately
        await pollTick();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to capture live snapshot.';
      setError(msg);
    } finally {
      setIsSnapshotting(false);
    }
  };

  // Start / Stop background collector thread
  const handleToggleWorker = async () => {
    try {
      setIsTogglingWorker(true);
      setError(null);
      if (workerStatus?.is_running) {
        const res = await stopMonitoring();
        setWorkerStatus(res);
      } else {
        const res = await startMonitoring();
        setWorkerStatus(res);
      }
      // Re-query status
      await pollTick();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to toggle background monitoring worker.';
      setError(msg);
    } finally {
      setIsTogglingWorker(false);
    }
  };

  if (isLoading && !telemetry) {
    return <LoadingState message="Initializing real-time telemetry stream..." height={350} />;
  }

  const metric = telemetry?.metrics;
  const isWorkerRunning = workerStatus?.is_running ?? false;

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="page-title">
            <Activity size={20} style={{ color: 'var(--accent-primary)' }} />
            <span>Real-Time Telemetry Stream</span>
          </div>
          <div className="page-subtitle">
            Continuous hardware polling stream, background collector thread management, and instant snapshot execution
          </div>
        </div>

        {/* Live Freshness & Clock Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-muted)' }}>
            <Clock size={13} />
            <span>
              Latest Sample: {metric?.timestamp ? new Date(metric.timestamp).toLocaleTimeString() : 'N/A'}
            </span>
          </div>

          <StatusBadge
            status={isWorkerRunning ? 'THREAD ACTIVE' : 'THREAD IDLE'}
            type={isWorkerRunning ? 'healthy' : 'neutral'}
          />
        </div>
      </div>

      {/* Stream Control Console */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Activity size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Polling Stream &amp; Collector Controls</span>
          </div>
        }
        subtitle="Manage continuous polling interval, daemon collector thread, and live snapshot execution"
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 14,
          }}
        >
          {/* Status Indicators */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Collector:</span>
              <StatusBadge
                status={isWorkerRunning ? 'RUNNING' : 'STOPPED'}
                type={isWorkerRunning ? 'healthy' : 'neutral'}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Freshness:</span>
              <StatusBadge status={workerStatus?.telemetry_freshness ?? 'FRESH'} />
              {workerStatus?.seconds_since_last_sample !== null && workerStatus?.seconds_since_last_sample !== undefined && (
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  ({workerStatus.seconds_since_last_sample.toFixed(1)}s ago)
                </span>
              )}
            </div>
          </div>

          {/* Controls Bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            {/* Polling Interval Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Interval:</span>
              <select
                className="form-select"
                style={{ padding: '5px 9px', fontSize: 12 }}
                value={pollIntervalSec}
                onChange={(e) => setPollIntervalSec(Number(e.target.value))}
              >
                <option value={1}>1 second</option>
                <option value={2}>2 seconds</option>
                <option value={3}>3 seconds</option>
                <option value={5}>5 seconds</option>
                <option value={10}>10 seconds</option>
              </select>
            </div>

            {/* Polling Pause/Resume */}
            <Button
              variant="secondary"
              size="sm"
              icon={pollingActive ? <Square size={12} /> : <Play size={12} />}
              onClick={() => setPollingActive(!pollingActive)}
            >
              {pollingActive ? 'Pause Stream' : 'Resume Stream'}
            </Button>

            {/* Worker Start/Stop */}
            <Button
              variant={isWorkerRunning ? 'danger' : 'secondary'}
              size="sm"
              icon={isWorkerRunning ? <Square size={12} /> : <Play size={12} />}
              loading={isTogglingWorker}
              onClick={handleToggleWorker}
            >
              {isWorkerRunning ? 'Stop Collector' : 'Start Collector'}
            </Button>

            {/* On-Demand Snapshot Action */}
            <Button
              variant="primary"
              size="sm"
              icon={<Camera size={13} />}
              loading={isSnapshotting}
              onClick={handleSnapshot}
            >
              Capture Snapshot
            </Button>
          </div>
        </div>

        {/* Snapshot Success Notification */}
        {snapshotMessage && (
          <div
            className="alert-box alert-success"
            style={{ marginTop: 14 }}
          >
            <CheckCircle2 size={16} />
            <span>{snapshotMessage}</span>
          </div>
        )}

        {/* Error notification */}
        {error && (
          <div
            className="alert-box alert-danger"
            style={{ marginTop: 14 }}
          >
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}
      </Card>

      {/* Live Metric Stats Cards */}
      <div className="grid-cols-4">
        <MetricCard
          label="Live CPU Utilization"
          value={metric?.cpu_percent !== null && metric?.cpu_percent !== undefined ? `${metric.cpu_percent.toFixed(1)}%` : '--'}
          percentage={metric?.cpu_percent}
          icon={<Cpu size={16} />}
          subtext={<span>{metric?.cpu_logical_cores ?? '--'} Cores Online</span>}
        />
        <MetricCard
          label="Live Memory Utilization"
          value={metric?.memory_percent !== null && metric?.memory_percent !== undefined ? `${metric.memory_percent.toFixed(1)}%` : '--'}
          percentage={metric?.memory_percent}
          icon={<Zap size={16} />}
          subtext={
            <span>
              {metric?.memory_used_bytes ? (metric.memory_used_bytes / (1024 ** 3)).toFixed(1) : '--'} GB /{' '}
              {metric?.memory_total_bytes ? (metric.memory_total_bytes / (1024 ** 3)).toFixed(1) : '--'} GB
            </span>
          }
        />
        <MetricCard
          label="Live Disk Space"
          value={metric?.disk_percent !== null && metric?.disk_percent !== undefined ? `${metric.disk_percent.toFixed(1)}%` : '--'}
          percentage={metric?.disk_percent}
          icon={<HardDrive size={16} />}
          subtext={
            <span>
              {metric?.disk_used_bytes ? (metric.disk_used_bytes / (1024 ** 3)).toFixed(1) : '--'} GB /{' '}
              {metric?.disk_total_bytes ? (metric.disk_total_bytes / (1024 ** 3)).toFixed(1) : '--'} GB
            </span>
          }
        />
        <MetricCard
          label="Live Network Throughput"
          value={
            metric?.network_bytes_recv_per_sec !== null && metric?.network_bytes_recv_per_sec !== undefined
              ? `${(metric.network_bytes_recv_per_sec / 1024).toFixed(1)} KB/s`
              : '0.0 KB/s'
          }
          icon={<NetIcon size={16} />}
          subtext={
            <span>
              ↑{' '}
              {metric?.network_bytes_sent_per_sec !== null && metric?.network_bytes_sent_per_sec !== undefined
                ? (metric.network_bytes_sent_per_sec / 1024).toFixed(1)
                : '0.0'}{' '}
              KB/s upload
            </span>
          }
        />
      </div>

      {/* Real-Time Charts: Hardware Utilization & Network Stream */}
      <div className="grid-cols-2">
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Cpu size={15} style={{ color: 'var(--accent-primary)' }} />
              <span>Live Hardware Utilization (CPU / RAM / Disk %)</span>
            </div>
          }
          subtitle={`Streaming continuous updates (${history.length} data points)`}
        >
          <TelemetryTimeseriesChart data={history} height={250} showDisk={true} />
        </Card>

        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <NetIcon size={15} style={{ color: 'var(--accent-primary)' }} />
              <span>Live Network Bandwidth (Upload &amp; Download KB/s)</span>
            </div>
          }
          subtitle="Real-time network throughput calculated over sampling interval"
        >
          <NetworkChart data={history} height={250} />
        </Card>
      </div>

      {/* Top Monitored Process Inspector */}
      {metric?.top_process_name && (
        <Card
          title="Active Host Process Inspector"
          subtitle="Top resource consumer detected during the latest live sample"
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 18px',
              backgroundColor: 'rgba(0, 0, 0, 0.25)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-default)',
              flexWrap: 'wrap',
              gap: 12,
            }}
          >
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                {metric.top_process_name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                PID: <code>{metric.top_process_pid ?? 'N/A'}</code> • Total Active System Processes: <strong>{metric.process_count ?? 'N/A'}</strong>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 24, textAlign: 'right' }}>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--accent-primary)', fontVariantNumeric: 'tabular-nums' }}>
                  {metric.top_process_cpu_percent?.toFixed(1) ?? '0.0'}%
                </div>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>CPU Load</div>
              </div>
              <div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#A855F7', fontVariantNumeric: 'tabular-nums' }}>
                  {metric.top_process_memory_percent?.toFixed(1) ?? '0.0'}%
                </div>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Memory Share</div>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
