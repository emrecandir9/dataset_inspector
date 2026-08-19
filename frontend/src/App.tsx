import React, { useState } from 'react';
import { analyzeDataset } from './api/client';
import Sidebar from './components/Sidebar';
import Landing from './pages/Landing';
import Overview from './pages/Overview';
import Structure from './pages/Structure';
import Statistics from './pages/Statistics';
import Quality from './pages/Quality';
import Classes from './pages/Classes';
import Images from './pages/Images';
import Duplicates from './pages/Duplicates';
import Examples from './pages/Examples';

export default function App() {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [activePage, setActivePage] = useState('overview');

  const handleAnalyze = async (path: string) => {
    setLoading(true);
    setError(null);
    setLoadingMessage('Starting analysis...');

    try {
      const result = await analyzeDataset({ path });
      setReport(result.report);
      setActivePage('overview');
    } catch (e: any) {
      setError(e.message || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setReport(null);
    setError(null);
  };

  // Loading state
  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="loading-spinner" />
        <div className="loading-stage">{loadingMessage}</div>
        <div className="loading-text">This may take a moment for large datasets</div>
      </div>
    );
  }

  // Landing page
  if (!report) {
    return <Landing onAnalyze={handleAnalyze} error={error} />;
  }

  // Report pages
  const schema = report.schema;
  const findings = report.analyzer_results?.flatMap((r: any) => r.findings || []) || [];
  const getAnalyzerResult = (id: string) =>
    report.analyzer_results?.find((r: any) => r.analyzer_id === id);

  const pages: Record<string, React.ReactNode> = {
    overview: <Overview report={report} findings={findings} onNavigate={setActivePage} />,
    structure: <Structure report={report} />,
    statistics: <Statistics report={report} getAnalyzerResult={getAnalyzerResult} />,
    quality: <Quality report={report} findings={findings} getAnalyzerResult={getAnalyzerResult} />,
    classes: <Classes report={report} getAnalyzerResult={getAnalyzerResult} />,
    images: <Images report={report} getAnalyzerResult={getAnalyzerResult} />,
    duplicates: <Duplicates report={report} getAnalyzerResult={getAnalyzerResult} findings={findings} />,
    examples: <Examples report={report} />,
  };

  return (
    <div className="app-layout">
      <Sidebar
        activePage={activePage}
        onNavigate={setActivePage}
        schema={schema}
      />
      <main className="app-content">
        {pages[activePage] || pages.overview}
      </main>
    </div>
  );
}
