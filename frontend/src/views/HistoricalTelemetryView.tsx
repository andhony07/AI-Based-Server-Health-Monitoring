import React, { useCallback, useEffect, useState } from 'react';
import {
  Download,
  Filter,
  History,
  Search,
} from 'lucide-react';
import {
  downloadCsv,
  getExportMetricsUrl,
  getTelemetryHistory,
} from '../api';
import { TelemetryTimeseriesChart } from '../components/charts';
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
} from '../components/common';
import type { SystemMetricRecord } from '../types';

export const HistoricalTelemetryView: React.FC = () => {
  const [records, setRecords] = useState<SystemMetricRecord[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [limit, setLimit] = useState<number>(100);
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(true);
  const [exporting, setExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getTelemetryHistory({
        limit,
        start_time: startTime ? new Date(startTime).toISOString() : undefined,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
      });
      setRecords(res.records);
      setTotalCount(res.count);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to query historical telemetry.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [limit, startTime, endTime]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleExportCsv = async () => {
    try {
      setExporting(true);
      const url = getExportMetricsUrl({
        limit,
        start_time: startTime ? new Date(startTime).toISOString() : undefined,
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
      });
      await downloadCsv(url, 'system_metrics_export.csv');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'CSV export failed.';
      alert(msg);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <div className="page-title">
            <History size={20} style={{ color: 'var(--accent-primary)' }} />
            <span>Historical Telemetry Repository</span>
          </div>
          <div className="page-subtitle">
            Query persisted hardware samples, inspect multi-resource curves, and export timestamped compliance datasets
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span
            style={{
              fontSize: 12,
              padding: '4px 10px',
              borderRadius: 'var(--radius-sm)',
              backgroundColor: 'rgba(30, 41, 59, 0.7)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
          >
            Database Total: <strong style={{ color: 'var(--accent-primary)' }}>{totalCount.toLocaleString()}</strong> Records
          </span>

          <Button
            variant="primary"
            size="sm"
            icon={<Download size={13} />}
            loading={exporting}
            onClick={handleExportCsv}
          >
            Export RFC-4180 CSV
          </Button>
        </div>
      </div>

      {/* Query & Filter Toolbar */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Filter size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Telemetry Query &amp; Filter Parameters</span>
          </div>
        }
        subtitle="Filter persisted SQLite hardware samples by record limit and UTC timestamp boundaries"
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-end',
            flexWrap: 'wrap',
            gap: 14,
          }}
        >
          {/* Limit selector */}
          <div className="form-group" style={{ width: 140 }}>
            <label className="form-label" htmlFor="hist-limit-select">Sample Limit</label>
            <select
              id="hist-limit-select"
              className="form-select"
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
            >
              <option value={50}>50 samples</option>
              <option value={100}>100 samples</option>
              <option value={200}>200 samples</option>
              <option value={500}>500 samples</option>
              <option value={1000}>1,000 samples</option>
            </select>
          </div>

          {/* Start Time */}
          <div className="form-group" style={{ flex: '1 1 200px', minWidth: 190 }}>
            <label className="form-label" htmlFor="hist-start-time">Start Timestamp (Local)</label>
            <input
              id="hist-start-time"
              type="datetime-local"
              className="form-input"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </div>

          {/* End Time */}
          <div className="form-group" style={{ flex: '1 1 200px', minWidth: 190 }}>
            <label className="form-label" htmlFor="hist-end-time">End Timestamp (Local)</label>
            <input
              id="hist-end-time"
              type="datetime-local"
              className="form-input"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
          </div>

          {/* Apply Query Button */}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 10 }}>
            {(startTime || endTime) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setStartTime('');
                  setEndTime('');
                }}
              >
                Clear Times
              </Button>
            )}

            <Button
              variant="secondary"
              icon={<Search size={14} />}
              loading={loading}
              onClick={fetchHistory}
            >
              Execute Query
            </Button>
          </div>
        </div>
      </Card>

      {/* Error Banner */}
      {error && (
        <ErrorState
          title="Failed to Load Historical Telemetry"
          message={error}
          onRetry={fetchHistory}
          height={180}
        />
      )}

      {/* Time-Series Trend of Query Result */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <History size={15} style={{ color: 'var(--accent-primary)' }} />
            <span>Historical Resource Trajectory ({records.length} Points Plotted)</span>
          </div>
        }
        subtitle="Chronological multi-resource usage curve across selected query window"
      >
        {loading ? (
          <LoadingState message="Querying time-series metrics..." height={240} />
        ) : records.length > 0 ? (
          <TelemetryTimeseriesChart data={records} height={260} showDisk={true} />
        ) : (
          <EmptyState
            title="No Telemetry Records Found"
            message="No historical samples match the selected timestamp and limit criteria."
            height={200}
          />
        )}
      </Card>

      {/* Tabular Log */}
      <Card
        title={`Persisted Telemetry Ledger (${records.length} of ${totalCount.toLocaleString()} total rows)`}
        subtitle="Chronological SQLite hardware samples with process attribution"
      >
        {loading ? (
          <LoadingState message="Rendering telemetry data table..." height={200} />
        ) : records.length > 0 ? (
          <div className="op-table-wrapper">
            <table className="op-table op-table-wide">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Timestamp</th>
                  <th>CPU %</th>
                  <th>Cores</th>
                  <th>Memory %</th>
                  <th>Memory Used</th>
                  <th>Disk %</th>
                  <th>Disk Used</th>
                  <th>Net Upload</th>
                  <th>Net Download</th>
                  <th>Top Monitored Process</th>
                  <th>Processes</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => {
                  const memUsedGb = r.memory_used_bytes
                    ? `${(r.memory_used_bytes / (1024 ** 3)).toFixed(1)} GB`
                    : '--';
                  const diskUsedGb = r.disk_used_bytes
                    ? `${(r.disk_used_bytes / (1024 ** 3)).toFixed(1)} GB`
                    : '--';
                  const uploadSec = r.network_bytes_sent_per_sec !== null && r.network_bytes_sent_per_sec !== undefined
                    ? `${(r.network_bytes_sent_per_sec / 1024).toFixed(1)} KB/s`
                    : '0.0 KB/s';
                  const downloadSec = r.network_bytes_recv_per_sec !== null && r.network_bytes_recv_per_sec !== undefined
                    ? `${(r.network_bytes_recv_per_sec / 1024).toFixed(1)} KB/s`
                    : '0.0 KB/s';

                  return (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-muted)' }}>#{r.id}</td>
                      <td>{new Date(r.timestamp).toLocaleString()}</td>
                      <td style={{ fontWeight: 600, color: (r.cpu_percent ?? 0) >= 80 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
                        {r.cpu_percent !== null ? `${r.cpu_percent.toFixed(1)}%` : '--'}
                      </td>
                      <td>{r.cpu_logical_cores ?? '--'}</td>
                      <td style={{ fontWeight: 600, color: (r.memory_percent ?? 0) >= 80 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
                        {r.memory_percent !== null ? `${r.memory_percent.toFixed(1)}%` : '--'}
                      </td>
                      <td>{memUsedGb}</td>
                      <td>{r.disk_percent !== null ? `${r.disk_percent.toFixed(1)}%` : '--'}</td>
                      <td>{diskUsedGb}</td>
                      <td>{uploadSec}</td>
                      <td>{downloadSec}</td>
                      <td style={{ color: 'var(--accent-primary)', fontWeight: 500 }}>
                        {r.top_process_name ? `${r.top_process_name} (${r.top_process_cpu_percent?.toFixed(1)}%)` : '--'}
                      </td>
                      <td>{r.process_count ?? '--'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Empty Telemetry Table"
            message="No records found in database for current query parameters."
            height={160}
          />
        )}
      </Card>
    </div>
  );
};
