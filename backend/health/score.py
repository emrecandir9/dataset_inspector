"""Dataset Inspector - Dataset health score calculator.

Computes a weighted composite score from analyzer results.
H = w_m * M + w_d * D + w_c * C + w_q * Q + w_s * S
"""

from __future__ import annotations

from backend.core.models import (
    AnalyzerResult,
    DatasetSchema,
    HealthBreakdown,
    HealthScore,
    Severity,
)


def calculate_health_score(
    schema: DatasetSchema,
    results: list[AnalyzerResult],
) -> HealthScore:
    """Calculate overall dataset health score from analyzer results.
    
    Returns a score from 0-100 with letter grade and breakdown.
    """
    breakdowns: list[HealthBreakdown] = []
    
    # Count findings by severity
    num_errors = 0
    num_warnings = 0
    num_info = 0
    
    for r in results:
        for f in r.findings:
            if f.severity == Severity.ERROR:
                num_errors += 1
            elif f.severity == Severity.WARNING:
                num_warnings += 1
            else:
                num_info += 1
    
    # --- Missingness score (weight: 0.25) ---
    missing_score = 100.0
    missing_result = _find_result(results, "missing_values")
    if missing_result and missing_result.status == "success":
        overall_pct = missing_result.metrics.get("overall_missing_pct", 0)
        if overall_pct > 50:
            missing_score = 10
        elif overall_pct > 20:
            missing_score = 40
        elif overall_pct > 5:
            missing_score = 70
        elif overall_pct > 1:
            missing_score = 85
        elif overall_pct > 0:
            missing_score = 95
    breakdowns.append(HealthBreakdown(
        category="Completeness",
        score=missing_score,
        weight=0.25,
        details=f"Data completeness: {missing_score:.0f}/100",
    ))
    
    # --- Duplicate quality score (weight: 0.20) ---
    dup_score = 100.0
    dup_result = _find_result(results, "duplicates")
    img_dup_result = _find_result(results, "image_duplicates")
    
    if dup_result and dup_result.status == "success":
        dup_pct = dup_result.metrics.get("duplicate_pct", 0)
        if dup_pct > 20:
            dup_score = 30
        elif dup_pct > 10:
            dup_score = 50
        elif dup_pct > 5:
            dup_score = 70
        elif dup_pct > 1:
            dup_score = 85
        elif dup_pct > 0:
            dup_score = 95
    
    if img_dup_result and img_dup_result.status == "success":
        exact = img_dup_result.metrics.get("exact_duplicate_count", 0)
        near = img_dup_result.metrics.get("near_duplicate_pairs", 0)
        analyzed = img_dup_result.metrics.get("analyzed", 1)
        total_dup_rate = (exact + near) / max(analyzed, 1) * 100
        
        img_dup_score = 100.0
        if total_dup_rate > 10:
            img_dup_score = 40
        elif total_dup_rate > 5:
            img_dup_score = 60
        elif total_dup_rate > 1:
            img_dup_score = 80
        elif total_dup_rate > 0:
            img_dup_score = 90
        
        dup_score = min(dup_score, img_dup_score)
    
    breakdowns.append(HealthBreakdown(
        category="Uniqueness",
        score=dup_score,
        weight=0.20,
        details=f"Duplicate quality: {dup_score:.0f}/100",
    ))
    
    # --- Class balance score (weight: 0.20) ---
    class_score = 100.0
    class_result = _find_result(results, "class_balance")
    if class_result and class_result.status == "success":
        ratio = class_result.metrics.get("imbalance_ratio", 1)
        if ratio > 20:
            class_score = 20
        elif ratio > 10:
            class_score = 40
        elif ratio > 5:
            class_score = 60
        elif ratio > 3:
            class_score = 75
        elif ratio > 1.5:
            class_score = 90
    elif "labels" not in schema.capabilities:
        class_score = 100  # No labels → not applicable
    
    breakdowns.append(HealthBreakdown(
        category="Balance",
        score=class_score,
        weight=0.20,
        details=f"Class balance: {class_score:.0f}/100",
    ))
    
    # --- Data quality score (weight: 0.20) ---
    quality_score = 100.0
    
    corrupted_result = _find_result(results, "corrupted_images")
    if corrupted_result and corrupted_result.status == "success":
        total_issues = corrupted_result.metrics.get("total_issues", 0)
        total_checked = corrupted_result.metrics.get("total_checked", 1)
        issue_rate = total_issues / max(total_checked, 1) * 100
        
        if issue_rate > 5:
            quality_score = 30
        elif issue_rate > 2:
            quality_score = 55
        elif issue_rate > 0.5:
            quality_score = 75
        elif issue_rate > 0:
            quality_score = 90
    
    outlier_result = _find_result(results, "outliers")
    if outlier_result and outlier_result.status == "success":
        cols_with_outliers = outlier_result.metrics.get("columns_with_outliers", 0)
        cols_analyzed = outlier_result.metrics.get("columns_analyzed", 1)
        if cols_analyzed > 0:
            outlier_ratio = cols_with_outliers / cols_analyzed
            if outlier_ratio > 0.5:
                quality_score = min(quality_score, 60)
            elif outlier_ratio > 0.3:
                quality_score = min(quality_score, 75)
    
    breakdowns.append(HealthBreakdown(
        category="Quality",
        score=quality_score,
        weight=0.20,
        details=f"Data quality: {quality_score:.0f}/100",
    ))
    
    # --- Consistency score (weight: 0.15) ---
    consistency_score = 100.0
    
    # Penalize for cross-split duplicates
    if img_dup_result and img_dup_result.status == "success":
        for finding in img_dup_result.findings:
            if finding.code == "cross_split_duplicates":
                consistency_score = 40
                break
    
    breakdowns.append(HealthBreakdown(
        category="Consistency",
        score=consistency_score,
        weight=0.15,
        details=f"Split consistency: {consistency_score:.0f}/100",
    ))
    
    # Compute weighted total
    total_score = sum(b.score * b.weight for b in breakdowns)
    
    # Determine grade
    if total_score >= 90:
        grade = "A"
    elif total_score >= 80:
        grade = "B"
    elif total_score >= 70:
        grade = "C"
    elif total_score >= 60:
        grade = "D"
    else:
        grade = "F"
    
    return HealthScore(
        score=round(total_score, 1),
        grade=grade,
        breakdown=breakdowns,
        num_errors=num_errors,
        num_warnings=num_warnings,
        num_info=num_info,
    )


def _find_result(results: list[AnalyzerResult], analyzer_id: str) -> AnalyzerResult | None:
    """Find an analyzer result by ID."""
    for r in results:
        if r.analyzer_id == analyzer_id:
            return r
    return None
