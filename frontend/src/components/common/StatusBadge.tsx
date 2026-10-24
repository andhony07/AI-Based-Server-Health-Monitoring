import React from 'react';

export type StatusType =
  | 'healthy'
  | 'warning'
  | 'critical'
  | 'info'
  | 'neutral';

interface StatusBadgeProps {
  status: string | null | undefined;
  type?: StatusType;
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  type,
  label,
  className = '',
}) => {
  const normalized = (status || '').toUpperCase().trim();

  // Infer type if not explicitly supplied
  let inferredType: StatusType = type || 'neutral';
  if (!type) {
    if (['HEALTHY', 'NOMINAL', 'OPERATIONAL', 'FRESH', 'SUCCESS', 'OK', 'READY', 'ACTIVE'].includes(normalized)) {
      inferredType = 'healthy';
    } else if (['WARNING', 'MODERATE', 'ELEVATED', 'WARM', 'DEGRADED'].includes(normalized)) {
      inferredType = 'warning';
    } else if (['CRITICAL', 'ERROR', 'FAILED', 'STALE', 'DOWN', 'UNHEALTHY'].includes(normalized)) {
      inferredType = 'critical';
    } else if (['INFO', 'RUNNING', 'IDLE', 'STANDBY'].includes(normalized)) {
      inferredType = 'info';
    }
  }

  const displayText = label || status || 'UNKNOWN';

  return (
    <span className={`status-badge ${inferredType} ${className}`}>
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          backgroundColor: 'currentColor',
          display: 'inline-block',
        }}
      />
      {displayText}
    </span>
  );
};
