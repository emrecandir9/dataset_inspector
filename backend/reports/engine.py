"""Dataset Inspector - Report engine.

Orchestrates the full analysis pipeline:
  scan → detect → load → analyze → health score → report
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

import polars as pl

from backend.analyzers.registry import run_all_analyzers
from backend.core.config import config
from backend.core.models import (
    AnalysisStatus,
    DatasetReport,
    DatasetSchema,
    Modality,
    ProgressUpdate,
    ScanResult,
)
from backend.detectors.format_detector import detect_format
from backend.health.score import calculate_health_score
from backend.loaders.base import get_loader
from backend.scanner.filesystem import scan_directory

# Import loaders to register them
import backend.loaders.csv_loader  # noqa: F401
import backend.loaders.json_loader  # noqa: F401
import backend.loaders.parquet_loader  # noqa: F401
import backend.loaders.excel_loader  # noqa: F401
import backend.loaders.image_folder_loader  # noqa: F401

# Import analyzers to register them
import backend.analyzers.generic.missing_values  # noqa: F401
import backend.analyzers.generic.duplicates  # noqa: F401
import backend.analyzers.generic.class_balance  # noqa: F401
import backend.analyzers.tabular.column_stats  # noqa: F401
import backend.analyzers.tabular.correlation  # noqa: F401
import backend.analyzers.tabular.outliers  # noqa: F401
import backend.analyzers.image.resolution  # noqa: F401
import backend.analyzers.image.quality  # noqa: F401
import backend.analyzers.image.duplicates  # noqa: F401
import backend.analyzers.image.corrupted  # noqa: F401


def run_analysis(
    dataset_path: str,
    sample_size: int | None = None,
    force_type: str | None = None,
    progress_callback: Callable[[ProgressUpdate], None] | None = None,
) -> DatasetReport:
    """Run the complete analysis pipeline on a dataset.
    
    Args:
        dataset_path: Path to the dataset directory or file.
        sample_size: Optional sample size override.
        force_type: Optional forced dataset type.
        progress_callback: Optional callback for progress updates.
        
    Returns:
        Complete DatasetReport.
    """
    start_time = time.time()
    
    def _progress(status: AnalysisStatus, stage: str, progress: float, stage_progress: float = 0.0, message: str = ""):
        if progress_callback:
            progress_callback(ProgressUpdate(
                status=status,
                stage=stage,
                progress=progress,
                stage_progress=stage_progress,
                message=message,
            ))
    
    report = DatasetReport(dataset_path=dataset_path)
    
    # --- Stage 1: Scan ---
    _progress(AnalysisStatus.SCANNING, "Scanning filesystem", 0.05, 0.3, "Walking directory tree...")
    scan_result = scan_directory(dataset_path)
    report.scan_result = scan_result
    
    _progress(AnalysisStatus.SCANNING, "Scanning filesystem", 0.15, 1.0,
              f"Found {scan_result.total_files:,} files ({_format_bytes(scan_result.total_size_bytes)})")
    
    if scan_result.total_files == 0:
        _progress(AnalysisStatus.COMPLETE, "Complete", 1.0, 1.0, "No files found")
        report.analysis_duration_seconds = time.time() - start_time
        return report
    
    # --- Stage 2: Detect format ---
    _progress(AnalysisStatus.DETECTING, "Detecting format", 0.20, 0.3, "Analyzing file types...")
    detection = detect_format(scan_result)
    report.detection = detection
    
    if not detection.selected:
        _progress(AnalysisStatus.COMPLETE, "Complete", 1.0, 1.0, "Could not detect dataset format")
        report.analysis_duration_seconds = time.time() - start_time
        return report
    
    selected = detection.selected
    if force_type:
        # Override with forced type
        for h in detection.hypotheses:
            if h.loader_id == force_type:
                selected = h
                break
    
    _progress(AnalysisStatus.DETECTING, "Detecting format", 0.25, 1.0,
              f"Detected: {selected.dataset_type} ({selected.confidence:.0%} confidence)")
    
    # --- Stage 3: Load ---
    _progress(AnalysisStatus.LOADING, "Loading dataset", 0.30, 0.2, "Loading data...")
    
    loader = get_loader(selected.loader_id)
    if not loader:
        _progress(AnalysisStatus.ERROR, "Error", 0.30, 0.0, f"No loader for: {selected.loader_id}")
        report.analysis_duration_seconds = time.time() - start_time
        return report
    
    schema = loader.load(scan_result, sample_size=sample_size)
    report.schema = schema
    
    mode_label = ""
    if schema.sample_size:
        mode_label = f" (sampled {schema.sample_size:,} of {schema.num_samples:,})"
    
    _progress(AnalysisStatus.LOADING, "Loading dataset", 0.40, 0.8,
              f"Loaded {schema.num_samples:,} samples{mode_label}")
    
    # --- Stage 4: Load data for analyzers ---
    data: Any = None
    if "tabular" in schema.capabilities:
        # Re-read for analysis
        data = _load_tabular_data(schema, scan_result, sample_size)
        
    _progress(AnalysisStatus.LOADING, "Loading dataset", 0.45, 1.0, "Ready for analysis")
    
    # --- Stage 5: Run analyzers ---
    _progress(AnalysisStatus.ANALYZING, "Running analyzers", 0.50, 0.0, "Starting analysis...")
    
    def _analyzer_progress(stage_pct: float):
        _progress(AnalysisStatus.ANALYZING, "Running analyzers", 0.50 + (0.35 * stage_pct), stage_pct, f"Analyzing ({stage_pct:.0%})")
        
    results = run_all_analyzers(schema, data, progress_callback=_analyzer_progress)
    report.analyzer_results = results
    
    _progress(AnalysisStatus.ANALYZING, "Running analyzers", 0.85, 1.0,
              f"Completed {len(results)} analyzers")
    
    # --- Stage 6: Health score ---
    _progress(AnalysisStatus.ANALYZING, "Computing health score", 0.90, 0.5, "Calculating...")
    health = calculate_health_score(schema, results)
    report.health = health
    
    # --- Stage 7: Generate examples ---
    _progress(AnalysisStatus.ANALYZING, "Generating examples", 0.95, 0.9, "Preparing samples...")
    report.examples = _generate_examples(schema, data)
    
    _progress(AnalysisStatus.COMPLETE, "Complete", 1.0, 1.0, "Analysis complete")
    
    # --- Done ---
    report.analysis_duration_seconds = round(time.time() - start_time, 2)
    _progress(AnalysisStatus.COMPLETE, "Complete", 1.0, 1.0,
              f"Analysis complete in {report.analysis_duration_seconds:.1f}s — Health: {health.score:.0f}/100")
    
    return report


def _load_tabular_data(
    schema: DatasetSchema,
    scan: ScanResult,
    sample_size: int | None,
) -> pl.DataFrame | None:
    """Load tabular data for analyzers."""
    root = Path(schema.root_path)
    
    # Find the main data file
    for ext in [".csv", ".tsv", ".parquet", ".pq", ".json", ".jsonl", ".ndjson", ".xlsx", ".xls"]:
        matching = [f for f in scan.file_list if f.extension == ext]
        if matching:
            main_file = max(matching, key=lambda f: f.size_bytes)
            filepath = root / main_file.path
            
            try:
                if ext in {".csv", ".tsv"}:
                    sep = "\t" if ext == ".tsv" else ","
                    df = pl.read_csv(filepath, separator=sep, infer_schema_length=10000,
                                     ignore_errors=True, try_parse_dates=True)
                elif ext in {".parquet", ".pq"}:
                    df = pl.read_parquet(filepath)
                elif ext in {".json"}:
                    import json
                    with open(filepath) as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        df = pl.DataFrame(data)
                    else:
                        continue
                elif ext == ".jsonl" or ext == ".ndjson":
                    df = pl.read_ndjson(filepath)
                elif ext in {".xlsx", ".xls"}:
                    df = pl.read_excel(filepath)
                else:
                    continue
                
                if sample_size and len(df) > sample_size:
                    df = df.sample(n=sample_size, seed=42)
                
                return df
            except Exception:
                continue
    
    return None


def _generate_examples(
    schema: DatasetSchema,
    data: Any = None,
) -> list[dict[str, Any]]:
    """Generate example samples for the UI."""
    examples: list[dict[str, Any]] = []
    
    if isinstance(data, pl.DataFrame):
        # Tabular examples
        sample = data.head(min(20, len(data)))
        for row in sample.iter_rows(named=True):
            examples.append({
                "type": "tabular",
                "data": {k: _serialize_value(v) for k, v in row.items()},
            })
    
    elif "images" in schema.capabilities and schema._file_paths:
        import random
        random.seed(42)
        sample_paths = random.sample(
            schema._file_paths,
            min(config.max_example_images, len(schema._file_paths))
        )
        
        for fp in sample_paths:
            p = Path(fp)
            rel = str(p.relative_to(schema.root_path))
            parts = p.relative_to(schema.root_path).parts
            
            label = None
            split = None
            if len(parts) >= 3:
                split = parts[0]
                label = parts[1]
            elif len(parts) >= 2:
                label = parts[0]
            
            examples.append({
                "type": "image",
                "path": fp,
                "relative_path": rel,
                "filename": p.name,
                "label": label,
                "split": split,
            })
    
    return examples


def _serialize_value(v: Any) -> Any:
    """Serialize a value for JSON output."""
    if v is None:
        return None
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


def _format_bytes(size: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
