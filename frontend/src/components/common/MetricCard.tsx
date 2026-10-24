import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  subtext?: React.ReactNode;
  icon?: React.ReactNode;
  percentage?: number | null;
  status?: 'healthy' | 'warning' | 'critical' | 'info';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subtext,
  icon,
  percentage,
  status,
  className = '',
}) => {
  // Determine severity and progress bar color
  let barColor = 'var(--accent-primary)';
  let borderColor = 'var(--border-default)';

  if (status === 'critical' || (percentage !== undefined && percentage !== null && percentage >= 85)) {
    barColor = 'var(--status-critical)';
    borderColor = 'rgba(239, 68, 68, 0.45)';
  } else if (status === 'warning' || (percentage !== undefined && percentage !== null && percentage >= 70)) {
    barColor = 'var(--status-warning)';
    borderColor = 'rgba(245, 158, 11, 0.45)';
  } else if (status === 'healthy' || (percentage !== undefined && percentage !== null && percentage < 70)) {
    barColor = 'var(--status-healthy)';
    borderColor = 'rgba(16, 185, 129, 0.35)';
  }

  return (
    <div
      className={`metric-card ${className}`}
      style={{
        borderColor,
      }}
    >
      {/* Top Header: Label & Icon */}
      <div className="metric-card-top">
        <span className="metric-card-label">{label}</span>
        {icon && <div className="metric-card-icon">{icon}</div>}
      </div>

      {/* Main KPI Value */}
      <div className="metric-card-value-wrap">
        <span className="metric-card-value">{value}</span>
        {unit && <span className="metric-card-unit">{unit}</span>}
      </div>

      {/* Progress Bar (if percentage is provided) */}
      {percentage !== undefined && percentage !== null && (
        <div className="metric-progress-bg">
          <div
            className="metric-progress-bar"
            style={{
              width: `${Math.min(100, Math.max(0, percentage))}%`,
              backgroundColor: barColor,
            }}
          />
        </div>
      )}

      {/* Supporting details / Subtext */}
      {subtext && <div className="metric-card-footer">{subtext}</div>}
    </div>
  );
};
