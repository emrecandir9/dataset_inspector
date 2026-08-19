import React from 'react';
import BarChartComponent from '../charts/BarChart';
import Histogram from '../charts/Histogram';
import StatCard from '../components/StatCard';

interface ImagesProps {
  report: any;
  getAnalyzerResult: (id: string) => any;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export default function Images({ report, getAnalyzerResult }: ImagesProps) {
  const resolution = getAnalyzerResult('image_resolution');
  const quality = getAnalyzerResult('image_quality');

  if (!resolution && !quality) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Images</h1>
        </div>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
          No image analysis available.
        </div>
      </div>
    );
  }

  const resMet = resolution?.metrics;
  const qualMet = quality?.metrics;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Images</h1>
        <p className="page-subtitle">
          {resMet && `Analyzed ${resMet.analyzed?.toLocaleString()} of ${resMet.total?.toLocaleString()} images`}
        </p>
      </div>

      <div className="stats-grid">
        {resMet && (
          <>
            <StatCard title="Width Range" value={`${resMet.width_min} – ${resMet.width_max}`} detail={`Mean: ${resMet.width_mean}`} />
            <StatCard title="Height Range" value={`${resMet.height_min} – ${resMet.height_max}`} detail={`Mean: ${resMet.height_mean}`} />
            <StatCard title="Unique Resolutions" value={resMet.unique_resolutions} />
            <StatCard title="File Size Range" value={`${formatBytes(resMet.file_size_min)} – ${formatBytes(resMet.file_size_max)}`} detail={`Mean: ${formatBytes(resMet.file_size_mean)}`} />
          </>
        )}
        {qualMet && (
          <>
            <StatCard title="Brightness" value={qualMet.brightness_mean?.toFixed(2)} detail={`σ = ${qualMet.brightness_std?.toFixed(2)}`} />
            <StatCard title="Contrast" value={qualMet.contrast_mean?.toFixed(2)} detail={`σ = ${qualMet.contrast_std?.toFixed(2)}`} />
            <StatCard title="Dark Images" value={qualMet.dark_images} />
            <StatCard title="Blurry Images" value={qualMet.blurry_images} />
          </>
        )}
      </div>

      {/* Resolution charts */}
      {resolution?.charts?.map((chart: any, i: number) => (
        <BarChartComponent key={`res-${i}`} title={chart.title} data={chart.data} color="#48484A" />
      ))}

      {/* Quality charts */}
      {quality?.charts?.map((chart: any, i: number) => (
        <Histogram key={`qual-${i}`} title={chart.title} data={chart.data} />
      ))}
    </div>
  );
}
