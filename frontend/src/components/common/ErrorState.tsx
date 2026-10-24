import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message: string;
  detail?: string;
  onRetry?: () => void;
  height?: number | string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Data Retrieval Error',
  message,
  detail,
  onRetry,
  height = 200,
}) => {
  return (
    <div
      className="state-box"
      style={{
        height,
        backgroundColor: 'rgba(239, 68, 68, 0.04)',
        border: '1px solid var(--status-critical-border)',
        borderRadius: 'var(--radius-lg)',
      }}
    >
      <AlertTriangle size={32} style={{ color: 'var(--status-critical)' }} />
      <div className="state-box-title" style={{ color: '#FCA5A5' }}>
        {title}
      </div>
      <div className="state-box-desc" style={{ color: 'var(--text-secondary)' }}>
        {message}
      </div>
      {detail && (
        <code
          style={{
            fontSize: 11,
            backgroundColor: 'rgba(0, 0, 0, 0.4)',
            padding: '4px 10px',
            borderRadius: 4,
            color: '#F87171',
            maxWidth: '90%',
            overflowX: 'auto',
          }}
        >
          {detail}
        </code>
      )}
      {onRetry && (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onRetry}
          style={{ marginTop: 8 }}
        >
          <RefreshCw size={14} /> Retry Request
        </button>
      )}
    </div>
  );
};
