import React from 'react';
import HealthScoreComponent from '../components/HealthScore';
import StatCard from '../components/StatCard';
import WarningsList from '../components/WarningsList';
import { getExportUrl } from '../api/client';

interface OverviewProps {
  report: any;
  findings: any[];
  onNavigate: (page: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

function formatNumber(n: number): string {
  return n.toLocaleString();
}

export default function Overview({ report, findings, onNavigate }: OverviewProps) {
  const schema = report.schema;
  const scan = report.scan_result;
  const health = report.health;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Overview</h1>
          {schema && (
            <p className="page-subtitle">
              {schema.source_format.toUpperCase()} · {schema.modality}
              {schema.analysis_mode === 'sample' && schema.sample_size &&
                ` · Sampled ${formatNumber(schema.sample_size)} of ${formatNumber(schema.num_samples)}`
              }
            </p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <a
            href={getExportUrl('json')}
            target="_blank"
            rel="noreferrer"
            className="badge accent"
            style={{ textDecoration: 'none', cursor: 'pointer' }}
          >
            JSON
          </a>
          <a
            href={getExportUrl('html')}
            target="_blank"
            rel="noreferrer"
            className="badge accent"
            style={{ textDecoration: 'none', cursor: 'pointer' }}
          >
            HTML
          </a>
          <a
            href={getExportUrl('markdown')}
            target="_blank"
            rel="noreferrer"
            className="badge accent"
            style={{ textDecoration: 'none', cursor: 'pointer' }}
          >
            MD
          </a>
        </div>
      </div>

      {/* Health */}
      {health && <HealthScoreComponent health={health} />}

      {/* Stats */}
      <div className="stats-grid">
        {schema && (
          <>
            <StatCard title="Samples" value={formatNumber(schema.num_samples)} />
            <StatCard title="Size" value={formatBytes(schema.total_size_bytes)} />
            <StatCard title="Modality" value={schema.modality} />
            {schema.fields?.length > 0 && (
              <StatCard title="Fields" value={schema.fields.length} />
            )}
            {schema.classes && (
              <StatCard title="Classes" value={Object.keys(schema.classes).length} />
            )}
            {schema.splits && Object.keys(schema.splits).length > 0 && (
              <StatCard
                title="Splits"
                value={Object.keys(schema.splits).length}
                detail={Object.entries(schema.splits).map(([k, v]: any) => `${k}: ${formatNumber(v)}`).join(' · ')}
              />
            )}
          </>
        )}
        {scan && (
          <>
            <StatCard title="Files" value={formatNumber(scan.total_files)} />
            <StatCard
              title="Extensions"
              value={scan.extensions?.length || 0}
              detail={scan.extensions?.slice(0, 3).map((e: any) => `${e.extension} (${e.count})`).join(', ')}
            />
          </>
        )}
      </div>

      {/* Detection */}
      {report.detection?.hypotheses?.length > 0 && (
        <div className="section">
          <h2 className="section-title">Format Detection</h2>
          <div className="detection-list">
            {report.detection.hypotheses.slice(0, 4).map((h: any, i: number) => (
              <div
                key={i}
                className={`detection-item ${h === report.detection.selected ? 'selected' : ''}`}
              >
                <span className="detection-type">{h.dataset_type}</span>
                <span className="badge accent">{h.modality}</span>
                <span className="detection-confidence">{(h.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Findings */}
      {findings.length > 0 && (
        <div className="section">
          <h2 className="section-title">Findings</h2>
          <WarningsList findings={findings} limit={8} />
        </div>
      )}

      {/* Duration */}
      <div style={{
        marginTop: 'var(--space-10)',
        fontSize: 'var(--font-size-xs)',
        color: 'var(--text-quaternary)',
      }}>
        Analysis completed in {report.analysis_duration_seconds?.toFixed(1)}s · Dataset Inspector v{report.version}
      </div>
    </div>
  );
}
