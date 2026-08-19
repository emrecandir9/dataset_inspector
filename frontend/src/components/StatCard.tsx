import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  detail?: string;
}

export default function StatCard({ title, value, detail }: StatCardProps) {
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      <div className="card-value">{value}</div>
      {detail && <div className="card-detail">{detail}</div>}
    </div>
  );
}
