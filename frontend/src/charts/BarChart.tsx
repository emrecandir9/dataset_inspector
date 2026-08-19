import React from 'react';
import {
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

interface BarChartProps {
  title: string;
  data: Array<{ name: string; value: number; [k: string]: any }>;
  xKey?: string;
  yKey?: string;
  yLabel?: string;
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

export default function BarChartComponent({
  title,
  data,
  xKey = 'name',
  yKey = 'value',
  color = '#2997FF',
  height = 280,
}: BarChartProps) {
  return (
    <div className="chart-container">
      <div className="chart-title">{title}</div>
      <ResponsiveContainer width="100%" height={height}>
        <ReBarChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1C1C1E" />
          <XAxis
            dataKey={xKey}
            tick={{ fill: '#6E6E73', fontSize: 11 }}
            axisLine={{ stroke: '#2C2C2E' }}
            tickLine={false}
            interval={0}
            angle={data.length > 8 ? -45 : 0}
            textAnchor={data.length > 8 ? 'end' : 'middle'}
            height={data.length > 8 ? 80 : 30}
          />
          <YAxis
            tick={{ fill: '#6E6E73', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <Bar dataKey={yKey} fill={color} radius={[3, 3, 0, 0]} maxBarSize={40} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  );
}
