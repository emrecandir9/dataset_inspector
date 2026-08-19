import React from 'react';

interface Finding {
  severity: string;
  code: string;
  title: string;
  message: string;
}

interface WarningsListProps {
  findings: Finding[];
  limit?: number;
}

const ICONS: Record<string, string> = {
  error: '✕',
  warning: '!',
  info: '·',
};

export default function WarningsList({ findings, limit }: WarningsListProps) {
  const sorted = [...findings].sort((a, b) => {
    const order = { error: 0, warning: 1, info: 2 };
    return (order[a.severity as keyof typeof order] ?? 3) - (order[b.severity as keyof typeof order] ?? 3);
  });

  const shown = limit ? sorted.slice(0, limit) : sorted;

  if (shown.length === 0) {
    return (
      <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
        No issues found.
      </div>
    );
  }

  return (
    <div className="findings-list">
      {shown.map((f, i) => (
        <div key={i} className={`finding-item ${f.severity}`}>
          <span className="finding-icon">{ICONS[f.severity] || '·'}</span>
          <div className="finding-content">
            <div className="finding-title">{f.title}</div>
            <div className="finding-message">{f.message}</div>
          </div>
        </div>
      ))}
      {limit && sorted.length > limit && (
        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--text-tertiary)', paddingTop: 'var(--space-2)' }}>
          + {sorted.length - limit} more
        </div>
      )}
    </div>
  );
}
