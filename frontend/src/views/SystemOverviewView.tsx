import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Clock,
  Cpu,
  Database,
  HardDrive,
  Layers,
  Network,
  RefreshCw,
  Server,
  ShieldCheck,
} from 'lucide-react';
import {
  getLatestTelemetry,
  getSystemStatus,
  getTelemetryHistory,
} from '../api';
import { TelemetryTimeseriesChart } from '../components/charts';
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  HealthGauge,
  LoadingState,
  MetricCard,
  StatusBadge,
} from '../components/common';
import type {
  LatestTelemetryResponse,
  OperationalStatusResponse,
  SystemMetricRecord,
} from '../types';

export const SystemOverviewView: React.FC = () => {
  const [telemetry, setTelemetry] = useState<LatestTelemetryResponse | null>(null);
  const [systemStatus, setSystemStatus] = useState<OperationalStatusResponse | null>(null);
  const [recentRecords, setRecentRecords] = useState<SystemMetricRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [telData, statusData, historyData] = await Promise.all([
        getLatestTelemetry(),
        getSystemStatus().catch(() => null),
        getTelemetryHistory({ limit: 25 }).catch(() => ({ records: [], count: 0, limit: 25 })),
      ]);
      setTelemetry(telData);
      if (statusData) setSystemStatus(statusData);
      setRecentRecords(historyData.records || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve system overview telemetry.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading && !telemetry) {
    return <LoadingState message="Connecting to system telemetry collector..." height={350} />;
  }

  if (error && !telemetry) {
    return (
      <ErrorState
        title="Failed to Load System Overview"
        message={error}
        detail="Ensure the FastAPI server is running on http://127.0.0.1:8000"
        onRetry={fetchData}
        height={300}
      />
    );
  }

  const metric = telemetry?.metrics;
  const prediction = telemetry?.prediction;
  const isHealthy = systemStatus?.overall_status === 'HEALTHY';

  // Memory calculation
  const memUsedGb = metric?.memory_used_bytes
    ? (metric.memory_used_bytes / (1024 ** 3)).toFixed(1)
    : '--';
  const memTotalGb = metric?.memory_total_bytes
    ? (metric.memory_total_bytes / (1024 ** 3)).toFixed(1)
    : '--';

  // Disk calculation
  const diskUsedGb = metric?.disk_used_bytes
    ? (metric.disk_used_bytes / (1024 ** 3)).toFixed(1)
    : '--';
  const diskTotalGb = metric?.disk_total_bytes
    ? (metric.disk_total_bytes / (1024 ** 3)).toFixed(1)
    : '--';

  // Network throughput calculation
  const netSentSec = metric?.network_bytes_sent_per_sec !== null && metric?.network_bytes_sent_per_sec !== undefined
    ? (metric.network_bytes_sent_per_sec / 1024).toFixed(1)
    : '0.0';
  const netRecvSec = metric?.network_bytes_recv_per_sec !== null && metric?.network_bytes_recv_per_sec !== undefined
    ? (metric.network_bytes_recv_per_sec / 1024).toFixed(1)
    : '0.0';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* Platform Operational State Banner */}
      {systemStatus && (
        <div
          style={{
            backgroundColor: isHealthy ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
            border: `1px solid ${isHealthy ? 'var(--status-healthy-border)' : 'var(--status-critical-border)'}`,
            borderRadius: 'var(--radius-lg)',
            padding: '12px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Server
              size={18}
              style={{ color: isHealthy ? 'var(--status-healthy)' : 'var(--status-critical)', flexShrink: 0 }}
            />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                  Platform Operational State
                </span>
                <StatusBadge status={systemStatus.overall_status} />
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                {systemStatus.headline}
              </div>
            </div>
          </div>
          <Button variant="ghost" size="sm" icon={<RefreshCw size={12} />} onClick={fetchData}>
            Sync
          </Button>
        </div>
      )}

      {/* 4 Responsive KPI Metric Cards */}
      <div className="grid-cols-4">
        <MetricCard
          label="CPU Utilization"
          value={metric?.cpu_percent !== null && metric?.cpu_percent !== undefined ? metric.cpu_percent.toFixed(1) : '--'}
          unit="%"
          percentage={metric?.cpu_percent}
          icon={<Cpu size={16} />}
          subtext={
            <span>
              {metric?.cpu_logical_cores ?? '--'} Cores{' '}
              {metric?.cpu_physical_cores ? `(${metric.cpu_physical_cores} Phys)` : ''}
            </span>
          }
        />

        <MetricCard
          label="Memory Usage"
          value={metric?.memory_percent !== null && metric?.memory_percent !== undefined ? metric.memory_percent.toFixed(1) : '--'}
          unit="%"
          percentage={metric?.memory_percent}
          icon={<Activity size={16} />}
          subtext={<span>{memUsedGb} GB / {memTotalGb} GB</span>}
        />

        <MetricCard
          label="Disk Storage"
          value={metric?.disk_percent !== null && metric?.disk_percent !== undefined ? metric.disk_percent.toFixed(1) : '--'}
          unit="%"
          percentage={metric?.disk_percent}
          icon={<HardDrive size={16} />}
          subtext={<span>{diskUsedGb} GB / {diskTotalGb} GB</span>}
        />

        <MetricCard
          label="Network Throughput"
          value={netRecvSec}
          unit="KB/s"
          icon={<Network size={16} />}
          subtext={<span>↑ {netSentSec} KB/s upload</span>}
        />
      </div>

      {/* Row 2: Health & Risk Evaluation Panel + Live Telemetry Chart */}
      <div className="grid-split-left">
        {/* Health & Risk Card */}
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={16} style={{ color: 'var(--accent-primary)' }} />
              Health &amp; Risk State
            </div>
          }
          subtitle="Real-time multi-signal ML evaluation"
        >
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
            <HealthGauge
              score={prediction?.health_score ?? null}
              riskCategory={prediction?.risk_category ?? 'Unknown'}
              size={135}
            />

            <div
              style={{
                width: '100%',
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 8,
              }}
            >
              <div
                style={{
                  padding: '9px 11px',
                  backgroundColor: 'rgba(0,0,0,0.25)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)' }}>ANOMALY SCORE</div>
                <div
                  style={{
                    fontSize: 16,
                    fontWeight: 700,
                    color: (prediction?.anomaly_score ?? 0) >= 0.5 ? 'var(--status-critical)' : 'var(--accent-primary)',
                    marginTop: 2,
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {prediction ? prediction.anomaly_score.toFixed(3) : '--'}
                </div>
              </div>

              <div
                style={{
                  padding: '9px 11px',
                  backgroundColor: 'rgba(0,0,0,0.25)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)' }}>RISK TIER</div>
                <div style={{ marginTop: 4 }}>
                  <StatusBadge status={prediction?.risk_category ?? 'UNKNOWN'} />
                </div>
              </div>
            </div>

            <div
              style={{
                width: '100%',
                padding: '9px 12px',
                backgroundColor: 'rgba(0,0,0,0.25)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                fontSize: 11.5,
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Decision Score:</span>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                  {prediction?.raw_decision_score !== undefined ? prediction.raw_decision_score.toFixed(4) : '--'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Active Model:</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                  {prediction?.model_name || 'Isolation Forest'}
                </span>
              </div>
            </div>

            {prediction?.warnings && prediction.warnings.length > 0 && (
              <div
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '7px 11px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--status-warning-bg)',
                  border: '1px solid var(--status-warning-border)',
                  color: 'var(--status-warning)',
                  fontSize: 11,
                  fontWeight: 600,
                }}
              >
                <AlertTriangle size={13} style={{ flexShrink: 0 }} />
                <span>{prediction.warnings.length} Active Deduction Signal{prediction.warnings.length > 1 ? 's' : ''}</span>
              </div>
            )}
          </div>
        </Card>

        {/* Live Multi-Metric Trend Chart */}
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Activity size={16} style={{ color: 'var(--accent-primary)' }} />
              Telemetry Trend (Last {recentRecords.length} Samples)
            </div>
          }
          subtitle="Chronological CPU, RAM, and Disk utilization time series"
        >
          <TelemetryTimeseriesChart data={recentRecords} height={250} />
        </Card>
      </div>

      {/* Row 3: Active Monitored Processes & Telemetry Metadata */}
      <div className="grid-cols-2">
        {/* Top Monitored Process Card */}
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Layers size={16} style={{ color: 'var(--accent-primary)' }} />
              Active Process Telemetry
            </div>
          }
          subtitle="Top resource consumer detected on host machine"
        >
          {metric?.top_process_name ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 14px',
                  backgroundColor: 'rgba(56, 189, 248, 0.05)',
                  border: '1px solid rgba(56, 189, 248, 0.2)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {metric.top_process_name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    PID: {metric.top_process_pid ?? 'N/A'} • Total Processes: {metric.process_count ?? 'N/A'}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--accent-primary)', fontVariantNumeric: 'tabular-nums' }}>
                    {metric.top_process_cpu_percent?.toFixed(1) ?? '0.0'}%
                  </div>
                  <div style={{ fontSize: 9.5, color: 'var(--text-muted)', textTransform: 'uppercase' }}>CPU Share</div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ color: 'var(--text-muted)' }}>Top Process Memory:</span>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  {metric.top_process_memory_percent?.toFixed(1) ?? '0.0'}% RAM
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                <span style={{ color: 'var(--text-muted)' }}>Collector Status:</span>
                <StatusBadge status={telemetry?.collector_status ?? 'OPERATIONAL'} />
              </div>
            </div>
          ) : (
            <EmptyState message="No process data recorded for current sample." height={130} />
          )}
        </Card>

        {/* Telemetry Snapshot Metadata */}
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Clock size={16} style={{ color: 'var(--accent-primary)' }} />
              Host Telemetry Metadata
            </div>
          }
          subtitle="Collector sample ID and timing metrics"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 6, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Sample ID:</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                #{metric?.id ?? 'Live Memory'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 6, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Timestamp:</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
                {metric?.timestamp ? new Date(metric.timestamp).toLocaleString() : 'N/A'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 6, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Engineered Features:</span>
              <span style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                {telemetry?.features?.features ? Object.keys(telemetry.features.features).length : 39} Extracted Dimensions
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Persistence:</span>
              <StatusBadge status="COMMITTED" type="healthy" />
            </div>
          </div>
        </Card>
      </div>

      {/* Row 4: Recent Telemetry Ledger Table */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Database size={16} style={{ color: 'var(--accent-primary)' }} />
            Recent Telemetry Ledger (Latest Samples)
          </div>
        }
        subtitle="Recent chronologically ordered hardware snapshots"
        noPadding={true}
      >
        {recentRecords.length > 0 ? (
          <div className="op-table-wrapper" style={{ border: 'none' }}>
            <table className="op-table" style={{ minWidth: 700 }}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Timestamp</th>
                  <th>CPU %</th>
                  <th>Memory %</th>
                  <th>Disk %</th>
                  <th>Network I/O</th>
                  <th>Top Process</th>
                  <th>Process Count</th>
                </tr>
              </thead>
              <tbody>
                {recentRecords.slice(0, 10).map((r) => {
                  const netSent = r.network_bytes_sent_per_sec !== null && r.network_bytes_sent_per_sec !== undefined
                    ? `${(r.network_bytes_sent_per_sec / 1024).toFixed(1)} KB/s`
                    : '0.0';
                  const netRecv = r.network_bytes_recv_per_sec !== null && r.network_bytes_recv_per_sec !== undefined
                    ? `${(r.network_bytes_recv_per_sec / 1024).toFixed(1)} KB/s`
                    : '0.0';

                  return (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-muted)' }}>#{r.id}</td>
                      <td>{new Date(r.timestamp).toLocaleTimeString()}</td>
                      <td style={{ fontWeight: 600, color: (r.cpu_percent ?? 0) >= 80 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
                        {r.cpu_percent !== null ? `${r.cpu_percent.toFixed(1)}%` : '--'}
                      </td>
                      <td style={{ fontWeight: 600, color: (r.memory_percent ?? 0) >= 80 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
                        {r.memory_percent !== null ? `${r.memory_percent.toFixed(1)}%` : '--'}
                      </td>
                      <td>{r.disk_percent !== null ? `${r.disk_percent.toFixed(1)}%` : '--'}</td>
                      <td>↓ {netRecv} / ↑ {netSent}</td>
                      <td style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>
                        {r.top_process_name ?? '--'}
                      </td>
                      <td>{r.process_count ?? '--'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState message="No recent telemetry records found." height={140} />
        )}
      </Card>
    </div>
  );
};
