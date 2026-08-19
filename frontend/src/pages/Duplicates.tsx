import React from 'react';
import StatCard from '../components/StatCard';
import WarningsList from '../components/WarningsList';

interface DuplicatesProps {
  report: any;
  getAnalyzerResult: (id: string) => any;
  findings: any[];
}

export default function Duplicates({ report, getAnalyzerResult, findings }: DuplicatesProps) {
  const tabDuplicates = getAnalyzerResult('duplicates');
  const imgDuplicates = getAnalyzerResult('image_duplicates');

  const dupFindings = findings.filter((f: any) =>
    f.code?.includes('duplicate') || f.code?.includes('constant') || f.code?.includes('potential_id') || f.code?.includes('leakage')
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Duplicates</h1>
        <p className="page-subtitle">Duplicate and uniqueness analysis</p>
      </div>

      <div className="stats-grid">
        {tabDuplicates?.metrics && (
          <>
            <StatCard
              title="Duplicate Rows"
              value={tabDuplicates.metrics.duplicate_rows?.toLocaleString()}
              detail={`${tabDuplicates.metrics.duplicate_pct}% of ${tabDuplicates.metrics.total_rows?.toLocaleString()} rows`}
            />
            <StatCard title="Unique Rows" value={tabDuplicates.metrics.unique_rows?.toLocaleString()} />
            {tabDuplicates.metrics.constant_columns?.length > 0 && (
              <StatCard
                title="Constant Columns"
                value={tabDuplicates.metrics.constant_columns.length}
                detail={tabDuplicates.metrics.constant_columns.join(', ')}
              />
            )}
            {tabDuplicates.metrics.potential_id_columns?.length > 0 && (
              <StatCard
                title="Potential IDs"
                value={tabDuplicates.metrics.potential_id_columns.length}
                detail={tabDuplicates.metrics.potential_id_columns.join(', ')}
              />
            )}
          </>
        )}
        {imgDuplicates?.metrics && (
          <>
            <StatCard title="Exact Duplicates" value={imgDuplicates.metrics.exact_duplicate_count} detail={`${imgDuplicates.metrics.exact_duplicate_groups} groups`} />
            <StatCard title="Near Duplicates" value={imgDuplicates.metrics.near_duplicate_pairs} detail="Perceptual hash pairs" />
            <StatCard title="Images Analyzed" value={imgDuplicates.metrics.analyzed?.toLocaleString()} />
          </>
        )}
      </div>

      {dupFindings.length > 0 && (
        <div className="section">
          <h2 className="section-title">Issues</h2>
          <WarningsList findings={dupFindings} />
        </div>
      )}

      {!tabDuplicates && !imgDuplicates && (
        <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
          No duplicate analysis available.
        </div>
      )}
    </div>
  );
}
