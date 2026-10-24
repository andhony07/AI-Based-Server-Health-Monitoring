import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface ResourceBarItem {
  resource: string;
  current: number;
  threshold?: number;
  baseline?: number;
}

interface ResourceBarChartProps {
  data: ResourceBarItem[];
  height?: number;
  compareMode?: boolean;
}

export const ResourceBarChart: React.FC<ResourceBarChartProps> = ({
  data,
  height = 240,
  compareMode = false,
}) => {
  return (
    <div className="chart-container" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid stroke="#1E293B" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="resource"
            stroke="#64748B"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#1E293B' }}
          />
          <YAxis
            domain={[0, 100]}
            stroke="#64748B"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: '#1E293B' }}
            tickFormatter={(val) => `${val}%`}
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
              return [`${num.toFixed(1)}%`];
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} iconType="circle" />
          {compareMode && (
            <Bar
              dataKey="baseline"
              name="Baseline / Nominal"
              fill="#475569"
              radius={[4, 4, 0, 0]}
              isAnimationActive={false}
            />
          )}
          <Bar
            dataKey="current"
            name={compareMode ? 'Simulated Value' : 'Utilization %'}
            fill="#38BDF8"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
