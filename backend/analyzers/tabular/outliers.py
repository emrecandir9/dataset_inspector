"""Dataset Inspector - Outlier detection analyzer."""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, FieldType, Finding, Severity


class OutlierAnalyzer(Analyzer):
    """Detects outliers in numeric columns using IQR method."""
    
    analyzer_id = "outliers"
    name = "Outlier Detection"
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
        per_column: list[dict[str, Any]] = []
        total_outliers = 0
        
        numeric_cols = [
            f.name for f in schema.fields
            if f.dtype in {FieldType.NUMERIC, FieldType.INTEGER, FieldType.FLOAT}
            and f.name in df.columns
        ]
        
        for col_name in numeric_cols:
            col = df[col_name].drop_nulls()
            if len(col) < 10:
                continue
            
            try:
                values = col.cast(pl.Float64)
                q1 = float(values.quantile(0.25))
                q3 = float(values.quantile(0.75))
                iqr = q3 - q1
                
                if iqr == 0:
                    continue
                
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                outlier_mask = (values < lower_bound) | (values > upper_bound)
                outlier_count = int(outlier_mask.sum())
                outlier_pct = round(outlier_count / len(values) * 100, 2)
                
                total_outliers += outlier_count
                
                col_info = {
                    "column": col_name,
                    "outlier_count": outlier_count,
                    "outlier_pct": outlier_pct,
                    "lower_bound": round(lower_bound, 4),
                    "upper_bound": round(upper_bound, 4),
                    "q1": round(q1, 4),
                    "q3": round(q3, 4),
                    "iqr": round(iqr, 4),
                }
                per_column.append(col_info)
                
                if outlier_pct > 5:
                    findings.append(Finding(
                        severity=Severity.WARNING,
                        code="high_outlier_rate",
                        title=f"High outlier rate in '{col_name}'",
                        message=f"Column '{col_name}' contains {outlier_pct}% extreme outliers ({outlier_count:,} values outside [{lower_bound:.2f}, {upper_bound:.2f}]).",
                        details=col_info,
                    ))
                elif outlier_pct > 1:
                    findings.append(Finding(
                        severity=Severity.INFO,
                        code="moderate_outliers",
                        title=f"Outliers in '{col_name}'",
                        message=f"Column '{col_name}' contains {outlier_pct}% outliers.",
                        details=col_info,
                    ))
            except Exception:
                continue
        
        # Sort by outlier count
        per_column.sort(key=lambda x: x["outlier_count"], reverse=True)
        
        # Chart data
        charts = []
        outlier_chart = [
            {"name": c["column"], "value": c["outlier_pct"]}
            for c in per_column
            if c["outlier_pct"] > 0
        ]
        if outlier_chart:
            charts.append({
                "type": "bar",
                "title": "Outlier Rate by Column",
                "data": outlier_chart[:15],
                "xKey": "name",
                "yKey": "value",
                "yLabel": "Outlier %",
            })
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "total_outliers": total_outliers,
                "columns_analyzed": len(numeric_cols),
                "columns_with_outliers": sum(1 for c in per_column if c["outlier_count"] > 0),
                "per_column": per_column,
            },
            findings=findings,
            charts=charts,
        )


register_analyzer(OutlierAnalyzer())
