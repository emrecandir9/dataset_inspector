"""Dataset Inspector - JSON/JSONL loader."""

from __future__ import annotations

import json
from pathlib import Path

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
from backend.loaders.csv_loader import _polars_dtype_to_field_type


class JSONLoader(DatasetLoader):
    """Loader for JSON and JSONL (newline-delimited JSON) files."""
    
    loader_id = "json"
    name = "JSON/JSONL Loader"
    
    def can_load(self, scan: ScanResult) -> DetectionResult | None:
        json_files = [
            f for f in scan.file_list
            if f.extension in {".json", ".jsonl", ".ndjson"}
        ]
        if not json_files:
            return None
        
        return DetectionResult(
            dataset_type="json",
            modality=Modality.TABULAR,
            confidence=0.8,
            reason=f"Found {len(json_files)} JSON/JSONL file(s)",
            loader_id=self.loader_id,
        )
    
    def load(
        self,
        scan: ScanResult,
        sample_size: int | None = None,
    ) -> DatasetSchema:
        root = Path(scan.root_path)
        
        json_files = [
            f for f in scan.file_list
            if f.extension in {".json", ".jsonl", ".ndjson"}
        ]
        
        if not json_files:
            raise ValueError("No JSON/JSONL files found")
        
        main_file = max(json_files, key=lambda f: f.size_bytes)
        filepath = root / main_file.path
        
        is_jsonl = main_file.extension in {".jsonl", ".ndjson"}
        
        if not is_jsonl:
            # Check if JSON file is an array of objects
            with open(filepath, "r") as f:
                first_char = f.read(1).strip()
                if not first_char:
                    raise ValueError("Empty JSON file")
            
            # Try reading as array of objects or JSONL
            if first_char == "[":
                is_jsonl = False
            elif first_char == "{":
                # Could be JSONL even with .json extension
                is_jsonl = True
            else:
                raise ValueError(f"Unexpected JSON start character: {first_char}")
        
        # Read with Polars
        use_sampling = False
        if main_file.size_bytes > config.auto_sample_threshold_bytes and sample_size is None:
            sample_size = config.default_sample_size
            use_sampling = True
        
        try:
            if is_jsonl:
                df = pl.read_ndjson(filepath)
            else:
                # Read JSON array
                with open(filepath, "r") as f:
                    data = json.load(f)
                
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    df = pl.DataFrame(data)
                else:
                    raise ValueError("JSON file does not contain an array of objects")
        except Exception as e:
            # Fallback: try line-by-line
            records = []
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            if not records:
                raise ValueError(f"Could not parse JSON file: {e}")
            df = pl.DataFrame(records)
        
        total_rows = len(df)
        
        if use_sampling and sample_size and len(df) > sample_size:
            df = df.sample(n=sample_size, seed=42)
        
        # Build fields
        fields: list[DatasetField] = []
        capabilities: set[str] = {"tabular"}
        
        for col_name in df.columns:
            col = df[col_name]
            field_type = _polars_dtype_to_field_type(col.dtype)
            
            try:
                sample_vals = col.drop_nulls().unique().head(5).to_list()
            except Exception:
                sample_vals = []
            
            fields.append(DatasetField(
                name=col_name,
                dtype=field_type,
                nullable=col.null_count() > 0,
                sample_values=sample_vals,
            ))
            
            if field_type in {FieldType.NUMERIC, FieldType.INTEGER, FieldType.FLOAT}:
                capabilities.add("numeric")
            if field_type == FieldType.TEXT:
                capabilities.add("text")
        
        # Detect classes
        classes: dict[str, int] | None = None
        for field in fields:
            if field.dtype in {FieldType.TEXT, FieldType.CATEGORICAL}:
                col = df[field.name]
                n_unique = col.n_unique()
                if n_unique < 100 and n_unique < total_rows * 0.05:
                    field.dtype = FieldType.CATEGORICAL
                    capabilities.add("labels")
                    if classes is None:
                        vc = col.drop_nulls().value_counts()
                        classes = {
                            str(row[col.name]): row["count"]
                            for row in vc.iter_rows(named=True)
                        }
        
        return DatasetSchema(
            modality=Modality.TABULAR,
            source_format="jsonl" if is_jsonl else "json",
            root_path=str(root),
            num_samples=total_rows,
            total_size_bytes=sum(f.size_bytes for f in json_files),
            splits={},
            fields=fields,
            classes=classes,
            capabilities=capabilities,
            analysis_mode=AnalysisMode.SAMPLE if use_sampling else AnalysisMode.FULL,
            sample_size=sample_size if use_sampling else None,
        )


register_loader(JSONLoader())
