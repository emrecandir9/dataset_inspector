"""Dataset Inspector - Format detection with confidence scoring.

Analyzes scan results to determine the most likely dataset type.
Uses extension distribution, directory structure, and content sniffing
to produce ranked hypotheses.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from backend.core.config import config
from backend.core.models import (
    DetectionReport,
    DetectionResult,
    Modality,
    ScanResult,
)


# Well-known directory names for splits
SPLIT_NAMES = {"train", "training", "test", "testing", "val", "validation", "dev"}


def detect_format(scan: ScanResult) -> DetectionReport:
    """Analyze scan results and produce ranked format hypotheses.
    
    This is the second stage of the pipeline. It looks at the file
    extension distribution and directory structure to determine what
    kind of dataset this is.
    
    Args:
        scan: Result from the filesystem scanner.
        
    Returns:
        DetectionReport with ranked hypotheses and a selected best match.
    """
    hypotheses: list[DetectionResult] = []
    
    # Build lookup structures
    ext_counts: dict[str, int] = {}
    for ec in scan.extensions:
        ext_counts[ec.extension] = ec.count
    
    total_files = scan.total_files
    if total_files == 0:
        return DetectionReport(hypotheses=[], selected=None)
    
    # Count files by category
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}
    tabular_exts = {".csv", ".tsv"}
    json_exts = {".json", ".jsonl", ".ndjson"}
    parquet_exts = {".parquet", ".pq"}
    excel_exts = {".xlsx", ".xls"}
    
    image_count = sum(ext_counts.get(e, 0) for e in image_exts)
    tabular_count = sum(ext_counts.get(e, 0) for e in tabular_exts)
    json_count = sum(ext_counts.get(e, 0) for e in json_exts)
    parquet_count = sum(ext_counts.get(e, 0) for e in parquet_exts)
    excel_count = sum(ext_counts.get(e, 0) for e in excel_exts)
    
    image_ratio = image_count / total_files if total_files > 0 else 0
    
    # --- Image classification folder detection ---
    if image_ratio > 0.7:
        confidence = _detect_image_classification(scan, image_ratio)
        if confidence > 0:
            hypotheses.append(DetectionResult(
                dataset_type="image_classification",
                modality=Modality.IMAGE,
                confidence=confidence,
                reason=f"{image_count} image files found in folder structure",
                loader_id="image_folder",
            ))
        
        # Generic image folder (lower confidence)
        hypotheses.append(DetectionResult(
            dataset_type="image_folder",
            modality=Modality.IMAGE,
            confidence=max(0.3, image_ratio * 0.6),
            reason=f"{image_count} image files ({image_ratio:.0%} of all files)",
            loader_id="image_folder",
        ))
    
    # --- Mixed Multimodal detection ---
    if tabular_count > 0 and image_count > 0:
        hypotheses.append(DetectionResult(
            dataset_type="mixed_multimodal",
            modality=Modality.IMAGE,
            confidence=0.98,
            reason=f"Found {tabular_count} tabular file(s) and {image_count} image(s)",
            loader_id="smart_mixed",
        ))
        
    # --- CSV detection ---
    if tabular_count > 0:
        csv_count = ext_counts.get(".csv", 0) + ext_counts.get(".tsv", 0)
        confidence = 0.0
        
        if csv_count == 1 and total_files <= 5:
            confidence = 0.95  # Single CSV file, likely the main dataset
        elif csv_count == 1:
            confidence = 0.7
        elif csv_count > 1:
            confidence = 0.8
        
        for ext in [".csv", ".tsv"]:
            if ext in ext_counts:
                hypotheses.append(DetectionResult(
                    dataset_type="csv" if ext == ".csv" else "tsv",
                    modality=Modality.TABULAR,
                    confidence=confidence,
                    reason=f"{ext_counts[ext]} {ext} file(s) found",
                    loader_id="csv",
                ))
    
    # --- JSON / JSONL detection ---
    if json_count > 0:
        # Check if it's a single JSON file or JSONL
        jsonl_count = ext_counts.get(".jsonl", 0) + ext_counts.get(".ndjson", 0)
        json_only = ext_counts.get(".json", 0)
        
        if jsonl_count > 0:
            confidence = 0.85 if jsonl_count == 1 else 0.75
            hypotheses.append(DetectionResult(
                dataset_type="jsonl",
                modality=Modality.TABULAR,
                confidence=confidence,
                reason=f"{jsonl_count} JSONL file(s) found",
                loader_id="json",
            ))
        
        if json_only > 0 and image_ratio < 0.5:
            # Could be tabular JSON, need to sniff content
            confidence = _sniff_json_type(scan)
            hypotheses.append(DetectionResult(
                dataset_type="json",
                modality=Modality.TABULAR,
                confidence=confidence,
                reason=f"{json_only} JSON file(s) found",
                loader_id="json",
            ))
    
    # --- Parquet detection ---
    if parquet_count > 0:
        confidence = 0.95 if parquet_count >= 1 else 0.8
        hypotheses.append(DetectionResult(
            dataset_type="parquet",
            modality=Modality.TABULAR,
            confidence=confidence,
            reason=f"{parquet_count} Parquet file(s) found",
            loader_id="parquet",
        ))
    
    # --- Excel detection ---
    if excel_count > 0:
        confidence = 0.9 if excel_count == 1 else 0.75
        hypotheses.append(DetectionResult(
            dataset_type="excel",
            modality=Modality.TABULAR,
            confidence=confidence,
            reason=f"{excel_count} Excel file(s) found",
            loader_id="excel",
        ))
    
    # Sort by confidence (descending)
    hypotheses.sort(key=lambda h: h.confidence, reverse=True)
    
    selected = hypotheses[0] if hypotheses else None
    
    return DetectionReport(
        hypotheses=hypotheses,
        selected=selected,
    )


def _detect_image_classification(scan: ScanResult, image_ratio: float) -> float:
    """Detect image classification folder structure.
    
    Looks for patterns like:
        train/cats/*.jpg, train/dogs/*.jpg
    or:
        cats/*.jpg, dogs/*.jpg
    """
    root = Path(scan.root_path)
    confidence = 0.0
    
    # Get top-level directories
    top_dirs = set()
    split_dirs = set()
    
    if scan.directory_tree and scan.directory_tree.children:
        for child in scan.directory_tree.children:
            if isinstance(child, type(scan.directory_tree)):  # DirectoryInfo
                name_lower = child.name.lower()
                top_dirs.add(child.name)
                if name_lower in SPLIT_NAMES:
                    split_dirs.add(child.name)
    
    # Pattern 1: Has split directories (train/test/val) with class subdirs
    if split_dirs:
        confidence = 0.85
        # Check if splits have class subdirectories
        for split_dir in split_dirs:
            split_path = root / split_dir
            if split_path.is_dir():
                subdirs = [
                    d for d in os.listdir(split_path)
                    if os.path.isdir(split_path / d) and not d.startswith(".")
                ]
                if len(subdirs) >= 2:
                    confidence = 0.95
                    break
    
    # Pattern 2: No splits, but multiple class directories at root with images
    elif len(top_dirs) >= 2 and image_ratio > 0.8:
        # Check if top-level dirs contain images
        has_class_structure = True
        for d in list(top_dirs)[:10]:  # Check first 10
            dir_path = root / d
            if dir_path.is_dir():
                contents = os.listdir(dir_path)
                image_files = [
                    f for f in contents
                    if os.path.splitext(f)[1].lower() in config.image_extensions
                ]
                if not image_files:
                    has_class_structure = False
                    break
        
        if has_class_structure:
            confidence = 0.85
    
    return confidence


def _sniff_json_type(scan: ScanResult) -> float:
    """Sniff JSON files to determine if they contain tabular data.
    
    Reads first few bytes of JSON files to check structure.
    """
    root = Path(scan.root_path)
    
    for file_info in scan.file_list:
        if file_info.extension == ".json":
            filepath = root / file_info.path
            try:
                with open(filepath, "r") as f:
                    # Read first 4KB
                    start = f.read(4096).strip()
                    
                if start.startswith("["):
                    # JSON array — likely tabular
                    return 0.8
                elif start.startswith("{"):
                    # Could be COCO annotations or config
                    if '"images"' in start and '"annotations"' in start:
                        return 0.3  # Likely COCO, not tabular
                    return 0.5
            except (OSError, UnicodeDecodeError):
                continue
    
    return 0.4
