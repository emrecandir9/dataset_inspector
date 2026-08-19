import React, { useState } from 'react';

interface LandingProps {
  onAnalyze: (path: string) => void;
  error: string | null;
}

export default function Landing({ onAnalyze, error }: LandingProps) {
  const [path, setPath] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (path.trim()) {
      onAnalyze(path.trim());
    }
  };

  return (
    <div className="landing">
      <h1 className="landing-title">Dataset Inspector</h1>
      <p className="landing-subtitle">
        Analyze any dataset instantly. Drop a path to get started.
      </p>
      <form onSubmit={handleSubmit} className="landing-input-group">
        <input
          id="dataset-path-input"
          className="landing-input"
          type="text"
          value={path}
          onChange={e => setPath(e.target.value)}
          placeholder="/path/to/your/dataset"
          autoFocus
        />
        <button
          id="analyze-button"
          className="landing-button"
          type="submit"
          disabled={!path.trim()}
        >
          Analyze
        </button>
      </form>
      {error && (
        <div style={{
          marginTop: 'var(--space-5)',
          color: 'var(--color-error)',
          fontSize: 'var(--font-size-sm)',
          maxWidth: '560px',
        }}>
          {error}
        </div>
      )}
      <div style={{
        marginTop: 'var(--space-12)',
        display: 'flex',
        gap: 'var(--space-8)',
        color: 'var(--text-quaternary)',
        fontSize: 'var(--font-size-xs)',
      }}>
        <span>CSV · JSON · Parquet · Excel</span>
        <span>Image Folders</span>
        <span>Local-first</span>
      </div>
    </div>
  );
}
