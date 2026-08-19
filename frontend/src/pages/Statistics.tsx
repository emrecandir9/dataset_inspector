import React from 'react';
import DataTable from '../components/DataTable';
import BarChartComponent from '../charts/BarChart';
import Histogram from '../charts/Histogram';

interface StatisticsProps {
  report: any;
  getAnalyzerResult: (id: string) => any;
}

export default function Statistics({ report, getAnalyzerResult }: StatisticsProps) {
  const columnStats = getAnalyzerResult('column_stats');
  const correlation = getAnalyzerResult('correlation');

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Statistics</h1>
        <p className="page-subtitle">Per-column statistical summary</p>
      </div>

      {/* Column stats table */}
      {columnStats?.metrics?.columns && (
        <div className="section">
          <h2 className="section-title">Column Summary</h2>
          <DataTable
            columns={[
              { key: 'column', label: 'Column' },
              { key: 'dtype', label: 'Type' },
              { key: 'missing', label: 'Missing', numeric: true, format: (v: number) => v?.toLocaleString() ?? '—' },
              { key: 'missing_pct', label: 'Missing %', numeric: true, format: (v: number) => v != null ? `${v}%` : '—' },
              { key: 'unique', label: 'Unique', numeric: true, format: (v: number) => v?.toLocaleString() ?? '—' },
              { key: 'mean', label: 'Mean', numeric: true, format: (v: number) => v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—' },
              { key: 'median', label: 'Median', numeric: true, format: (v: number) => v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—' },
              { key: 'std', label: 'Std', numeric: true, format: (v: number) => v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—' },
              { key: 'min', label: 'Min', numeric: true, format: (v: number) => v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—' },
              { key: 'max', label: 'Max', numeric: true, format: (v: number) => v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : '—' },
            ]}
            data={columnStats.metrics.columns}
          />
        </div>
      )}

      {/* Distribution charts */}
      {columnStats?.charts?.map((chart: any, i: number) => (
        <div key={i}>
          {chart.type === 'histogram' ? (
            <Histogram title={chart.title} data={chart.data} />
          ) : chart.type === 'bar' ? (
            <BarChartComponent title={chart.title} data={chart.data} />
          ) : null}
        </div>
      ))}

      {/* Top values for categorical columns */}
      {columnStats?.metrics?.columns?.filter((c: any) => c.top_values?.length > 0).map((col: any) => (
        <div key={col.column} className="section">
          <h2 className="section-title">{col.column}</h2>
          <div className="section-subtitle">
            {col.dtype} · {col.unique?.toLocaleString()} unique values
          </div>
          <BarChartComponent
            title={`Top values: ${col.column}`}
            data={col.top_values.map((v: any) => ({ name: String(v.value), value: v.count }))}
            color="#48484A"
          />
        </div>
      ))}

      {/* Correlations */}
      {correlation?.metrics?.high_correlations?.length > 0 && (
        <div className="section">
          <h2 className="section-title">High Correlations</h2>
          <DataTable
            columns={[
              { key: 'col_a', label: 'Feature A' },
              { key: 'col_b', label: 'Feature B' },
              { key: 'correlation', label: 'Correlation', numeric: true },
            ]}
            data={correlation.metrics.high_correlations}
          />
        </div>
      )}
    </div>
  );
}
