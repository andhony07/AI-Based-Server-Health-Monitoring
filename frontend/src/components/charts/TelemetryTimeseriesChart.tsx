import React from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SystemMetricRecord } from '../../types';

interface TelemetryTimeseriesChartProps {
  data: SystemMetricRecord[];
  height?: number;
  showDisk?: boolean;
}

export const TelemetryTimeseriesChart: React.FC<TelemetryTimeseriesChartProps> = ({
  data,
  height = 250,
  showDisk = true,
}) => {
  // Sort chronologically and format data for chart
  const formattedData = React.useMemo(() => {
    const sorted = [...data].sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    return sorted.map((record) => {
      const dt = new Date(record.timestamp);
      const timeStr = !isNaN(dt.getTime())
        ? dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : record.timestamp;
      return {
        timestamp: timeStr,
        rawTimestamp: record.timestamp,
        cpu: record.cpu_percent !== null ? Number(record.cpu_percent.toFixed(1)) : 0,
        memory: record.memory_percent !== null ? Number(record.memory_percent.toFixed(1)) : 0,
        disk: record.disk_percent !== null ? Number(record.disk_percent.toFixed(1)) : 0,
        diskActive: record.disk_active_percent !== null && record.disk_active_percent !== undefined
          ? Number(record.disk_active_percent.toFixed(1))
          : null,
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
          fontSize: 12.5,
        }}
      >
        No historical telemetry points available
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formattedData} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
          <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="timestamp"
            stroke="#64748B"
            fontSize={10.5}
            tickLine={false}
            axisLine={{ stroke: '#293548' }}
          />
          <YAxis
            domain={[0, 100]}
            stroke="#64748B"
            fontSize={10.5}
            tickLine={false}
            axisLine={{ stroke: '#293548' }}
            tickFormatter={(val) => `${val}%`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#151D2C',
              borderColor: '#293548',
              borderRadius: 6,
              color: '#F8FAFC',
              fontSize: 11.5,
              boxShadow: '0 8px 16px rgba(0, 0, 0, 0.4)',
              padding: '8px 12px',
            }}
            labelStyle={{ color: '#94A3B8', fontWeight: 600, marginBottom: 4 }}
            formatter={(value: unknown) => {
              const num = typeof value === 'number' ? value : Number(value);
              return [`${num.toFixed(1)}%`];
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11.5, paddingTop: 8 }}
            iconType="circle"
          />
          <Line
            type="monotone"
            dataKey="cpu"
            name="CPU Utilization"
            stroke="#38BDF8"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, stroke: '#38BDF8', strokeWidth: 2, fill: '#0B0F19' }}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="memory"
            name="Memory Usage"
            stroke="#A855F7"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, stroke: '#A855F7', strokeWidth: 2, fill: '#0B0F19' }}
            isAnimationActive={false}
          />
          {showDisk && (
            <>
              <Line
                type="monotone"
                dataKey="disk"
                name="Disk Storage"
                stroke="#10B981"
                strokeWidth={2}
                dot={false}
                strokeDasharray="4 4"
                activeDot={{ r: 4, stroke: '#10B981', strokeWidth: 2, fill: '#0B0F19' }}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="diskActive"
                name="Disk Active Time"
                stroke="#F59E0B"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, stroke: '#F59E0B', strokeWidth: 2, fill: '#0B0F19' }}
                isAnimationActive={false}
                connectNulls={true}
              />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
