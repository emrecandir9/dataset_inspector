import React from 'react';
import BarChartComponent from '../charts/BarChart';
import StatCard from '../components/StatCard';

interface ClassesProps {
  report: any;
  getAnalyzerResult: (id: string) => any;
}

export default function Classes({ report, getAnalyzerResult }: ClassesProps) {
  const classBalance = getAnalyzerResult('class_balance');
  const schema = report.schema;

  if (!schema?.classes && !classBalance) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Classes</h1>
        </div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
          No class labels detected in this dataset.
        </div>
      </div>
    );
  }

  const metrics = classBalance?.metrics;
  const distribution = metrics?.distribution || [];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Classes</h1>
        <p className="page-subtitle">Class distribution analysis</p>
      </div>

      <div className="stats-grid">
        {metrics && (
          <>
            <StatCard title="Classes" value={metrics.num_classes} />
            <StatCard title="Total Samples" value={metrics.total_samples?.toLocaleString()} />
            <StatCard
              title="Imbalance Ratio"
              value={`${metrics.imbalance_ratio}:1`}
              detail={metrics.imbalance_ratio > 3 ? 'Significant imbalance' : 'Balanced'}
            />
            <StatCard
              title="Largest"
              value={metrics.largest_class?.name}
              detail={`${metrics.largest_class?.count?.toLocaleString()} samples`}
            />
            <StatCard
              title="Smallest"
              value={metrics.smallest_class?.name}
              detail={`${metrics.smallest_class?.count?.toLocaleString()} samples`}
            />
          </>
        )}
      </div>

      {/* Distribution chart */}
      {distribution.length > 0 && (
        <BarChartComponent
          title="Class Distribution"
          data={distribution.map((d: any) => ({ name: d.name, value: d.count }))}
          color="#48484A"
          height={Math.max(280, distribution.length * 20)}
        />
      )}

      {/* Distribution table */}
      {distribution.length > 0 && (
        <div className="section">
          <h2 className="section-title">All Classes</h2>
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Class</th>
                  <th>Count</th>
                  <th>Percentage</th>
                </tr>
              </thead>
              <tbody>
                {distribution.map((d: any, i: number) => (
                  <tr key={i}>
                    <td>{d.name}</td>
                    <td className="numeric">{d.count?.toLocaleString()}</td>
                    <td className="numeric">{d.pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
