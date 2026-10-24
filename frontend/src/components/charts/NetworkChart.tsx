import React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { SystemMetricRecord } from '../../types';

interface NetworkChartProps {
  data: SystemMetricRecord[];
  height?: number;
}

export const NetworkChart: React.FC<NetworkChartProps> = ({
  data,
  height = 240,
}) => {
  const formattedData = React.useMemo(() => {
    return data.map((record) => {
      const dt = new Date(record.timestamp);
      const timeStr = !isNaN(dt.getTime())
        ? dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : record.timestamp;

      // Use per-second rate if present, otherwise extract from raw payload or KB/s estimation
      const rawPayload = record.raw_payload as Record<string, unknown> | undefined;
      const netObj = rawPayload?.network as Record<string, unknown> | undefined;

      const upload = typeof netObj?.upload_kbps === 'number'
        ? netObj.upload_kbps
        : (record.network_bytes_sent_per_sec !== null ? record.network_bytes_sent_per_sec / 1024 : 0);

      const download = typeof netObj?.download_kbps === 'number'
        ? netObj.download_kbps
        : (record.network_bytes_recv_per_sec !== null ? record.network_bytes_recv_per_sec / 1024 : 0);

      return {
        timestamp: timeStr,
        upload: Number(upload.toFixed(1)),
        download: Number(download.toFixed(1)),
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
        No network telemetry data available
      </div>
    );
  }

  return (
    <div className="chart-container" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={formattedData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="netUploadGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#38BDF8" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="netDownloadGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="timestamp"
            stroke="#64748B"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#1E293B' }}
          />
          <YAxis
            stroke="#64748B"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#1E293B' }}
            tickFormatter={(val) => `${val} KB/s`}
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
            formatter={(value: unknown) => {
              const num = typeof value === 'number' ? value : Number(value);
              return [`${num} KB/s`];
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} iconType="circle" />
          <Area
            type="monotone"
            dataKey="upload"
            name="Upload (KB/s)"
            stroke="#38BDF8"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#netUploadGrad)"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="download"
            name="Download (KB/s)"
            stroke="#10B981"
            strokeWidth={2}
            fillOpacity={1}
            fill="url(#netDownloadGrad)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
