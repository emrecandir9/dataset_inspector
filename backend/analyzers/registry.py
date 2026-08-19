"""Dataset Inspector - Analyzer registry and dispatcher.

Manages all registered analyzers and dispatches only those
whose required capabilities match the dataset.
"""

from __future__ import annotations

from typing import Any

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
) -> list[AnalyzerResult]:
    """Run all applicable analyzers on the dataset.
    
    Args:
        schema: The unified dataset schema.
        data: Optional data object for analyzers.
        
    Returns:
        List of AnalyzerResult from each applicable analyzer.
    """
    applicable = get_applicable_analyzers(schema)
    results: list[AnalyzerResult] = []
    
    for analyzer in applicable:
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
    
    return results
