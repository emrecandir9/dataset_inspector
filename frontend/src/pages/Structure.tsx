import React from 'react';
import BarChartComponent from '../charts/BarChart';

interface StructureProps {
  report: any;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export default function Structure({ report }: StructureProps) {
  const scan = report.scan_result;
  if (!scan) return <div className="page-header"><h1 className="page-title">Structure</h1></div>;

  const extData = (scan.extensions || []).slice(0, 15).map((e: any) => ({
    name: e.extension,
    value: e.count,
  }));

  const extSizeData = (scan.extensions || []).slice(0, 15).map((e: any) => ({
    name: e.extension,
    value: Math.round(e.total_size_bytes / (1024 * 1024) * 100) / 100,
  }));

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Structure</h1>
        <p className="page-subtitle">{scan.root_path}</p>
      </div>

      <div className="stats-grid">
        <div className="card">
          <div className="card-title">Total Files</div>
          <div className="card-value">{scan.total_files?.toLocaleString()}</div>
        </div>
        <div className="card">
          <div className="card-title">Directories</div>
          <div className="card-value">{scan.total_directories?.toLocaleString()}</div>
        </div>
        <div className="card">
          <div className="card-title">Total Size</div>
          <div className="card-value">{formatBytes(scan.total_size_bytes)}</div>
        </div>
        <div className="card">
          <div className="card-title">Extensions</div>
          <div className="card-value">{scan.extensions?.length || 0}</div>
        </div>
      </div>

      {extData.length > 0 && (
        <BarChartComponent
          title="Files by Extension"
          data={extData}
          color="#48484A"
        />
      )}

      {extSizeData.length > 0 && (
        <BarChartComponent
          title="Size by Extension (MB)"
          data={extSizeData}
          color="#38383A"
        />
      )}

      {/* Extension table */}
      {scan.extensions?.length > 0 && (
        <div className="section">
          <h2 className="section-title">Extension Breakdown</h2>
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Extension</th>
                  <th>Count</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {scan.extensions.map((e: any, i: number) => (
                  <tr key={i}>
                    <td>{e.extension}</td>
                    <td className="numeric">{e.count.toLocaleString()}</td>
                    <td className="numeric">{formatBytes(e.total_size_bytes)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {scan.empty_directories?.length > 0 && (
        <div className="section">
          <h2 className="section-title">Empty Directories</h2>
          <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-tertiary)' }}>
            {scan.empty_directories.map((d: string, i: number) => (
              <div key={i} style={{ padding: 'var(--space-1) 0' }}>{d}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
