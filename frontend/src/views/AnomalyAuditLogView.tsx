import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertOctagon,
  Download,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import {
  downloadCsv,
  getAnomaliesHistory,
  getExportAnomaliesUrl,
} from '../api';
import { AnomalyScatterChart } from '../components/charts';
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from '../components/common';
import type { AnomalyAuditItem } from '../types';

export const AnomalyAuditLogView: React.FC = () => {
  const [anomalies, setAnomalies] = useState<AnomalyAuditItem[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [limit, setLimit] = useState<number>(100);
  const [anomaliesOnly, setAnomaliesOnly] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [exporting, setExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnomalies = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getAnomaliesHistory({
        limit,
        anomalies_only: anomaliesOnly,
      });
      setAnomalies(res.anomalies);
      setTotalCount(res.count);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to query historical anomalies.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [limit, anomaliesOnly]);

  useEffect(() => {
    fetchAnomalies();
  }, [fetchAnomalies]);

  const handleExportCsv = async () => {
    try {
      setExporting(true);
      const url = getExportAnomaliesUrl({
        limit,
        anomalies_only: anomaliesOnly,
      });
      await downloadCsv(url, 'anomalies_audit_export.csv');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'CSV export failed.';
      alert(msg);
    } finally {
      setExporting(false);
    }
  };

  const flaggedCount = anomalies.filter((a) => a.is_anomaly).length;

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="page-title">
            <AlertOctagon size={20} style={{ color: 'var(--accent-primary)' }} />
            <span>Anomaly Evaluation &amp; Inference Audit Log</span>
          </div>
          <div className="page-subtitle">
            Historical Isolation Forest inference vectors, decision score trajectories, and deterministic risk classifications
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span
            style={{
              fontSize: 12,
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: flaggedCount > 0 ? 'var(--status-critical-bg)' : 'rgba(30, 41, 59, 0.7)',
              border: `1px solid ${flaggedCount > 0 ? 'var(--status-critical-border)' : 'var(--border-subtle)'}`,
              color: flaggedCount > 0 ? 'var(--status-critical)' : 'var(--text-secondary)',
              fontWeight: 600,
            }}
          >
            {flaggedCount} Anomalies in View ({totalCount.toLocaleString()} Total Evaluated)
          </span>

          <Button
            variant="primary"
            size="sm"
            icon={<Download size={13} />}
            loading={exporting}
            onClick={handleExportCsv}
          >
            Export Anomaly CSV
          </Button>
        </div>
      </div>

      {/* Controls & Filter Toolbar */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <AlertOctagon size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Audit Log Filters &amp; Parameters</span>
          </div>
        }
        subtitle="Filter evaluated feature vectors by sample threshold and strict anomaly flag"
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
            {/* Limit selector */}
            <div className="form-group" style={{ width: 140 }}>
              <label className="form-label" htmlFor="anom-limit-select">Sample Limit</label>
              <select
                id="anom-limit-select"
                className="form-select"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
              >
                <option value={50}>50 rows</option>
                <option value={100}>100 rows</option>
                <option value={200}>200 rows</option>
                <option value={500}>500 rows</option>
              </select>
            </div>

            {/* Filter Anomalies Only Checkbox */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                marginTop: 18,
                fontSize: 12.5,
                color: 'var(--text-secondary)',
              }}
            >
              <input
                id="anomalies-only-check"
                type="checkbox"
                checked={anomaliesOnly}
                onChange={(e) => setAnomaliesOnly(e.target.checked)}
                style={{ cursor: 'pointer', accentColor: 'var(--status-critical)', width: 15, height: 15 }}
              />
              <label htmlFor="anomalies-only-check" style={{ cursor: 'pointer', fontWeight: 600 }}>
                Strict Anomalies Only ({flaggedCount} flagged)
              </label>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4 }}>
            <Button
              variant="secondary"
              icon={<RefreshCw size={13} />}
              loading={loading}
              onClick={fetchAnomalies}
            >
              Refresh Log
            </Button>
          </div>
        </div>
      </Card>

      {/* Error State */}
      {error && (
        <ErrorState
          title="Failed to Load Anomaly Audit Log"
          message={error}
          onRetry={fetchAnomalies}
          height={180}
        />
      )}

      {/* Anomaly Distribution Scatter & Threshold Chart */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <ShieldAlert size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Anomaly Score Trajectory &amp; Decision Boundary</span>
          </div>
        }
        subtitle="Isolation Forest score evaluated per historical sample (Threshold = 0.50)"
      >
        {loading ? (
          <LoadingState message="Scoring historical feature vectors..." height={240} />
        ) : anomalies.length > 0 ? (
          <AnomalyScatterChart data={anomalies} height={260} />
        ) : (
          <EmptyState
            title="No Anomaly Audit Records"
            message="No historical samples found matching filter criteria."
            height={200}
          />
        )}
      </Card>

      {/* Anomaly Records Table */}
      <Card
        title={`Anomaly Evaluation Audit Ledger (${anomalies.length} of ${totalCount.toLocaleString()} evaluated)`}
        subtitle="Scored feature vectors with correlated hardware telemetry"
      >
        {loading ? (
          <LoadingState message="Loading anomaly audit records..." height={200} />
        ) : anomalies.length > 0 ? (
          <div className="op-table-wrapper">
            <table className="op-table op-table-wide">
              <thead>
                <tr>
                  <th>Feature ID</th>
                  <th>Metric ID</th>
                  <th>Timestamp</th>
                  <th>Anomaly Score</th>
                  <th>Inference Status</th>
                  <th>Health Score</th>
                  <th>Risk Tier</th>
                  <th>Model Engine</th>
                  <th>CPU %</th>
                  <th>RAM %</th>
                  <th>Disk %</th>
                  <th>Network</th>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a) => {
                  const isAnom = a.is_anomaly;
                  return (
                    <tr
                      key={a.feature_id}
                      style={{
                        backgroundColor: isAnom ? 'rgba(239, 68, 68, 0.07)' : undefined,
                      }}
                    >
                      <td style={{ fontWeight: 600, color: 'var(--text-muted)' }}>
                        #{a.feature_id}
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>
                        {a.metric_id ? `#${a.metric_id}` : '--'}
                      </td>
                      <td>{new Date(a.timestamp).toLocaleString()}</td>
                      <td>
                        <span
                          style={{
                            fontWeight: 700,
                            color: isAnom ? 'var(--status-critical)' : 'var(--accent-primary)',
                            fontVariantNumeric: 'tabular-nums',
                          }}
                        >
                          {a.anomaly_score.toFixed(3)}
                        </span>
                      </td>
                      <td>
                        <StatusBadge
                          status={isAnom ? 'ANOMALOUS' : 'NOMINAL'}
                          type={isAnom ? 'critical' : 'healthy'}
                        />
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {a.health_score !== null ? `${a.health_score.toFixed(1)}/100` : '--'}
                      </td>
                      <td>
                        <StatusBadge status={a.risk_category} />
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {a.model_name}{' '}
                        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                          ({a.is_trained_model ? 'Trained' : 'Heuristic'})
                        </span>
                      </td>
                      <td style={{ fontWeight: 500, color: (a.cpu_percent ?? 0) >= 80 ? 'var(--status-critical)' : undefined }}>
                        {a.cpu_percent !== null ? `${a.cpu_percent.toFixed(1)}%` : '--'}
                      </td>
                      <td style={{ fontWeight: 500, color: (a.memory_percent ?? 0) >= 80 ? 'var(--status-critical)' : undefined }}>
                        {a.memory_percent !== null ? `${a.memory_percent.toFixed(1)}%` : '--'}
                      </td>
                      <td>
                        {a.disk_percent !== null ? `${a.disk_percent.toFixed(1)}%` : '--'}
                      </td>
                      <td>
                        {a.network_kbps !== null ? `${a.network_kbps.toFixed(1)} KB/s` : '--'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No Records Found"
            message={anomaliesOnly ? 'No anomalies detected in the evaluated range.' : 'No audit records exist.'}
            height={160}
          />
        )}
      </Card>
    </div>
  );
};
