import React from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { AnomalyAuditItem } from '../../types';

interface AnomalyScatterChartProps {
  data: AnomalyAuditItem[];
  height?: number;
}

export const AnomalyScatterChart: React.FC<AnomalyScatterChartProps> = ({
  data,
  height = 260,
}) => {
  const formattedData = React.useMemo(() => {
    return data.map((item) => {
      const dt = new Date(item.timestamp);
      const timeStr = !isNaN(dt.getTime())
        ? dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : item.timestamp;

      return {
        timestamp: timeStr,
        anomaly_score: Number(item.anomaly_score.toFixed(3)),
        health_score: item.health_score !== null ? Number(item.health_score.toFixed(1)) : null,
        is_anomaly: item.is_anomaly,
        risk_category: item.risk_category,
      };
    });
  }, [data]);

  if (formattedData.length === 0) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: 13,
        }}
      >
        No anomaly audit data available
      </div>
    );
  }

  return (
    <div className="chart-container" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formattedData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="timestamp"
            stroke="#64748B"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#1E293B' }}
          />
          <YAxis
            domain={[0, 1.0]}
            stroke="#64748B"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#1E293B' }}
            tickFormatter={(val) => val.toFixed(1)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#151D2C',
              borderColor: '#293548',
              borderRadius: 6,
              color: '#F8FAFC',
              fontSize: 12,
            }}
            labelStyle={{ color: '#94A3B8', fontWeight: 600, marginBottom: 4 }}
            formatter={(value: unknown, name?: unknown) => {
              const num = typeof value === 'number' ? value : Number(value);
              const nameStr = String(name || '');
              if (nameStr.includes('Anomaly')) {
                return [`${num.toFixed(3)}`];
              }
              return [`${num}`];
            }}
          />
          <ReferenceLine
            y={0.5}
            stroke="#EF4444"
            strokeDasharray="4 4"
            label={{
              value: 'Anomaly Threshold (0.50)',
              fill: '#EF4444',
              fontSize: 11,
              position: 'insideTopRight',
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} iconType="circle" />
          <Line
            type="monotone"
            dataKey="anomaly_score"
            name="Isolation Forest Anomaly Score"
            stroke="#38BDF8"
            strokeWidth={2}
            dot={(props: unknown) => {
              const dotProps = props as { cx: number; cy: number; payload: { is_anomaly: boolean } };
              const isAnomaly = dotProps.payload?.is_anomaly;
              return (
                <circle
                  key={`${dotProps.cx}-${dotProps.cy}`}
                  cx={dotProps.cx}
                  cy={dotProps.cy}
                  r={isAnomaly ? 5 : 2}
                  fill={isAnomaly ? '#EF4444' : '#38BDF8'}
                  stroke={isAnomaly ? '#7F1D1D' : 'none'}
                  strokeWidth={isAnomaly ? 2 : 0}
                />
              );
            }}
            activeDot={{ r: 6 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
