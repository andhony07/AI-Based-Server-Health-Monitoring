import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Brain,
  Clock,
  Database,
  ExternalLink,
  HardDrive,
  Info,
  RefreshCw,
  Server,
  ShieldCheck,
} from 'lucide-react';
import {
  getDatabaseSummary,
  getModelStatus,
  getSystemStatus,
  getValidationLogs,
} from '../api';
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  MetricCard,
  StatusBadge,
} from '../components/common';
import type {
  DatabaseSummaryResponse,
  ModelStatusResponse,
  OperationalStatusResponse,
  ValidationLogRecord,
} from '../types';

export const DatabaseStatusView: React.FC = () => {
  const [dbSummary, setDbSummary] = useState<DatabaseSummaryResponse | null>(null);
  const [systemStatus, setSystemStatus] = useState<OperationalStatusResponse | null>(null);
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [validationLogs, setValidationLogs] = useState<ValidationLogRecord[]>([]);

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const [db, sys, model, logs] = await Promise.all([
        getDatabaseSummary(),
        getSystemStatus(),
        getModelStatus().catch(() => null),
        getValidationLogs(50).catch(() => []),
      ]);
      setDbSummary(db);
      setSystemStatus(sys);
      setModelStatus(model);
      setValidationLogs(logs);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to retrieve database & system status.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  if (loading && !dbSummary) {
    return <LoadingState message="Inspecting SQLite database and subsystem integrity..." height={350} />;
  }

  if (error && !dbSummary) {
    return (
      <ErrorState
        title="Failed to Retrieve System Status"
        message={error}
        onRetry={fetchStatus}
        height={300}
      />
    );
  }

  const dbSizeMb = dbSummary
    ? (dbSummary.file_size_bytes / (1024 * 1024)).toFixed(2)
    : '--';

  const subsystems = systemStatus?.subsystems ?? {};

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="page-title">
            <Database size={20} style={{ color: 'var(--accent-primary)' }} />
            <span>Database &amp; Subsystem Architecture Status</span>
          </div>
          <div className="page-subtitle">
            SQLite persistence diagnostics, non-destructive subsystem health probes, and FastAPI documentation endpoints
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          icon={<RefreshCw size={13} />}
          loading={loading}
          onClick={fetchStatus}
        >
          Re-verify Health
        </Button>
      </div>

      {/* Platform Overall Operational Health Header */}
      {systemStatus && (
        <div
          style={{
            backgroundColor: systemStatus.overall_status === 'HEALTHY'
              ? 'rgba(16, 185, 129, 0.08)'
              : 'rgba(239, 68, 68, 0.08)',
            border: `1px solid ${
              systemStatus.overall_status === 'HEALTHY'
                ? 'var(--status-healthy-border)'
                : 'var(--status-critical-border)'
            }`,
            borderRadius: 'var(--radius-lg)',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 'var(--radius-md)',
                backgroundColor: systemStatus.overall_status === 'HEALTHY'
                  ? 'var(--status-healthy-bg)'
                  : 'var(--status-critical-bg)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <Server
                size={22}
                style={{
                  color: systemStatus.overall_status === 'HEALTHY'
                    ? 'var(--status-healthy)'
                    : 'var(--status-critical)',
                }}
              />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                  Platform Subsystem Health State
                </span>
                <StatusBadge status={systemStatus.overall_status} />
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                {systemStatus.headline} • Evaluation Time: {systemStatus.timestamp}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Database Key Stats */}
      <div className="grid-cols-4">
        <MetricCard
          label="Database Size"
          value={`${dbSizeMb} MB`}
          icon={<HardDrive size={16} />}
          subtext={<span>SQLite 3 file on local disk</span>}
        />
        <MetricCard
          label="Total Database Records"
          value={dbSummary?.total_records.toLocaleString() ?? '--'}
          icon={<Database size={16} />}
          subtext={<span>Across all relational tables</span>}
        />
        <MetricCard
          label="System Metrics Records"
          value={dbSummary?.counts?.system_metrics?.toLocaleString() ?? '--'}
          icon={<Clock size={16} />}
          subtext={<span>Hardware telemetry rows</span>}
        />
        <MetricCard
          label="Feature Vectors"
          value={dbSummary?.counts?.feature_vectors?.toLocaleString() ?? '--'}
          icon={<Brain size={16} />}
          subtext={<span>39-dimensional engineered vectors</span>}
        />
      </div>

      {/* Subsystem Health Grid */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <ShieldCheck size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Subsystem Health Diagnostics &amp; Telemetry Freshness</span>
          </div>
        }
        subtitle="Non-destructive live health checks across persistence, model engine, collector, and pipeline components"
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
          {Object.entries(subsystems).map(([subsystemName, info]) => {
            const rawInfo = info as Record<string, unknown>;
            const statusStr = String(rawInfo.status || 'UNKNOWN');
            const message = String(rawInfo.message || rawInfo.detail || '');

            return (
              <div
                key={subsystemName}
                style={{
                  padding: '14px 16px',
                  backgroundColor: 'rgba(0, 0, 0, 0.25)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: 'var(--text-primary)',
                      textTransform: 'capitalize',
                    }}
                  >
                    {subsystemName.replace(/_/g, ' ')}
                  </span>
                  <StatusBadge status={statusStr} />
                </div>
                {message && (
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {message}
                  </div>
                )}
                {/* Additional properties */}
                <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {Object.entries(rawInfo)
                    .filter(([k]) => !['status', 'message', 'detail'].includes(k))
                    .map(([k, v]) => (
                      <span key={k}>
                        {k}: <strong style={{ color: 'var(--text-secondary)' }}>{String(v)}</strong>
                      </span>
                    ))}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* SQLite Database Physical Summary & API Gateway */}
      <div className="grid-cols-2">
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Database size={15} style={{ color: 'var(--accent-primary)' }} />
              <span>SQLite Physical Storage State</span>
            </div>
          }
          subtitle="Database file location and chronological sampling bounds"
        >
          {dbSummary ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 12.5 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 7, borderBottom: '1px solid var(--border-subtle)', flexWrap: 'wrap', gap: 4 }}>
                <span style={{ color: 'var(--text-muted)' }}>Database Path:</span>
                <code style={{ fontSize: 11, color: 'var(--accent-primary)', wordBreak: 'break-all' }}>
                  {dbSummary.database_path}
                </code>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 7, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Database Exists:</span>
                <span style={{ fontWeight: 600, color: dbSummary.database_exists ? 'var(--status-healthy)' : 'var(--status-critical)' }}>
                  {dbSummary.database_exists ? 'Verified on Disk' : 'Missing File'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 7, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Earliest Sample:</span>
                <span style={{ color: 'var(--text-primary)' }}>
                  {dbSummary.earliest_timestamp ? new Date(dbSummary.earliest_timestamp).toLocaleString() : 'N/A'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 7, borderBottom: '1px solid var(--border-subtle)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Latest Sample:</span>
                <span style={{ color: 'var(--text-primary)' }}>
                  {dbSummary.latest_timestamp ? new Date(dbSummary.latest_timestamp).toLocaleString() : 'N/A'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Retention Policy:</span>
                <span style={{ color: 'var(--text-secondary)' }}>
                  {dbSummary.retention_days ? `${dbSummary.retention_days} Days Purge Policy` : 'Unlimited Retention'}
                </span>
              </div>
            </div>
          ) : (
            <EmptyState message="No database summary metadata." height={140} />
          )}
        </Card>

        {/* API Gateway & OpenAPI Info */}
        <Card
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
              <Info size={15} style={{ color: 'var(--accent-primary)' }} />
              <span>FastAPI REST Services &amp; Docs</span>
            </div>
          }
          subtitle="Backend integration endpoints and schema documentation"
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 12.5 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>API Server URL:</span>
              <a
                href="http://localhost:8000"
                target="_blank"
                rel="noreferrer"
                style={{ color: 'var(--accent-primary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
              >
                http://localhost:8000 <ExternalLink size={12} />
              </a>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Interactive API Docs:</span>
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noreferrer"
                style={{ color: 'var(--accent-primary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
              >
                http://localhost:8000/docs <ExternalLink size={12} />
              </a>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>Liveness Probe:</span>
              <code style={{ color: 'var(--text-primary)' }}>GET /healthz</code>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-muted)' }}>Active ML Mode:</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                {modelStatus?.mode ?? 'Isolation Forest / Heuristic'}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Validation Logs Audit Table */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <AlertTriangle size={15} style={{ color: 'var(--status-warning)' }} />
            <span>Recent Telemetry Preprocessing Validation Audit Logs ({validationLogs.length} Rows)</span>
          </div>
        }
        subtitle="Recent validation log issues recorded during feature preprocessing"
      >
        {validationLogs.length > 0 ? (
          <div className="op-table-wrapper">
            <table className="op-table" style={{ minWidth: 800 }}>
              <thead>
                <tr>
                  <th>Audit ID</th>
                  <th>Metric ID</th>
                  <th>Timestamp</th>
                  <th>Validation Result</th>
                  <th>Issues Count</th>
                  <th>Severity</th>
                  <th>Audit Message / Issues Detail</th>
                </tr>
              </thead>
              <tbody>
                {validationLogs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ fontWeight: 600, color: 'var(--text-muted)' }}>#{log.id}</td>
                    <td>{log.metric_id ? `#${log.metric_id}` : '--'}</td>
                    <td>{new Date(log.timestamp).toLocaleString()}</td>
                    <td>
                      <StatusBadge
                        status={log.is_valid ? 'VALID' : 'INVALID'}
                        type={log.is_valid ? 'healthy' : 'warning'}
                      />
                    </td>
                    <td style={{ fontWeight: 600 }}>{log.issues_count}</td>
                    <td>
                      <StatusBadge
                        status={log.has_errors ? 'ERRORS' : 'WARNINGS'}
                        type={log.has_errors ? 'critical' : 'warning'}
                      />
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {log.issues && log.issues.length > 0
                        ? log.issues.map((iss, i) => (
                            <div key={i}>
                              {iss.field ? `[${iss.field}] ` : ''}
                              {iss.message || JSON.stringify(iss)}
                            </div>
                          ))
                        : 'No issue details recorded'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Clean Validation Audit Log"
            message="No validation issues or schema errors recorded in the validation_logs table."
            height={140}
          />
        )}
      </Card>
    </div>
  );
};
