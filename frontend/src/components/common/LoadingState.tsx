import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  height?: number | string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading telemetry from server...',
  height = 200,
}) => {
  return (
    <div
      className="state-box"
      style={{
        height,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Loader2
        size={28}
        style={{
          color: 'var(--accent-primary)',
          animation: 'spin 1s linear infinite',
        }}
      />
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
      <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 10 }}>
        {message}
      </div>
    </div>
  );
};
