const API_BASE = '/api';

export interface AnalyzeRequest {
  path: string;
  sample_size?: number;
  force_type?: string;
}

export async function analyzeDataset(request: AnalyzeRequest) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Analysis failed');
  }
  return res.json();
}

export async function getReport() {
  const res = await fetch(`${API_BASE}/report`);
  if (!res.ok) throw new Error('No report available');
  return res.json();
}

export async function getExamples(filter = 'random', limit = 20, className?: string) {
  const params = new URLSearchParams({ filter, limit: String(limit) });
  if (className) params.set('class_name', className);
  const res = await fetch(`${API_BASE}/examples?${params}`);
  if (!res.ok) throw new Error('Failed to fetch examples');
  return res.json();
}

export async function getThumbnail(path: string, size = 256) {
  const params = new URLSearchParams({ path, size: String(size) });
  const res = await fetch(`${API_BASE}/image/thumbnail?${params}`);
  if (!res.ok) throw new Error('Failed to fetch thumbnail');
  return res.json();
}

export function getImageUrl(path: string) {
  return `${API_BASE}/image?path=${encodeURIComponent(path)}`;
}

export function getExportUrl(format: string) {
  return `${API_BASE}/report/export?format=${format}`;
}
