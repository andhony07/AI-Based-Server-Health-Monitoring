import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import type { ViewType } from './Sidebar';
import { TopBar } from './TopBar';

interface LayoutProps {
  currentView: ViewType;
  onSelectView: (view: ViewType) => void;
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
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({
  currentView,
  onSelectView,
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
  children,
}) => {
  const [collapsed, setCollapsed] = useState<boolean>(false);
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);

  return (
    <div className="app-layout">
      <Sidebar
        currentView={currentView}
        onSelectView={onSelectView}
        apiConnected={apiConnected}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(!collapsed)}
        isMobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <div className="main-content">
        <TopBar
          currentView={currentView}
          apiConnected={apiConnected}
          isBgRunning={isBgRunning}
          isSnapshotLoading={isSnapshotLoading}
          isTogglingWorker={isTogglingWorker}
          autoRefresh={autoRefresh}
          refreshInterval={refreshInterval}
          lastUpdated={lastUpdated}
          onCaptureSnapshot={onCaptureSnapshot}
          onToggleWorker={onToggleWorker}
          onRefreshNow={onRefreshNow}
          onToggleAutoRefresh={onToggleAutoRefresh}
          onChangeRefreshInterval={onChangeRefreshInterval}
          onOpenMobileMenu={() => setMobileOpen(true)}
        />
        <main className="main-scroll-area" id="main-scroll-container">
          {children}
        </main>
      </div>
    </div>
  );
};
