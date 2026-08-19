"""Dataset Inspector - Core models for the unified dataset representation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Modality(str, Enum):
    TABULAR = "tabular"
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"
    UNKNOWN = "unknown"


class FieldType(str, Enum):
    NUMERIC = "numeric"
    INTEGER = "integer"
    FLOAT = "float"
    CATEGORICAL = "categorical"
    TEXT = "text"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AnalysisMode(str, Enum):
    FULL = "full"
    SAMPLE = "sample"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    SCANNING = "scanning"
    DETECTING = "detecting"
    LOADING = "loading"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Scanner models
# ---------------------------------------------------------------------------

class FileInfo(BaseModel):
    """Information about a single file."""
    path: str
    name: str
    extension: str
    size_bytes: int
    is_hidden: bool = False
    is_symlink: bool = False


class DirectoryInfo(BaseModel):
    """Information about a directory."""
    path: str
    name: str
    num_files: int = 0
    num_subdirs: int = 0
    total_size_bytes: int = 0
    children: List[Any] = Field(default_factory=list)


class ExtensionCount(BaseModel):
    """Count of files with a given extension."""
    extension: str
    count: int
    total_size_bytes: int


class ScanResult(BaseModel):
    """Result of scanning a dataset directory."""
    root_path: str
    total_files: int = 0
    total_directories: int = 0
    total_size_bytes: int = 0
    extensions: List[ExtensionCount] = Field(default_factory=list)
    directory_tree: Optional[DirectoryInfo] = None
    empty_directories: List[str] = Field(default_factory=list)
    hidden_files: List[str] = Field(default_factory=list)
    symlinks: List[str] = Field(default_factory=list)
    file_list: List[FileInfo] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Detection models
# ---------------------------------------------------------------------------

class DetectionResult(BaseModel):
    """Result from format detection."""
    dataset_type: str  # e.g. "csv", "image_classification", "parquet"
    modality: Modality
    confidence: float  # 0.0 - 1.0
    reason: str
    loader_id: str  # which loader to use


class DetectionReport(BaseModel):
    """All detection hypotheses ranked by confidence."""
    hypotheses: List[DetectionResult] = Field(default_factory=list)
    selected: Optional[DetectionResult] = None


# ---------------------------------------------------------------------------
# Dataset representation (Unified)
# ---------------------------------------------------------------------------

class DatasetField(BaseModel):
    """A single field/column in the dataset."""
    name: str
    dtype: FieldType
    nullable: bool = True
    sample_values: List[Any] = Field(default_factory=list)


class DatasetSchema(BaseModel):
    """The Unified Dataset Representation — the core abstraction.
    
    Every loader produces this, regardless of source format.
    Every analyzer consumes this, regardless of dataset type.
    """
    modality: Modality
    source_format: str  # "csv", "parquet", "image_folder", etc.
    root_path: str
    num_samples: int
    total_size_bytes: int
    
    # Structure
    splits: Dict[str, int] = Field(default_factory=dict)  # {"train": 20341, "test": 5091}
    fields: List[DatasetField] = Field(default_factory=list)
    classes: Optional[Dict[str, int]] = None  # {"cats": 12384, "dogs": 13048}
    
    # Capabilities — what analyzers can run on this dataset
    capabilities: Set[str] = Field(default_factory=set)
    # Possible capabilities:
    #   "tabular"  — has tabular data (columns, rows)
    #   "images"   — has image files
    #   "labels"   — has class/category labels
    #   "splits"   — has train/test/val splits
    #   "text"     — has text fields
    #   "numeric"  — has numeric fields
    
    # Metadata
    analysis_mode: AnalysisMode = AnalysisMode.FULL
    sample_size: Optional[int] = None  # if sampled, how many
    
    # Internal data references (not serialized to API)
    _data_path: Optional[str] = None
    _file_paths: List[str] = []


# ---------------------------------------------------------------------------
# Analyzer result models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    """A single finding/warning from an analyzer."""
    severity: Severity
    code: str  # machine-readable code, e.g. "missing_values_high"
    title: str  # short human-readable title
    message: str  # detailed explanation
    details: Dict[str, Any] = Field(default_factory=dict)


class AnalyzerResult(BaseModel):
    """Result from a single analyzer."""
    analyzer_id: str
    analyzer_name: str
    status: str = "success"  # "success", "error", "skipped"
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    findings: List[Finding] = Field(default_factory=list)
    charts: List[Dict[str, Any]] = Field(default_factory=list)  # chart data for UI


# ---------------------------------------------------------------------------
# Health score
# ---------------------------------------------------------------------------

class HealthBreakdown(BaseModel):
    """Breakdown of the health score."""
    category: str
    score: float  # 0-100
    weight: float
    details: str


class HealthScore(BaseModel):
    """Overall dataset health score."""
    score: float  # 0-100
    grade: str  # "A", "B", "C", "D", "F"
    breakdown: List[HealthBreakdown] = Field(default_factory=list)
    num_errors: int = 0
    num_warnings: int = 0
    num_info: int = 0


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class DatasetReport(BaseModel):
    """The complete analysis report."""
    # Metadata
    version: str = "0.1.0"
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    analysis_duration_seconds: float = 0.0
    
    # Dataset info
    dataset_path: str = ""
    scan_result: Optional[ScanResult] = None
    detection: Optional[DetectionReport] = None
    schema: Optional[DatasetSchema] = None
    
    # Results
    health: Optional[HealthScore] = None
    analyzer_results: List[AnalyzerResult] = Field(default_factory=list)
    
    # Examples
    examples: List[Dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Request to start an analysis."""
    path: str
    mode: AnalysisMode = AnalysisMode.SAMPLE
    sample_size: Optional[int] = None
    force_type: Optional[str] = None  # override detected type


class ProgressUpdate(BaseModel):
    """Progress update sent via WebSocket."""
    status: AnalysisStatus
    stage: str  # human-readable stage name
    progress: float  # 0.0 - 1.0
    message: str = ""
    detail: str = ""
