"""Dataset Inspector - Duplicate rows analyzer."""

from __future__ import annotations

from typing import Any

import polars as pl

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, Finding, Severity


class DuplicateAnalyzer(Analyzer):
    """Detects duplicate rows in tabular data."""
    
    analyzer_id = "duplicates"
    name = "Duplicate Detection"
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
        
        # Exact duplicate rows
        unique_rows = df.unique().height
        duplicate_count = total_rows - unique_rows
        duplicate_pct = (duplicate_count / total_rows * 100) if total_rows > 0 else 0
        
        if duplicate_pct > 10:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="high_duplicate_rate",
                title=f"{duplicate_count:,} duplicate rows ({duplicate_pct:.1f}%)",
                message=f"The dataset contains {duplicate_count:,} exact duplicate rows out of {total_rows:,} total rows.",
            ))
        elif duplicate_pct > 1:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="moderate_duplicate_rate",
                title=f"{duplicate_count:,} duplicate rows ({duplicate_pct:.1f}%)",
                message=f"Found {duplicate_count:,} exact duplicate rows.",
            ))
        elif duplicate_count > 0:
            findings.append(Finding(
                severity=Severity.INFO,
                code="low_duplicate_rate",
                title=f"{duplicate_count:,} duplicate rows",
                message=f"Found {duplicate_count:,} exact duplicate rows ({duplicate_pct:.2f}%).",
            ))
        
        # Detect potential ID columns (100% unique)
        potential_ids: list[str] = []
        for col_name in df.columns:
            col = df[col_name]
            if col.n_unique() == total_rows and col.null_count() == 0:
                potential_ids.append(col_name)
        
        if potential_ids:
            findings.append(Finding(
                severity=Severity.INFO,
                code="potential_id_columns",
                title=f"Potential identifier column(s): {', '.join(potential_ids)}",
                message=f"Column(s) {', '.join(potential_ids)} appear unique in 100% of rows. These may be identifier columns.",
                details={"columns": potential_ids},
            ))
        
        # Constant columns (only 1 unique value)
        constant_cols: list[str] = []
        for col_name in df.columns:
            if df[col_name].n_unique() <= 1:
                constant_cols.append(col_name)
        
        if constant_cols:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="constant_columns",
                title=f"{len(constant_cols)} constant column(s)",
                message=f"Columns with only one unique value: {', '.join(constant_cols)}. These carry no information.",
                details={"columns": constant_cols},
            ))
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "total_rows": total_rows,
                "unique_rows": unique_rows,
                "duplicate_rows": duplicate_count,
                "duplicate_pct": round(duplicate_pct, 2),
                "potential_id_columns": potential_ids,
                "constant_columns": constant_cols,
            },
            findings=findings,
        )


register_analyzer(DuplicateAnalyzer())
