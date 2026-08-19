import React from 'react';

interface HealthScoreProps {
  health: {
    score: number;
    grade: string;
    breakdown: Array<{
      category: string;
      score: number;
      weight: number;
      details: string;
    }>;
    num_errors: number;
    num_warnings: number;
    num_info: number;
  };
}

function scoreColor(score: number): string {
  if (score >= 80) return 'var(--color-success)';
  if (score >= 60) return 'var(--color-warning)';
  return 'var(--color-error)';
}

export default function HealthScore({ health }: HealthScoreProps) {
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (health.score / 100) * circumference;
  const color = scoreColor(health.score);

  return (
    <div className="health-score">
      <div className="health-score-circle">
        <svg viewBox="0 0 96 96">
          <circle
            className="health-score-circle-bg"
            cx="48" cy="48" r="40"
          />
          <circle
            className="health-score-circle-fill"
            cx="48" cy="48" r="40"
            stroke={color}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
          />
        </svg>
        <div className="health-score-number" style={{ color }}>
          {Math.round(health.score)}
        </div>
      </div>

      <div className="health-score-meta">
        <div className="health-score-grade">
          Grade {health.grade} · {health.num_errors} errors · {health.num_warnings} warnings · {health.num_info} info
        </div>
        <div className="health-breakdown">
          {health.breakdown.map(b => (
            <div key={b.category} className="health-breakdown-item">
              <span className="health-breakdown-label">{b.category}</span>
              <div className="health-breakdown-bar">
                <div
                  className="health-breakdown-bar-fill"
                  style={{
                    width: `${b.score}%`,
                    background: scoreColor(b.score),
                  }}
                />
              </div>
              <span className="health-breakdown-value">{Math.round(b.score)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
