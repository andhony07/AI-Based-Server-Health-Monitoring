import React from 'react';
import {
  Camera,
  CheckCircle2,
  Menu,
  Play,
  RefreshCw,
  Square,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { Button } from '../common';
import type { ViewType } from './Sidebar';

interface TopBarProps {
  currentView: ViewType;
  apiConnected: boolean;
  isBgRunning: boolean;
  isSnapshotLoading: boolean;
  isTogglingWorker: boolean;
  autoRefresh: boolean;
  refreshInterval: number;
  lastUpdated: string | null;
  onCaptureSnapshot: () => void;
  onToggleWorker: () => void;
  onRefreshNow: () => void;
  onToggleAutoRefresh: (enabled: boolean) => void;
  onChangeRefreshInterval: (interval: number) => void;
  onOpenMobileMenu?: () => void;
}

const VIEW_TITLES: Record<ViewType, { title: string; subtitle: string }> = {
  overview: {
    title: 'System Overview',
    subtitle: 'Unified host resource metrics, ML risk evaluation, and hardware telemetry',
  },
  health: {
    title: 'Health & Risk Analysis',
    subtitle: 'Deterministic 0–100 health scoring, Isolation Forest inference, and explainable root-cause evidence',
  },
  simulation: {
    title: 'Anomaly Simulation Studio',
    subtitle: 'Deterministic synthetic failure injection and end-to-end pipeline diagnosis',
  },
  realtime: {
    title: 'Real-Time Monitoring',
    subtitle: 'Continuous hardware telemetry streaming with sub-second polling and process inspection',
  },
  history: {
    title: 'Historical Telemetry',
    subtitle: 'Chronological time-series ledger with temporal filters and RFC-4180 CSV export',
  },
  anomalies: {
    title: 'Anomaly Audit Log',
    subtitle: 'Historical anomaly evaluation records scored against Isolation Forest decision boundaries',
  },
  database: {
    title: 'Database & Operational Status',
    subtitle: 'SQLite physical storage summary, subsystem integrity, and validation audit logs',
  },
};

export const TopBar: React.FC<TopBarProps> = ({
  currentView,
  apiConnected,
  isBgRunning,
  isSnapshotLoading,
  isTogglingWorker,
  autoRefresh,
  refreshInterval,
  lastUpdated,
  onCaptureSnapshot,
  onToggleWorker,
  onRefreshNow,
  onToggleAutoRefresh,
  onChangeRefreshInterval,
  onOpenMobileMenu,
}) => {
  const currentMeta = VIEW_TITLES[currentView] || VIEW_TITLES.overview;

  return (
    <header
      style={{
        height: 'var(--topbar-height)',
        backgroundColor: 'var(--bg-topbar)',
        borderBottom: '1px solid var(--border-default)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        flexShrink: 0,
        zIndex: 20,
        gap: 16,
        width: '100%',
        maxWidth: '100%',
        minWidth: 0,
      }}
    >
      {/* Title & View Metadata + Mobile Hamburger */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
        {onOpenMobileMenu && (
          <button
            type="button"
            onClick={onOpenMobileMenu}
            className="mobile-menu-btn"
            style={{
              background: 'none',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '6px',
              display: 'none',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Menu size={18} />
          </button>
        )}
        <div style={{ minWidth: 0, overflow: 'hidden' }}>
          <h2
            style={{
              fontSize: 15.5,
              fontWeight: 700,
              color: 'var(--text-primary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {currentMeta.title}
          </h2>
          <p
            style={{
              fontSize: 11.5,
              color: 'var(--text-muted)',
              marginTop: 1,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {currentMeta.subtitle}
          </p>
        </div>
      </div>

      {/* Global Actions Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        {/* API Status Badge */}
        <div
          className={`status-badge ${apiConnected ? 'healthy' : 'critical'}`}
          style={{ height: 28, padding: '0 9px' }}
          title={apiConnected ? 'Connected to FastAPI REST Gateway' : 'Backend connection unavailable'}
        >
          {apiConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
          <span>{apiConnected ? 'API ONLINE' : 'DISCONNECTED'}</span>
        </div>

        {/* Live Snapshot Button */}
        <Button
          variant="primary"
          size="sm"
          icon={<Camera size={13} />}
          loading={isSnapshotLoading}
          disabled={!apiConnected}
          onClick={onCaptureSnapshot}
          title="Captures on-demand live psutil metrics, runs feature engineering, and evaluates ML risk"
        >
          Capture Snapshot
        </Button>

        {/* Background Worker Start/Stop */}
        <Button
          variant={isBgRunning ? 'danger' : 'secondary'}
          size="sm"
          icon={isBgRunning ? <Square size={12} /> : <Play size={12} />}
          loading={isTogglingWorker}
          disabled={!apiConnected}
          onClick={onToggleWorker}
          title={isBgRunning ? 'Stop background telemetry collection thread' : 'Start background telemetry collection thread'}
        >
          {isBgRunning ? 'Stop Worker' : 'Start Worker'}
        </Button>

        {/* Auto Refresh & Controls */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            padding: '3px 8px',
            height: 28,
            boxSizing: 'border-box',
          }}
        >
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              color: autoRefresh ? 'var(--accent-primary)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => onToggleAutoRefresh(e.target.checked)}
              style={{ cursor: 'pointer', accentColor: 'var(--accent-primary)' }}
            />
            Auto
          </label>

          {autoRefresh && (
            <select
              value={refreshInterval}
              onChange={(e) => onChangeRefreshInterval(Number(e.target.value))}
              style={{
                backgroundColor: 'transparent',
                color: 'var(--accent-primary)',
                border: 'none',
                fontSize: 11,
                fontWeight: 700,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value={2} style={{ background: '#111827' }}>2s</option>
              <option value={5} style={{ background: '#111827' }}>5s</option>
              <option value={10} style={{ background: '#111827' }}>10s</option>
              <option value={30} style={{ background: '#111827' }}>30s</option>
            </select>
          )}

          <button
            type="button"
            onClick={onRefreshNow}
            title="Refresh current view now"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: 2,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <RefreshCw size={12} />
          </button>
        </div>

        {/* Timestamp */}
        {lastUpdated && (
          <div
            style={{
              fontSize: 11,
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              paddingLeft: 4,
            }}
            title={`Last updated at ${lastUpdated}`}
          >
            <CheckCircle2 size={12} style={{ color: 'var(--status-healthy)' }} />
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>{lastUpdated}</span>
          </div>
        )}
      </div>
      <style>{`
        @media (max-width: 900px) {
          .mobile-menu-btn {
            display: flex !important;
          }
        }
      `}</style>
    </header>
  );
};
