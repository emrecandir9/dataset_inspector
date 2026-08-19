import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

interface HistogramProps {
  title: string;
  data: Array<{ bin: string; count: number }>;
  color?: string;
  height?: number;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#1C1C1E',
      border: '1px solid #2C2C2E',
      borderRadius: '8px',
      padding: '8px 12px',
      fontSize: '13px',
    }}>
      <div style={{ color: '#86868B', marginBottom: '4px' }}>{label}</div>
      <div style={{ color: '#F5F5F7', fontWeight: 500 }}>
        {payload[0].value?.toLocaleString()}
      </div>
    </div>
  );
};

export default function Histogram({
  title,
  data,
  color = '#48484A',
  height = 220,
}: HistogramProps) {
  return (
    <div className="chart-container">
      <div className="chart-title">{title}</div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1C1C1E" />
          <XAxis
            dataKey="bin"
            tick={{ fill: '#6E6E73', fontSize: 10 }}
            axisLine={{ stroke: '#2C2C2E' }}
            tickLine={false}
            interval={Math.max(0, Math.floor(data.length / 8))}
          />
          <YAxis
            tick={{ fill: '#6E6E73', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey="count" fill={color} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
