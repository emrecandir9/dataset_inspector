"""Dataset Inspector - Analyzer registry and dispatcher.

Manages all registered analyzers and dispatches only those
whose required capabilities match the dataset.
"""

from __future__ import annotations

from typing import Any, Callable

from backend.analyzers.base import Analyzer
from backend.core.models import AnalyzerResult, DatasetSchema


# Global registry
_ANALYZERS: list[Analyzer] = []


def register_analyzer(analyzer: Analyzer) -> None:
    """Register an analyzer in the global registry."""
    _ANALYZERS.append(analyzer)


def get_all_analyzers() -> list[Analyzer]:
    """Get all registered analyzers."""
    return list(_ANALYZERS)


def get_applicable_analyzers(schema: DatasetSchema) -> list[Analyzer]:
    """Get analyzers whose capabilities match the dataset."""
    return [a for a in _ANALYZERS if a.can_run(schema)]


def run_all_analyzers(
    schema: DatasetSchema,
    data: Any = None,
    progress_callback: Callable[[float], None] | None = None,
) -> list[AnalyzerResult]:
    """Run all applicable analyzers on the dataset.
    
    Args:
        schema: The unified dataset schema.
        data: Optional data object for analyzers.
        progress_callback: Optional callback for progress (0.0 to 1.0).
        
    Returns:
        List of AnalyzerResult from each applicable analyzer.
    """
    applicable = get_applicable_analyzers(schema)
    results: list[AnalyzerResult] = []
    
    total = len(applicable)
    for i, analyzer in enumerate(applicable):
        try:
            result = analyzer.analyze(schema, data)
            results.append(result)
        except Exception as e:
            results.append(AnalyzerResult(
                analyzer_id=analyzer.analyzer_id,
                analyzer_name=analyzer.name,
                status="error",
                error_message=str(e),
            ))
            
        if progress_callback and total > 0:
            progress_callback((i + 1) / total)
    
    return results
