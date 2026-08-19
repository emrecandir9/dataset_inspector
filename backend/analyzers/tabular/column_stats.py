"""Dataset Inspector - Per-column statistics analyzer."""

from __future__ import annotations

from typing import Any

import polars as pl

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, FieldType, Finding, Severity


class ColumnStatsAnalyzer(Analyzer):
    """Computes per-column statistics for tabular data."""
    
    analyzer_id = "column_stats"
    name = "Column Statistics"
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
        columns_stats: list[dict[str, Any]] = []
        charts: list[dict[str, Any]] = []
        findings: list[Finding] = []
        
        for field in schema.fields:
            col_name = field.name
            if col_name not in df.columns:
                continue
            
            col = df[col_name]
            
            stats: dict[str, Any] = {
                "column": col_name,
                "dtype": field.dtype.value,
                "total": total_rows,
                "missing": col.null_count(),
                "missing_pct": round(col.null_count() / total_rows * 100, 2) if total_rows > 0 else 0,
                "unique": col.n_unique(),
                "unique_pct": round(col.n_unique() / total_rows * 100, 2) if total_rows > 0 else 0,
            }
            
            # Numeric columns
            if field.dtype in {FieldType.NUMERIC, FieldType.INTEGER, FieldType.FLOAT}:
                non_null = col.drop_nulls()
                if len(non_null) > 0:
                    try:
                        numeric_col = non_null.cast(pl.Float64)
                        stats.update({
                            "min": float(numeric_col.min()),
                            "max": float(numeric_col.max()),
                            "mean": round(float(numeric_col.mean()), 4),
                            "median": round(float(numeric_col.median()), 4),
                            "std": round(float(numeric_col.std()), 4) if len(numeric_col) > 1 else 0,
                            "q25": round(float(numeric_col.quantile(0.25)), 4),
                            "q75": round(float(numeric_col.quantile(0.75)), 4),
                            "zeros": int((numeric_col == 0).sum()),
                            "negatives": int((numeric_col < 0).sum()),
                        })
                        
                        # Distribution histogram data
                        try:
                            hist_data = _compute_histogram(numeric_col)
                            if hist_data:
                                charts.append({
                                    "type": "histogram",
                                    "title": f"Distribution: {col_name}",
                                    "data": hist_data,
                                    "xKey": "bin",
                                    "yKey": "count",
                                })
                        except Exception:
                            pass
                            
                    except Exception:
                        pass
            
            # Categorical / text columns
            elif field.dtype in {FieldType.CATEGORICAL, FieldType.TEXT}:
                non_null = col.drop_nulls().cast(pl.Utf8)
                if len(non_null) > 0:
                    # Top values
                    vc = non_null.value_counts().sort("count", descending=True)
                    top_values = []
                    for row in vc.head(10).iter_rows(named=True):
                        top_values.append({
                            "value": str(row[col_name]),
                            "count": row["count"],
                            "pct": round(row["count"] / total_rows * 100, 2),
                        })
                    stats["top_values"] = top_values
                    
                    # Text length stats
                    if field.dtype == FieldType.TEXT:
                        lengths = non_null.str.len_chars()
                        stats.update({
                            "min_length": int(lengths.min()),
                            "max_length": int(lengths.max()),
                            "mean_length": round(float(lengths.mean()), 1),
                        })
                    
                    # High cardinality warning
                    cardinality_ratio = col.n_unique() / total_rows
                    if cardinality_ratio > 0.9 and col.n_unique() > 50:
                        findings.append(Finding(
                            severity=Severity.INFO,
                            code="high_cardinality",
                            title=f"High cardinality in '{col_name}'",
                            message=f"Column '{col_name}' has {col.n_unique():,} unique values ({cardinality_ratio:.0%} of rows). Consider if this is an identifier.",
                            details={"column": col_name, "unique": col.n_unique()},
                        ))
            
            # Boolean columns
            elif field.dtype == FieldType.BOOLEAN:
                non_null = col.drop_nulls()
                if len(non_null) > 0:
                    true_count = int(non_null.sum())
                    false_count = len(non_null) - true_count
                    stats.update({
                        "true_count": true_count,
                        "false_count": false_count,
                        "true_pct": round(true_count / len(non_null) * 100, 2),
                    })
            
            columns_stats.append(stats)
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "num_columns": len(columns_stats),
                "num_numeric": sum(1 for s in columns_stats if s["dtype"] in {"numeric", "integer", "float"}),
                "num_categorical": sum(1 for s in columns_stats if s["dtype"] == "categorical"),
                "num_text": sum(1 for s in columns_stats if s["dtype"] == "text"),
                "columns": columns_stats,
            },
            findings=findings,
            charts=charts,
        )


def _compute_histogram(col: pl.Series, bins: int = 20) -> list[dict[str, Any]]:
    """Compute histogram data for a numeric column."""
    import numpy as np
    
    values = col.to_numpy()
    values = values[~np.isnan(values)]
    
    if len(values) == 0:
        return []
    
    counts, edges = np.histogram(values, bins=min(bins, len(set(values))))
    
    histogram = []
    for i in range(len(counts)):
        label = f"{edges[i]:.2f}"
        histogram.append({
            "bin": label,
            "count": int(counts[i]),
            "range_start": float(edges[i]),
            "range_end": float(edges[i + 1]),
        })
    
    return histogram


register_analyzer(ColumnStatsAnalyzer())
