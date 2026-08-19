import React from 'react';

interface Column {
  key: string;
  label: string;
  numeric?: boolean;
  format?: (value: any) => string;
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  maxRows?: number;
}

export default function DataTable({ columns, data, maxRows }: DataTableProps) {
  const rows = maxRows ? data.slice(0, maxRows) : data;

  return (
    <div className="data-table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map(col => {
                const val = row[col.key];
                const displayed = col.format ? col.format(val) : val;
                return (
                  <td key={col.key} className={col.numeric ? 'numeric' : ''}>
                    {displayed ?? '—'}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {maxRows && data.length > maxRows && (
        <div style={{
          fontSize: 'var(--font-size-sm)',
          color: 'var(--text-tertiary)',
          padding: 'var(--space-3) var(--space-4)',
        }}>
          Showing {maxRows} of {data.length} rows
        </div>
      )}
    </div>
  );
}
