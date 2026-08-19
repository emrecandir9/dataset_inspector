"""Dataset Inspector - CSV/TSV loader.

Uses DuckDB for large files and Polars for smaller ones.
Auto-detects delimiter, encoding, and header.
"""

from __future__ import annotations

import os
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


class CSVLoader(DatasetLoader):
    """Loader for CSV and TSV files."""
    
    loader_id = "csv"
    name = "CSV/TSV Loader"
    
    def can_load(self, scan: ScanResult) -> DetectionResult | None:
        csv_files = [
            f for f in scan.file_list
            if f.extension in {".csv", ".tsv"}
        ]
        if not csv_files:
            return None
        
        return DetectionResult(
            dataset_type="csv",
            modality=Modality.TABULAR,
            confidence=0.9 if len(csv_files) == 1 else 0.7,
            reason=f"Found {len(csv_files)} CSV/TSV file(s)",
            loader_id=self.loader_id,
        )
    
    def load(
        self,
        scan: ScanResult,
        sample_size: int | None = None,
    ) -> DatasetSchema:
        root = Path(scan.root_path)
        
        # Find CSV files
        csv_files = [
            f for f in scan.file_list
            if f.extension in {".csv", ".tsv"}
        ]
        
        if not csv_files:
            raise ValueError("No CSV/TSV files found")
        
        # Use the largest CSV file as the main dataset
        main_file = max(csv_files, key=lambda f: f.size_bytes)
        filepath = root / main_file.path
        
        # Determine separator
        separator = "\t" if main_file.extension == ".tsv" else ","
        
        # Check size — use DuckDB for large files, Polars for smaller
        use_sampling = False
        if main_file.size_bytes > config.auto_sample_threshold_bytes and sample_size is None:
            sample_size = config.default_sample_size
            use_sampling = True
        
        if sample_size:
            # Use DuckDB for sampled reads
            conn = duckdb.connect()
            try:
                query = f"""
                    SELECT * FROM read_csv_auto('{filepath}', 
                        sample_size=10000,
                        ignore_errors=true)
                    USING SAMPLE {sample_size}
                """
                df = conn.execute(query).pl()
                
                # Get total count
                count_query = f"""
                    SELECT COUNT(*) as cnt FROM read_csv_auto('{filepath}',
                        sample_size=10000,
                        ignore_errors=true)
                """
                total_rows = conn.execute(count_query).fetchone()[0]
            finally:
                conn.close()
        else:
            # Read full file with Polars
            try:
                df = pl.read_csv(
                    filepath,
                    separator=separator,
                    infer_schema_length=10000,
                    ignore_errors=True,
                    try_parse_dates=True,
                )
            except Exception:
                # Fallback: try with DuckDB
                conn = duckdb.connect()
                try:
                    df = conn.execute(
                        f"SELECT * FROM read_csv_auto('{filepath}', ignore_errors=true)"
                    ).pl()
                finally:
                    conn.close()
            
            total_rows = len(df)
        
        # Build fields
        fields: list[DatasetField] = []
        capabilities: set[str] = {"tabular"}
        
        for col_name in df.columns:
            col = df[col_name]
            dtype = col.dtype
            field_type = _polars_dtype_to_field_type(dtype)
            
            # Get sample values (up to 5 non-null unique values)
            try:
                sample_vals = (
                    col.drop_nulls()
                    .unique()
                    .head(5)
                    .to_list()
                )
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
        
        # Detect potential label/class columns
        classes: dict[str, int] | None = None
        for field in fields:
            if field.dtype == FieldType.TEXT or field.dtype == FieldType.CATEGORICAL:
                col = df[field.name]
                n_unique = col.n_unique()
                # Heuristic: if < 100 unique values and < 5% of total, likely categorical
                if n_unique < 100 and n_unique < total_rows * 0.05:
                    field.dtype = FieldType.CATEGORICAL
                    capabilities.add("labels")
                    if classes is None:
                        # Use the first categorical column as class distribution
                        vc = col.drop_nulls().value_counts()
                        classes = {
                            str(row[col.name]): row["count"]
                            for row in vc.iter_rows(named=True)
                        }
        
        # Detect splits if multiple CSV files
        splits: dict[str, int] = {}
        if len(csv_files) > 1:
            capabilities.add("splits")
            for f in csv_files:
                name = Path(f.name).stem.lower()
                for split_name in {"train", "test", "val", "validation", "dev"}:
                    if split_name in name:
                        # Count rows in this split
                        try:
                            split_df = pl.read_csv(root / f.path, n_rows=0)
                            split_count = pl.read_csv(root / f.path).height
                            splits[split_name] = split_count
                        except Exception:
                            splits[split_name] = 0
                        break
                else:
                    splits[name] = 0
        
        schema = DatasetSchema(
            modality=Modality.TABULAR,
            source_format="csv" if main_file.extension == ".csv" else "tsv",
            root_path=str(root),
            num_samples=total_rows,
            total_size_bytes=sum(f.size_bytes for f in csv_files),
            splits=splits,
            fields=fields,
            classes=classes,
            capabilities=capabilities,
            analysis_mode=AnalysisMode.SAMPLE if use_sampling else AnalysisMode.FULL,
            sample_size=sample_size if use_sampling else None,
        )
        
        # Store internal reference
        schema._data_path = str(filepath)
        
        return schema


# Auto-register
register_loader(CSVLoader())
