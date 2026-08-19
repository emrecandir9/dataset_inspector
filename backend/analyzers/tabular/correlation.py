"""Dataset Inspector - Correlation analyzer."""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, FieldType, Finding, Severity


class CorrelationAnalyzer(Analyzer):
    """Computes Pearson correlation matrix for numeric columns."""
    
    analyzer_id = "correlation"
    name = "Feature Correlation"
    required_capabilities = {"tabular", "numeric"}
    
    def analyze(
        self,
        schema: DatasetSchema,
        data: Any = None,
    ) -> AnalyzerResult:
        if not isinstance(data, pl.DataFrame):
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No tabular data available",
            )
        
        df = data
        findings: list[Finding] = []
        
        # Select numeric columns
        numeric_cols = [
            f.name for f in schema.fields
            if f.dtype in {FieldType.NUMERIC, FieldType.INTEGER, FieldType.FLOAT}
            and f.name in df.columns
        ]
        
        if len(numeric_cols) < 2:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="Need at least 2 numeric columns for correlation",
            )
        
        # Limit to first 50 numeric columns
        numeric_cols = numeric_cols[:50]
        
        # Compute correlation matrix
        numeric_df = df.select(numeric_cols).drop_nulls()
        
        if len(numeric_df) < 10:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="Too few non-null rows for correlation",
            )
        
        try:
            matrix = np.corrcoef(numeric_df.to_numpy().T)
        except Exception:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="error",
                error_message="Failed to compute correlation matrix",
            )
        
        # Find highly correlated pairs
        high_correlations: list[dict[str, Any]] = []
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                corr = float(matrix[i][j])
                if not np.isnan(corr) and abs(corr) > 0.8:
                    high_correlations.append({
                        "col_a": numeric_cols[i],
                        "col_b": numeric_cols[j],
                        "correlation": round(corr, 4),
                    })
        
        # Sort by absolute correlation
        high_correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        
        if high_correlations:
            for hc in high_correlations[:5]:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    code="high_correlation",
                    title=f"High correlation: '{hc['col_a']}' ↔ '{hc['col_b']}'",
                    message=f"Correlation of {hc['correlation']:.3f} between '{hc['col_a']}' and '{hc['col_b']}'. Consider removing redundant features.",
                    details=hc,
                ))
        
        # Prepare correlation matrix for chart
        corr_matrix_data = []
        for i, col_a in enumerate(numeric_cols):
            for j, col_b in enumerate(numeric_cols):
                val = float(matrix[i][j])
                if not np.isnan(val):
                    corr_matrix_data.append({
                        "x": col_a,
                        "y": col_b,
                        "value": round(val, 3),
                    })
        
        charts = []
        if len(numeric_cols) <= 20:
            charts.append({
                "type": "heatmap",
                "title": "Correlation Matrix",
                "data": corr_matrix_data,
                "columns": numeric_cols,
            })
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "num_numeric_columns": len(numeric_cols),
                "high_correlations": high_correlations,
                "matrix_columns": numeric_cols,
            },
            findings=findings,
            charts=charts,
        )


register_analyzer(CorrelationAnalyzer())
