import React, { useState } from 'react';
import ImageGrid from '../components/ImageGrid';
import DataTable from '../components/DataTable';

interface ExamplesProps {
  report: any;
}

export default function Examples({ report }: ExamplesProps) {
  const examples = report.examples || [];
  const [filter, setFilter] = useState('all');
  const schema = report.schema;

  // Determine available classes
  const classes = schema?.classes ? Object.keys(schema.classes) : [];

  // Filter examples
  let filtered = examples;
  if (filter !== 'all' && filter !== 'random') {
    filtered = examples.filter((e: any) => e.label === filter);
  }

  const isImage = examples.some((e: any) => e.type === 'image');
  const isTabular = examples.some((e: any) => e.type === 'tabular');

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Examples</h1>
        <p className="page-subtitle">{examples.length} samples</p>
      </div>

      {/* Filter tabs */}
      {classes.length > 0 && (
        <div className="tabs">
          <button
            className={`tab ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            All
          </button>
          {classes.slice(0, 12).map(cls => (
            <button
              key={cls}
              className={`tab ${filter === cls ? 'active' : ''}`}
              onClick={() => setFilter(cls)}
            >
              {cls}
            </button>
          ))}
        </div>
      )}

      {/* Image examples */}
      {isImage && <ImageGrid examples={filtered} />}

      {/* Tabular examples */}
      {isTabular && filtered.length > 0 && (
        <DataTable
          columns={
            Object.keys(filtered[0]?.data || {}).map(key => ({
              key,
              label: key,
            }))
          }
          data={filtered.map((e: any) => e.data)}
          maxRows={50}
        />
      )}

      {filtered.length === 0 && (
        <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
          No examples available{filter !== 'all' ? ` for class "${filter}"` : ''}.
        </div>
      )}
    </div>
  );
}
