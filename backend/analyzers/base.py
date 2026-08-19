"""Dataset Inspector - Abstract base analyzer."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.core.models import AnalyzerResult, DatasetSchema


class Analyzer(ABC):
    """Abstract base class for all analyzers.
    
    Each analyzer declares what capabilities it requires and produces
    a standardized AnalyzerResult.
    """
    
    analyzer_id: str = ""
    name: str = ""
    required_capabilities: set[str] = set()
    
    def can_run(self, schema: DatasetSchema) -> bool:
        """Check if this analyzer can run on the given dataset."""
        return self.required_capabilities.issubset(schema.capabilities)
    
    @abstractmethod
    def analyze(
        self,
        schema: DatasetSchema,
        data: Any = None,
    ) -> AnalyzerResult:
        """Run analysis on the dataset.
        
        Args:
            schema: The unified dataset schema.
            data: Optional data object (Polars DataFrame, file paths, etc.)
            
        Returns:
            AnalyzerResult with metrics, findings, and chart data.
        """
        ...
