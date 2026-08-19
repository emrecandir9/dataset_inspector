"""Dataset Inspector - Time Series analyzer."""

from __future__ import annotations

from typing import Any

import polars as pl

from backend.analyzers.base import Analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, FieldType, Finding, Severity


class TimeSeriesAnalyzer(Analyzer):
    """Analyzes DateTime columns for temporal spans and frequency."""
    
    analyzer_id = "time_series"
    name = "Time Series Analysis"
    required_capabilities = {"tabular"}
    
    def analyze(self, schema: DatasetSchema, data: Any = None) -> AnalyzerResult:
        if not isinstance(data, pl.DataFrame) or data.height == 0:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No tabular data available",
            )
            
        time_cols = [f.name for f in schema.fields if f.dtype == FieldType.DATETIME]
        
        if not time_cols:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No DateTime columns detected.",
            )

        metrics = {}
        findings = []
        
        for col in time_cols:
            try:
                series = data[col].drop_nulls()
                if len(series) == 0:
                    continue
                    
                min_time = series.min()
                max_time = series.max()
                unique_times = series.n_unique()
                
                metrics[f"{col} - Start"] = str(min_time)
                metrics[f"{col} - End"] = str(max_time)
                metrics[f"{col} - Unique Timestamps"] = f"{unique_times:,}"
                
                if unique_times > 0:
                    try:
                        # Try to calculate approximate frequency
                        # Polars duration cast to microseconds
                        sorted_series = series.sort()
                        diffs = sorted_series.diff().drop_nulls()
                        if len(diffs) > 0:
                            # Mode of differences (most common interval)
                            freq = diffs.mode()
                            if len(freq) > 0:
                                freq_val = freq[0]
                                metrics[f"{col} - Main Interval"] = str(freq_val)
                    except Exception:
                        pass
                
            except Exception:
                continue
                
        if not metrics:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="error",
                error_message="Failed to analyze DateTime columns.",
            )

        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics=metrics,
            findings=findings,
            chart_data=None,
        )
