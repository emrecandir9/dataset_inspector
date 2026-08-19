"""Dataset Inspector - Abstract base loader.

All dataset loaders implement this interface, producing a unified
DatasetSchema regardless of the source format.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.core.models import DatasetSchema, DetectionResult, ScanResult


class DatasetLoader(ABC):
    """Abstract base class for dataset loaders.
    
    Each loader knows how to:
    1. Detect if it can handle a given dataset (can_load)
    2. Load the dataset into a unified DatasetSchema (load)
    """
    
    loader_id: str = ""
    name: str = ""
    
    @abstractmethod
    def can_load(self, scan: ScanResult) -> DetectionResult | None:
        """Check if this loader can handle the scanned dataset.
        
        Args:
            scan: Result from the filesystem scanner.
            
        Returns:
            DetectionResult if this loader can handle it, None otherwise.
        """
        ...
    
    @abstractmethod
    def load(
        self,
        scan: ScanResult,
        sample_size: int | None = None,
    ) -> DatasetSchema:
        """Load the dataset into a unified schema.
        
        Args:
            scan: Result from the filesystem scanner.
            sample_size: If set, sample this many rows/items.
            
        Returns:
            DatasetSchema with the unified representation.
        """
        ...


# Registry of all available loaders
_LOADERS: list[DatasetLoader] = []


def register_loader(loader: DatasetLoader) -> None:
    """Register a loader in the global registry."""
    _LOADERS.append(loader)


def get_loader(loader_id: str) -> DatasetLoader | None:
    """Get a loader by its ID."""
    for loader in _LOADERS:
        if loader.loader_id == loader_id:
            return loader
    return None


def get_all_loaders() -> list[DatasetLoader]:
    """Get all registered loaders."""
    return list(_LOADERS)
