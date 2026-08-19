"""Dataset Inspector - NLP Text Column analyzer."""

from __future__ import annotations

from typing import Any

import polars as pl

from backend.analyzers.base import Analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, FieldType, Finding, Severity


class TextAnalysisAnalyzer(Analyzer):
    """Analyzes text columns for NLP metrics like word counts and vocabulary size."""
    
    analyzer_id = "text_analysis"
    name = "NLP Text Analysis"
    required_capabilities = {"tabular"}
    
    def analyze(self, schema: DatasetSchema, data: Any = None) -> AnalyzerResult:
        if not isinstance(data, pl.DataFrame) or data.height == 0:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No tabular data available",
            )
            
        text_cols = [f.name for f in schema.fields if f.dtype == FieldType.TEXT]
        
        # Filter out categorical/ID columns (we only want actual free-text)
        # Heuristic: A text column is "free text" if its average length > 20 chars
        # or if it has very high cardinality.
        actual_text_cols = []
        for col in text_cols:
            try:
                # Fast check on a sample
                sample = data[col].drop_nulls().head(100)
                if len(sample) == 0:
                    continue
                avg_len = sample.str.len_chars().mean()
                if avg_len is not None and avg_len > 15:
                    actual_text_cols.append(col)
            except Exception:
                continue
                
        if not actual_text_cols:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No free-text columns detected (all string columns appear to be categorical or IDs).",
            )

        metrics = {}
        findings = []
        
        for col in actual_text_cols:
            try:
                series = data[col].drop_nulls()
                if len(series) == 0:
                    continue
                    
                # 1. Empty string / whitespace only
                is_empty = series.str.strip_chars() == ""
                empty_pct = (is_empty.sum() / len(series)) * 100
                
                # 2. Word count
                # Splitting by whitespace to estimate words
                word_counts = series.str.split(" ").list.len()
                avg_words = word_counts.mean()
                max_words = word_counts.max()
                
                metrics[f"{col} - Avg Words"] = f"{avg_words:.1f}"
                metrics[f"{col} - Max Words"] = f"{max_words}"
                
                if empty_pct > 0:
                    metrics[f"{col} - Empty/Whitespace"] = f"{empty_pct:.1f}%"
                    
                if empty_pct > 5:
                    findings.append(Finding(
                        severity=Severity.WARNING,
                        title="Empty Text Fields",
                        description=f"Column '{col}' contains {empty_pct:.1f}% empty or whitespace-only strings."
                    ))
                    
                if avg_words is not None and avg_words > 256:
                    findings.append(Finding(
                        severity=Severity.INFO,
                        title="Long Text Sequences",
                        description=f"Column '{col}' has very long text (avg {avg_words:.1f} words). Standard transformer models (like BERT) may truncate these sequences unless you use Longformer or chunking."
                    ))
                    
            except Exception:
                continue
                
        if not metrics:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="error",
                error_message="Failed to analyze text columns.",
            )

        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics=metrics,
            findings=findings,
            chart_data=None,
        )
