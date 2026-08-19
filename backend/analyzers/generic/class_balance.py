"""Dataset Inspector - Class balance analyzer."""

from __future__ import annotations

from typing import Any

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, Finding, Severity


class ClassBalanceAnalyzer(Analyzer):
    """Analyzes class distribution and detects imbalance."""
    
    analyzer_id = "class_balance"
    name = "Class Balance"
    required_capabilities = {"labels"}
    
    def analyze(
        self,
        schema: DatasetSchema,
        data: Any = None,
    ) -> AnalyzerResult:
        if not schema.classes:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No class labels found",
            )
        
        classes = schema.classes
        findings: list[Finding] = []
        
        total_samples = sum(classes.values())
        num_classes = len(classes)
        
        # Sort by count descending
        sorted_classes = sorted(classes.items(), key=lambda x: x[1], reverse=True)
        
        largest_class = sorted_classes[0]
        smallest_class = sorted_classes[-1]
        
        # Imbalance ratio
        imbalance_ratio = (
            largest_class[1] / smallest_class[1]
            if smallest_class[1] > 0 else float("inf")
        )
        
        # Per-class percentages
        class_distribution = [
            {
                "name": name,
                "count": count,
                "pct": round(count / total_samples * 100, 2) if total_samples > 0 else 0,
            }
            for name, count in sorted_classes
        ]
        
        # Findings
        if imbalance_ratio > 10:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="severe_class_imbalance",
                title="Severe class imbalance detected",
                message=(
                    f"Largest class '{largest_class[0]}' ({largest_class[1]:,}) is "
                    f"{imbalance_ratio:.1f}× larger than smallest class "
                    f"'{smallest_class[0]}' ({smallest_class[1]:,})."
                ),
                details={
                    "largest": largest_class[0],
                    "smallest": smallest_class[0],
                    "ratio": round(imbalance_ratio, 1),
                },
            ))
        elif imbalance_ratio > 3:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="moderate_class_imbalance",
                title="Moderate class imbalance",
                message=(
                    f"Imbalance ratio of {imbalance_ratio:.1f}:1 between "
                    f"'{largest_class[0]}' and '{smallest_class[0]}'."
                ),
                details={"ratio": round(imbalance_ratio, 1)},
            ))
        elif imbalance_ratio > 1.5:
            findings.append(Finding(
                severity=Severity.INFO,
                code="slight_class_imbalance",
                title="Slight class imbalance",
                message=f"Imbalance ratio of {imbalance_ratio:.1f}:1.",
            ))
        
        # Very small classes
        small_classes = [
            c for c in class_distribution
            if c["count"] < total_samples * 0.01  # less than 1%
        ]
        if small_classes:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="very_small_classes",
                title=f"{len(small_classes)} class(es) with < 1% of samples",
                message=(
                    f"Classes with very few samples: "
                    f"{', '.join(c['name'] for c in small_classes[:5])}"
                ),
                details={"classes": [c["name"] for c in small_classes]},
            ))
        
        # Chart data
        charts = [
            {
                "type": "bar",
                "title": "Class Distribution",
                "data": class_distribution,
                "xKey": "name",
                "yKey": "count",
                "yLabel": "Samples",
            }
        ]
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "num_classes": num_classes,
                "total_samples": total_samples,
                "imbalance_ratio": round(imbalance_ratio, 2),
                "largest_class": {"name": largest_class[0], "count": largest_class[1]},
                "smallest_class": {"name": smallest_class[0], "count": smallest_class[1]},
                "distribution": class_distribution,
            },
            findings=findings,
            charts=charts,
        )


register_analyzer(ClassBalanceAnalyzer())
