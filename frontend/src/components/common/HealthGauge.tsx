import React from 'react';

interface HealthGaugeProps {
  score: number | null | undefined;
  size?: number;
  label?: string;
  riskCategory?: string;
}

export const HealthGauge: React.FC<HealthGaugeProps> = ({
  score,
  size = 140,
  label = 'Overall Health',
  riskCategory,
}) => {
  const validScore = score !== null && score !== undefined && !isNaN(score)
    ? Math.min(100, Math.max(0, Math.round(score)))
    : null;

  // Arc geometry (240 degree gauge arc from 150deg to 390deg)
  const strokeWidth = 10;
  const radius = (size - strokeWidth * 2) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * (240 / 360);
  const strokeDashoffset = validScore !== null
    ? arcLength - (arcLength * validScore) / 100
    : arcLength;

  // Colors
  let scoreColor = '#64748B'; // Muted
  if (validScore !== null) {
    if (validScore >= 80) scoreColor = '#10B981'; // Green
    else if (validScore >= 60) scoreColor = '#F59E0B'; // Amber
    else scoreColor = '#EF4444'; // Red
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ position: 'relative', width: size, height: size * 0.82 }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{ transform: 'rotate(150deg)', overflow: 'visible' }}
        >
          {/* Track Arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="transparent"
            stroke="#1E293B"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
          />
          {/* Progress Arc */}
          {validScore !== null && (
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="transparent"
              stroke={scoreColor}
              strokeWidth={strokeWidth}
              strokeDasharray={`${arcLength} ${circumference}`}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              style={{ transition: 'stroke-dashoffset 0.5s cubic-bezier(0.4, 0, 0.2, 1)' }}
            />
          )}
        </svg>

        {/* Value in Center */}
        <div
          style={{
            position: 'absolute',
            top: '42%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <div
            style={{
              fontSize: Math.round(size * 0.24),
              fontWeight: 800,
              color: scoreColor,
              lineHeight: 1,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {validScore !== null ? validScore : '--'}
          </div>
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: 0.5,
              marginTop: 3,
            }}
          >
            / 100
          </div>
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: -6 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
          {label}
        </div>
        {riskCategory && (
          <div
            style={{
              fontSize: 11.5,
              fontWeight: 700,
              color: scoreColor,
              marginTop: 2,
            }}
          >
            {riskCategory} Tier
          </div>
        )}
      </div>
    </div>
  );
};
