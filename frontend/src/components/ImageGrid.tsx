import React, { useState, useEffect } from 'react';
import { getImageUrl, getThumbnail } from '../api/client';

interface ImageGridItem {
  path?: string;
  relative_path?: string;
  filename?: string;
  label?: string;
  split?: string;
}

interface ImageGridProps {
  examples: ImageGridItem[];
}

function ThumbnailImage({ item }: { item: ImageGridItem }) {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    if (item.path) {
      getThumbnail(item.path, 256)
        .then(res => setSrc(res.data))
        .catch(() => setSrc(null));
    }
  }, [item.path]);

  return (
    <div className="image-grid-item">
      {src ? (
        <img src={src} alt={item.filename || ''} loading="lazy" />
      ) : (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          height: '100%',
          color: 'var(--text-quaternary)',
          fontSize: 'var(--font-size-xs)',
        }}>
          Loading...
        </div>
      )}
      {item.label && (
        <div className="image-grid-label">
          {item.label}
        </div>
      )}
    </div>
  );
}

export default function ImageGrid({ examples }: ImageGridProps) {
  const imageExamples = examples.filter(e => (e as any).type === 'image' || e.path);

  if (imageExamples.length === 0) {
    return (
      <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--font-size-sm)' }}>
        No image examples available.
      </div>
    );
  }

  return (
    <div className="image-grid">
      {imageExamples.map((item, i) => (
        <ThumbnailImage key={i} item={item} />
      ))}
    </div>
  );
}
