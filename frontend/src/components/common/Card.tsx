import React from 'react';

interface CardProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  noPadding?: boolean;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  action,
  children,
  className = '',
  style,
  noPadding = false,
}) => {
  return (
    <div className={`op-card ${className}`} style={style}>
      {(title || action || subtitle) && (
        <div className="op-card-header">
          <div>
            {title && <div className="op-card-title">{title}</div>}
            {subtitle && <div className="op-card-subtitle">{subtitle}</div>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={noPadding ? '' : 'op-card-body'}>
        {children}
      </div>
    </div>
  );
};
