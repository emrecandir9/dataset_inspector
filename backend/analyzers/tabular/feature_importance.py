"""Dataset Inspector - Target-Aware Feature Importance analyzer."""

from __future__ import annotations

from typing import Any

import polars as pl

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, FieldType, Finding, Severity


class FeatureImportanceAnalyzer(Analyzer):
    """Detects target column and calculates feature importance."""
    
    analyzer_id = "feature_importance"
    name = "Feature Importance"
    required_capabilities = {"tabular", "numeric"}
    
    def _find_target_column(self, schema: DatasetSchema, data: pl.DataFrame) -> str | None:
        # Strategy 1: Explicit name matches
        target_names = {"target", "label", "class", "churn", "y"}
        for col in data.columns:
            if col.lower() in target_names:
                return col
                
        # Strategy 2: Last categorical or boolean column
        # In many datasets, the label is the last column
        for col in reversed(data.columns):
            dtype = data[col].dtype
            if dtype == pl.Boolean or dtype == pl.Utf8 or dtype == pl.Categorical or dtype == pl.String:
                # Ensure it's not a high-cardinality ID column
                if data[col].n_unique() <= 20:
                    return col
                    
        return None

    def analyze(self, schema: DatasetSchema, data: Any = None) -> AnalyzerResult:
        if not isinstance(data, pl.DataFrame) or data.height == 0:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No tabular data available",
            )
            
        target_col = self._find_target_column(schema, data)
        if not target_col:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="Could not auto-detect a target variable (e.g. 'label', 'target', or a categorical column).",
            )
            
        # Get numerical features to correlate
        numeric_cols = []
        for f in schema.fields:
            if f.name != target_col and f.dtype in {FieldType.INTEGER, FieldType.FLOAT, FieldType.NUMERIC}:
                numeric_cols.append(f.name)
                
        if not numeric_cols:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No numerical features to evaluate importance against the target.",
            )

        # Encode target if it's a string/categorical
        target_series = data[target_col]
        is_classification = False
        
        if target_series.dtype in {pl.Utf8, pl.Categorical, pl.String, pl.Boolean}:
            is_classification = True
            # Label encode using rank (fastest way in polars for dense encoding)
            if target_series.dtype == pl.Boolean:
                target_series = target_series.cast(pl.Int8)
            else:
                # Assign simple integer to each unique string
                unique_vals = target_series.drop_nulls().unique()
                mapping = {val: i for i, val in enumerate(unique_vals.to_list())}
                target_series = target_series.replace(mapping).cast(pl.Int32)
                
        # Handle cases where target encoding failed or resulted in all nulls
        if target_series.null_count() == len(target_series):
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="error",
                error_message="Target column encoding failed.",
            )
            
        # Compute absolute Pearson correlation with the target
        importances = []
        for col in numeric_cols:
            try:
                # Drop nulls pairwise
                valid_mask = data[col].is_not_null() & target_series.is_not_null()
                if valid_mask.sum() > 1:
                    corr = pl.corr(data[col].filter(valid_mask), target_series.filter(valid_mask))
                    if corr is not None and not pl.Series([corr]).is_nan()[0]:
                        importances.append({"feature": col, "score": abs(corr), "raw": corr})
            except Exception:
                continue
                
        if not importances:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="Failed to compute correlations with the target.",
            )
            
        # Sort by absolute correlation (highest first)
        importances.sort(key=lambda x: x["score"], reverse=True)
        top_features = importances[:5]
        
        metrics = {
            "Target Column": target_col,
            "Target Type": "Classification" if is_classification else "Regression",
        }
        
        # Add top features to metrics
        for i, imp in enumerate(top_features, 1):
            metrics[f"#{i} Feature"] = f"{imp['feature']} (Score: {imp['score']:.3f})"
            
        findings = []
        if top_features:
            best = top_features[0]
            if best["score"] > 0.8:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    code="potential_target_leakage",
                    title="Potential Target Leakage",
                    message=f"Feature '{best['feature']}' has extremely high correlation ({best['raw']:.3f}) with the target. Verify this is not a leaky feature that won't be available at inference time."
                ))
            elif best["score"] < 0.05:
                findings.append(Finding(
                    severity=Severity.INFO,
                    code="low_predictive_power",
                    title="Low Predictive Power",
                    message="None of the numerical features show strong linear correlation with the target. Consider engineering new features or using non-linear models (like Random Forests)."
                ))
            else:
                findings.append(Finding(
                    severity=Severity.INFO,
                    code="strong_predictors_found",
                    title="Strong Predictors Found",
                    message=f"'{best['feature']}' is the strongest linear predictor for the target."
                ))

        # Chart Data
        chart_data = {
            "type": "bar",
            "title": f"Feature Importance (Target: {target_col})",
            "data": {
                "labels": [x["feature"] for x in top_features],
                "datasets": [{
                    "label": "Importance (Abs Correlation)",
                    "data": [round(x["score"], 3) for x in top_features],
                    "backgroundColor": "#32D74B"
                }]
            }
        }

        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics=metrics,
            findings=findings,
            chart_data=chart_data,
        )

register_analyzer(FeatureImportanceAnalyzer())
