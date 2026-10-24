import React, { useCallback, useEffect, useState } from 'react';
import {
  captureSnapshot,
  getMonitoringStatus,
  getSystemStatus,
  startMonitoring,
  stopMonitoring,
} from './api';
import { Layout } from './components/layout';
import type { ViewType } from './components/layout';
import {
  AnomalyAuditLogView,
  DatabaseStatusView,
  HealthRiskView,
  HistoricalTelemetryView,
  RealTimeMonitoringView,
  SimulationStudioView,
  SystemOverviewView,
} from './views';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewType>('overview');
  const [apiConnected, setApiConnected] = useState<boolean>(true);
  const [isBgRunning, setIsBgRunning] = useState<boolean>(false);
  const [isSnapshotLoading, setIsSnapshotLoading] = useState<boolean>(false);
  const [isTogglingWorker, setIsTogglingWorker] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false);
  const [refreshInterval, setRefreshInterval] = useState<number>(5);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState<number>(0);

  // Check background worker and API liveness
  const checkHealth = useCallback(async () => {
    try {
      const [sysStatus, monStatus] = await Promise.all([
        getSystemStatus().catch(() => null),
        getMonitoringStatus().catch(() => null),
      ]);

      if (sysStatus || monStatus) {
        setApiConnected(true);
      } else {
        setApiConnected(false);
      }

      if (monStatus) {
        setIsBgRunning(monStatus.is_running);
      }
      setLastUpdated(new Date().toLocaleTimeString());
    } catch {
      setApiConnected(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Global manual refresh trigger
  const handleRefreshNow = useCallback(() => {
    checkHealth();
    setRefreshKey((prev) => prev + 1);
    setLastUpdated(new Date().toLocaleTimeString());
  }, [checkHealth]);

  // Auto-refresh interval
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      handleRefreshNow();
    }, refreshInterval * 1000);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, handleRefreshNow]);

  // Capture on-demand live snapshot
  const handleCaptureSnapshot = async () => {
    try {
      setIsSnapshotLoading(true);
      const res = await captureSnapshot(true);
      if (res.success) {
        handleRefreshNow();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to capture snapshot.';
      alert(msg);
    } finally {
      setIsSnapshotLoading(false);
    }
  };

  // Toggle background worker thread
  const handleToggleWorker = async () => {
    try {
      setIsTogglingWorker(true);
      if (isBgRunning) {
        const res = await stopMonitoring();
        setIsBgRunning(res.is_running);
      } else {
        const res = await startMonitoring();
        setIsBgRunning(res.is_running);
      }
      handleRefreshNow();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to toggle background monitoring.';
      alert(msg);
    } finally {
      setIsTogglingWorker(false);
    }
  };

  // Render view component based on currentView
  const renderView = () => {
    switch (currentView) {
      case 'overview':
        return <SystemOverviewView key={refreshKey} />;
      case 'health':
        return <HealthRiskView key={refreshKey} />;
      case 'simulation':
        return <SimulationStudioView key={refreshKey} />;
      case 'realtime':
        return <RealTimeMonitoringView key={refreshKey} />;
      case 'history':
        return <HistoricalTelemetryView key={refreshKey} />;
      case 'anomalies':
        return <AnomalyAuditLogView key={refreshKey} />;
      case 'database':
        return <DatabaseStatusView key={refreshKey} />;
      default:
        return <SystemOverviewView key={refreshKey} />;
    }
  };

  return (
    <Layout
      currentView={currentView}
      onSelectView={setCurrentView}
      apiConnected={apiConnected}
      isBgRunning={isBgRunning}
      isSnapshotLoading={isSnapshotLoading}
      isTogglingWorker={isTogglingWorker}
      autoRefresh={autoRefresh}
      refreshInterval={refreshInterval}
      lastUpdated={lastUpdated}
      onCaptureSnapshot={handleCaptureSnapshot}
      onToggleWorker={handleToggleWorker}
      onRefreshNow={handleRefreshNow}
      onToggleAutoRefresh={setAutoRefresh}
      onChangeRefreshInterval={setRefreshInterval}
    >
      {renderView()}
    </Layout>
  );
};

export default App;
