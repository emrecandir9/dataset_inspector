import React from 'react';
import WarningsList from '../components/WarningsList';
import BarChartComponent from '../charts/BarChart';

interface QualityProps {
  report: any;
  findings: any[];
  getAnalyzerResult: (id: string) => any;
}

export default function Quality({ report, findings, getAnalyzerResult }: QualityProps) {
  const missing = getAnalyzerResult('missing_values');
  const outliers = getAnalyzerResult('outliers');
  const corrupted = getAnalyzerResult('corrupted_images');

  // Filter quality-related findings
  const qualityFindings = findings.filter((f: any) =>
    ['missing_values', 'outliers', 'corrupted_images', 'image_quality'].some(id =>
      f.code?.includes(id.replace('_', '')) || f.code?.includes('missing') || f.code?.includes('outlier') ||
      f.code?.includes('corrupt') || f.code?.includes('dark') || f.code?.includes('bright') ||
      f.code?.includes('blur') || f.code?.includes('empty') || f.code?.includes('truncat')
    )
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Quality</h1>
        <p className="page-subtitle">Data quality analysis and issues</p>
      </div>

      {/* Quality stats */}
      <div className="stats-grid">
        {missing?.metrics && (
          <>
            <div className="card">
              <div className="card-title">Missing Cells</div>
              <div className="card-value">{missing.metrics.total_missing_cells?.toLocaleString()}</div>
              <div className="card-detail">{missing.metrics.overall_missing_pct}% of all cells</div>
            </div>
            <div className="card">
              <div className="card-title">Columns with Missing</div>
              <div className="card-value">{missing.metrics.columns_with_missing}</div>
            </div>
          </>
        )}
        {outliers?.metrics && (
          <>
            <div className="card">
              <div className="card-title">Total Outliers</div>
              <div className="card-value">{outliers.metrics.total_outliers?.toLocaleString()}</div>
            </div>
            <div className="card">
              <div className="card-title">Columns with Outliers</div>
              <div className="card-value">{outliers.metrics.columns_with_outliers}</div>
            </div>
          </>
        )}
        {corrupted?.metrics && (
          <>
            <div className="card">
              <div className="card-title">Corrupted Files</div>
              <div className="card-value">{corrupted.metrics.corrupted}</div>
            </div>
            <div className="card">
              <div className="card-title">Truncated Files</div>
              <div className="card-value">{corrupted.metrics.truncated}</div>
            </div>
            <div className="card">
              <div className="card-title">Healthy</div>
              <div className="card-value">{corrupted.metrics.healthy_pct}%</div>
            </div>
          </>
        )}
      </div>

      {/* Charts */}
      {missing?.charts?.map((chart: any, i: number) => (
        <BarChartComponent key={i} title={chart.title} data={chart.data} color="var(--color-warning)" />
      ))}

      {outliers?.charts?.map((chart: any, i: number) => (
        <BarChartComponent key={i} title={chart.title} data={chart.data} color="var(--color-error)" />
      ))}

      {/* Findings */}
      {qualityFindings.length > 0 && (
        <div className="section">
          <h2 className="section-title">Quality Issues</h2>
          <WarningsList findings={qualityFindings} />
        </div>
      )}

      {qualityFindings.length === 0 && findings.length === 0 && (
        <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
          No quality issues detected.
        </div>
      )}
    </div>
  );
}
