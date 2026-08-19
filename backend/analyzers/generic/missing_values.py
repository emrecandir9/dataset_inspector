"""Dataset Inspector - Missing values analyzer."""

from __future__ import annotations

from typing import Any

import polars as pl

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, Finding, Severity


class MissingValueAnalyzer(Analyzer):
    """Analyzes missing values across all fields."""
    
    analyzer_id = "missing_values"
    name = "Missing Values"
    required_capabilities = {"tabular"}
    
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
        total_rows = len(df)
        findings: list[Finding] = []
        per_column: list[dict[str, Any]] = []
        total_missing = 0
        
        for col_name in df.columns:
            col = df[col_name]
            null_count = col.null_count()
            total_missing += null_count
            pct = (null_count / total_rows * 100) if total_rows > 0 else 0
            
            per_column.append({
                "column": col_name,
                "missing_count": null_count,
                "missing_pct": round(pct, 2),
                "total_rows": total_rows,
            })
            
            # Generate findings
            if pct > 50:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    code="missing_values_high",
                    title=f"High missing rate in '{col_name}'",
                    message=f"Column '{col_name}' has {pct:.1f}% missing values ({null_count:,} of {total_rows:,} rows).",
                    details={"column": col_name, "pct": pct},
                ))
            elif pct > 20:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    code="missing_values_moderate",
                    title=f"Moderate missing rate in '{col_name}'",
                    message=f"Column '{col_name}' has {pct:.1f}% missing values.",
                    details={"column": col_name, "pct": pct},
                ))
            elif pct > 0:
                findings.append(Finding(
                    severity=Severity.INFO,
                    code="missing_values_low",
                    title=f"Missing values in '{col_name}'",
                    message=f"Column '{col_name}' has {pct:.1f}% missing values.",
                    details={"column": col_name, "pct": pct},
                ))
        
        # Sort by missing percentage
        per_column.sort(key=lambda x: x["missing_pct"], reverse=True)
        
        total_cells = total_rows * len(df.columns)
        overall_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0
        
        # Completely empty columns
        empty_cols = [c for c in per_column if c["missing_pct"] == 100]
        if empty_cols:
            findings.append(Finding(
                severity=Severity.ERROR,
                code="empty_columns",
                title=f"{len(empty_cols)} completely empty column(s)",
                message=f"Columns with 100% missing values: {', '.join(c['column'] for c in empty_cols)}",
                details={"columns": [c["column"] for c in empty_cols]},
            ))
        
        # Chart data: bar chart of missing percentages
        chart_data = [
            {"name": c["column"], "value": c["missing_pct"]}
            for c in per_column
            if c["missing_pct"] > 0
        ]
        
        charts = []
        if chart_data:
            charts.append({
                "type": "bar",
                "title": "Missing Values by Column",
                "data": chart_data[:20],  # Top 20
                "xKey": "name",
                "yKey": "value",
                "yLabel": "Missing %",
            })
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "total_missing_cells": total_missing,
                "total_cells": total_cells,
                "overall_missing_pct": round(overall_pct, 2),
                "columns_with_missing": sum(1 for c in per_column if c["missing_pct"] > 0),
                "per_column": per_column,
            },
            findings=findings,
            charts=charts,
        )


register_analyzer(MissingValueAnalyzer())
