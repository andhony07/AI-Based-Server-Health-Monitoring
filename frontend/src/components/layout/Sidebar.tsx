import React from 'react';
import {
  Activity,
  AlertOctagon,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Database,
  FlaskConical,
  History,
  LayoutDashboard,
  ShieldCheck,
  X,
} from 'lucide-react';

export type ViewType =
  | 'overview'
  | 'health'
  | 'simulation'
  | 'realtime'
  | 'history'
  | 'anomalies'
  | 'database';

interface SidebarProps {
  currentView: ViewType;
  onSelectView: (view: ViewType) => void;
  apiConnected: boolean;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  id: ViewType;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentView,
  onSelectView,
  apiConnected,
  collapsed = false,
  onToggleCollapse,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const navItems: NavItem[] = [
    {
      id: 'overview',
      label: 'System Overview',
      icon: <LayoutDashboard size={18} />,
    },
    {
      id: 'health',
      label: 'Health & Risk Analysis',
      icon: <ShieldCheck size={18} />,
    },
    {
      id: 'simulation',
      label: 'Anomaly Simulation',
      icon: <FlaskConical size={18} />,
    },
    {
      id: 'realtime',
      label: 'Real-Time Monitoring',
      icon: <Activity size={18} />,
    },
    {
      id: 'history',
      label: 'Historical Telemetry',
      icon: <History size={18} />,
    },
    {
      id: 'anomalies',
      label: 'Anomaly Audit Log',
      icon: <AlertOctagon size={18} />,
    },
    {
      id: 'database',
      label: 'Database & Status',
      icon: <Database size={18} />,
    },
  ];

  const sidebarWidth = collapsed ? 68 : 248;

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.65)',
            zIndex: 40,
            backdropFilter: 'blur(2px)',
          }}
        />
      )}

      <aside
        style={{
          width: sidebarWidth,
          backgroundColor: 'var(--bg-sidebar)',
          borderRight: '1px solid var(--border-default)',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          userSelect: 'none',
          flexShrink: 0,
          transition: 'width 200ms cubic-bezier(0.4, 0, 0.2, 1)',
          zIndex: 45,
          position: isMobileOpen ? 'fixed' : 'relative',
          top: 0,
          bottom: 0,
          left: 0,
        }}
      >
        {/* Brand Header */}
        <div
          style={{
            padding: collapsed ? '16px 12px' : '16px 16px',
            borderBottom: '1px solid var(--border-default)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 'var(--topbar-height)',
            boxSizing: 'border-box',
          }}
        >
          {!collapsed ? (
            <div style={{ overflow: 'hidden' }}>
              <div style={{ marginBottom: 4 }}>
                <span
                  style={{
                    fontSize: 10,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    fontWeight: 700,
                    letterSpacing: 0.5,
                  }}
                >
                  Operations Center
                </span>
              </div>
              <h1
                style={{
                  fontSize: 14,
                  fontWeight: 700,
                  color: 'var(--text-primary)',
                  letterSpacing: -0.3,
                  lineHeight: 1.2,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  whiteSpace: 'nowrap',
                }}
              >
                <Cpu size={16} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
                Server Health AI
              </h1>
            </div>
          ) : (
            <div style={{ margin: '0 auto' }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 6,
                  backgroundColor: 'rgba(56, 189, 248, 0.12)',
                  border: '1px solid rgba(56, 189, 248, 0.35)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--accent-primary)',
                }}
                title="Server Health AI"
              >
                <Cpu size={18} />
              </div>
            </div>
          )}

          {/* Desktop Collapse Toggle / Mobile Close */}
          {isMobileOpen ? (
            <button
              type="button"
              onClick={onCloseMobile}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: 4,
              }}
            >
              <X size={18} />
            </button>
          ) : (
            onToggleCollapse && (
              <button
                type="button"
                onClick={onToggleCollapse}
                title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
                style={{
                  background: 'none',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 4,
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 24,
                  height: 24,
                  transition: 'background-color 150ms ease, color 150ms ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                  e.currentTarget.style.color = 'var(--text-muted)';
                }}
              >
                {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
              </button>
            )
          )}
        </div>

        {/* Navigation List */}
        <nav
          style={{
            flex: 1,
            padding: collapsed ? '12px 6px' : '14px 10px',
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
            overflowY: 'auto',
          }}
        >
          {!collapsed && (
            <div
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: 0.8,
                padding: '4px 8px 8px 8px',
              }}
            >
              Operations Menu
            </div>
          )}

          {navItems.map((item) => {
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                id={`nav-item-${item.id}`}
                data-view-id={item.id}
                type="button"
                onClick={() => {
                  onSelectView(item.id);
                  if (onCloseMobile) onCloseMobile();
                }}
                title={collapsed ? item.label : undefined}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  height: 38,
                  padding: collapsed ? '0' : '0 10px',
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isActive ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                  color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  border: '1px solid',
                  borderColor: isActive ? 'rgba(56, 189, 248, 0.4)' : 'transparent',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: 12.5,
                  cursor: 'pointer',
                  textAlign: 'left',
                  width: '100%',
                  transition: 'all 150ms ease',
                  position: 'relative',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'var(--bg-card-hover)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }
                }}
              >
                {isActive && (
                  <span
                    style={{
                      position: 'absolute',
                      left: 0,
                      top: '20%',
                      bottom: '20%',
                      width: 3,
                      borderRadius: '0 2px 2px 0',
                      backgroundColor: 'var(--accent-primary)',
                    }}
                  />
                )}
                <span
                  style={{
                    color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  {item.icon}
                </span>
                {!collapsed && (
                  <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.label}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom Service Status Footer */}
        <div
          style={{
            padding: collapsed ? '12px 6px' : '12px 14px',
            borderTop: '1px solid var(--border-default)',
            backgroundColor: '#0D1420',
            fontSize: 11,
            display: 'flex',
            flexDirection: 'column',
            gap: 5,
          }}
        >
          {!collapsed ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>FastAPI Gateway:</span>
                <span
                  style={{
                    color: apiConnected ? 'var(--status-healthy)' : 'var(--status-critical)',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 5,
                    fontSize: 10.5,
                  }}
                >
                  <span
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: apiConnected ? 'var(--status-healthy)' : 'var(--status-critical)',
                    }}
                  />
                  {apiConnected ? 'ONLINE' : 'OFFLINE'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#64748B', fontSize: 10 }}>
                <span>API :8000</span>
                <span>Vite :5173</span>
                <span>Streamlit :8501</span>
              </div>
            </>
          ) : (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
              }}
              title={apiConnected ? 'FastAPI Gateway: ONLINE' : 'FastAPI Gateway: OFFLINE'}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: apiConnected ? 'var(--status-healthy)' : 'var(--status-critical)',
                }}
              />
            </div>
          )}
        </div>
      </aside>
    </>
  );
};
