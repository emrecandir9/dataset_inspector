"""Dataset Inspector - Smart Mixed Loader.

Handles complex datasets with mixed modalities (e.g., CSVs alongside image directories)
and attempts to auto-associate tabular references with media.
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

import duckdb
import polars as pl

from backend.core.config import config
from backend.core.models import (
    AnalysisMode,
    DatasetField,
    DatasetSchema,
    DetectionResult,
    FieldType,
    Modality,
    ScanResult,
)
from backend.loaders.base import DatasetLoader, register_loader


def _polars_dtype_to_field_type(dtype: pl.DataType) -> FieldType:
    """Convert Polars dtype to our FieldType enum."""
    if dtype.is_integer():
        return FieldType.INTEGER
    elif dtype.is_float():
        return FieldType.FLOAT
    elif dtype.is_numeric():
        return FieldType.NUMERIC
    elif dtype == pl.Boolean:
        return FieldType.BOOLEAN
    elif dtype == pl.Utf8 or dtype == pl.String:
        return FieldType.TEXT
    elif dtype.is_temporal():
        return FieldType.DATETIME
    else:
        return FieldType.UNKNOWN


class SmartMixedLoader(DatasetLoader):
    """Loader for mixed (tabular + images) unstructured datasets."""
    
    loader_id = "smart_mixed"
    name = "Smart Mixed Loader"
    
    def can_load(self, scan: ScanResult) -> DetectionResult | None:
        csv_files = [
            f for f in scan.file_list
            if f.extension in {".csv", ".tsv"}
        ]
        
        image_files = [
            f for f in scan.file_list
            if f.extension in config.image_extensions
        ]
        
        # We need BOTH tabular and image files to qualify for this loader
        if not csv_files or not image_files:
            return None
            
        return DetectionResult(
            dataset_type="mixed_multimodal",
            modality=Modality.IMAGE, # Primary modality is image since it has raw pixels
            confidence=0.98, # Very high confidence to intercept before simple image/csv loaders
            reason=f"Found {len(csv_files)} CSV(s) and {len(image_files)} Image(s)",
            loader_id=self.loader_id,
        )

    def load(
        self,
        scan: ScanResult,
        sample_size: int | None = None,
    ) -> DatasetSchema:
        root = Path(scan.root_path)
        
        csv_files = [
            f for f in scan.file_list
            if f.extension in {".csv", ".tsv"}
        ]
        
        image_files = [
            f for f in scan.file_list
            if f.extension in config.image_extensions
        ]
        
        # 1. Gather all image paths
        all_image_paths = [str(root / f.path) for f in image_files]
        image_basenames = {os.path.basename(p) for p in all_image_paths}
        
        # 2. Load and concatenate CSV files (attempting to align schemas)
        dfs = []
        for csv_meta in csv_files:
            csv_path = str(root / csv_meta.path)
            try:
                df = pl.read_csv(csv_path, infer_schema_length=10000, ignore_errors=True)
                dfs.append(df)
            except Exception:
                continue
                
        if not dfs:
            raise ValueError("Found CSV files but failed to parse any of them.")
            
        try:
            combined_df = pl.concat(dfs, how="diagonal")
        except Exception:
            valid_csvs = [f for f in csv_files if "submission" not in f.path.lower()]
            if not valid_csvs:
                valid_csvs = csv_files
            largest_csv = max(valid_csvs, key=lambda f: f.size_bytes)
            combined_df = pl.read_csv(str(root / largest_csv.path), infer_schema_length=10000, ignore_errors=True)
            
        if sample_size and len(combined_df) > sample_size:
            combined_df = combined_df.sample(n=sample_size, seed=42)
            
        # 3. Create DatasetSchema
        schema = DatasetSchema(
            root_path=str(root),
            modality=Modality.IMAGE,
            source_format="mixed_multimodal",
            num_samples=len(all_image_paths),
            total_size_bytes=sum(f.size_bytes for f in scan.file_list),
            fields=[],
            classes={},
            splits={},
            capabilities={"tabular", "images", "labels"}, # Crucial: flags both engines!
            analysis_mode=AnalysisMode.SAMPLE,
        )
        schema._file_paths = all_image_paths
        
        # 4. Extract fields and apply heuristic cross-referencing
        for col_name, dtype in zip(combined_df.columns, combined_df.dtypes):
            field_type = _polars_dtype_to_field_type(dtype)
            
            # Heuristic: if this is a string column, does it contain our image filenames?
            if field_type == FieldType.TEXT:
                sample_vals = combined_df[col_name].drop_nulls().head(100).to_list()
                if sample_vals:
                    match_count = 0
                    for val in sample_vals:
                        if str(val) in image_basenames or f"{val}.jpg" in image_basenames or f"{val}.png" in image_basenames:
                            match_count += 1
                            
                    if match_count / len(sample_vals) >= 0.5:
                        field_type = FieldType.IMAGE
            
            schema.fields.append(DatasetField(
                name=col_name,
                dtype=field_type,
                nullable=combined_df[col_name].null_count() > 0,
            ))
        # 5. Extract classes if there is a label column
        for col in combined_df.columns:
            if col.lower() in ["class", "label", "category", "target"]:
                class_counts = combined_df[col].value_counts().to_dicts()
                schema.classes = {str(d[col]): d["count"] for d in class_counts if d[col] is not None}
                break
            
        return schema

register_loader(SmartMixedLoader())
