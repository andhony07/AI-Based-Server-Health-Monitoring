import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
  action?: React.ReactNode;
  height?: number | string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Records Found',
  message = 'There is currently no telemetry or audit data matching the query criteria.',
  action,
  height = 200,
}) => {
  return (
    <div className="state-box" style={{ height }}>
      <Inbox size={32} style={{ color: 'var(--text-muted)' }} />
      <div className="state-box-title">{title}</div>
      <div className="state-box-desc">{message}</div>
      {action && <div style={{ marginTop: 8 }}>{action}</div>}
    </div>
  );
};
