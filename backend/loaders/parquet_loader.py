"""Dataset Inspector - Parquet loader."""

from __future__ import annotations

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
from backend.loaders.csv_loader import _polars_dtype_to_field_type


class ParquetLoader(DatasetLoader):
    """Loader for Apache Parquet files."""
    
    loader_id = "parquet"
    name = "Parquet Loader"
    
    def can_load(self, scan: ScanResult) -> DetectionResult | None:
        pq_files = [
            f for f in scan.file_list
            if f.extension in {".parquet", ".pq"}
        ]
        if not pq_files:
            return None
        
        return DetectionResult(
            dataset_type="parquet",
            modality=Modality.TABULAR,
            confidence=0.95,
            reason=f"Found {len(pq_files)} Parquet file(s)",
            loader_id=self.loader_id,
        )
    
    def load(
        self,
        scan: ScanResult,
        sample_size: int | None = None,
    ) -> DatasetSchema:
        root = Path(scan.root_path)
        
        pq_files = [
            f for f in scan.file_list
            if f.extension in {".parquet", ".pq"}
        ]
        
        if not pq_files:
            raise ValueError("No Parquet files found")
        
        total_size = sum(f.size_bytes for f in pq_files)
        use_sampling = False
        
        if total_size > config.auto_sample_threshold_bytes and sample_size is None:
            sample_size = config.default_sample_size
            use_sampling = True
        
        # Use DuckDB for efficient Parquet reading
        conn = duckdb.connect()
        try:
            if len(pq_files) == 1:
                filepath = root / pq_files[0].path
                source = f"'{filepath}'"
            else:
                # Use glob for multiple files
                source = f"'{root}/**/*.parquet'"
            
            # Get total count
            total_rows = conn.execute(
                f"SELECT COUNT(*) FROM read_parquet({source})"
            ).fetchone()[0]
            
            # Read data
            if use_sampling and sample_size:
                df = conn.execute(
                    f"SELECT * FROM read_parquet({source}) USING SAMPLE {sample_size}"
                ).pl()
            else:
                df = conn.execute(
                    f"SELECT * FROM read_parquet({source})"
                ).pl()
        finally:
            conn.close()
        
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
        
        # Detect partitioned splits
        splits: dict[str, int] = {}
        if len(pq_files) > 1:
            for f in pq_files:
                parts = Path(f.path).parts
                for part in parts:
                    part_lower = part.lower()
                    for split_name in {"train", "test", "val", "validation"}:
                        if split_name in part_lower:
                            if split_name not in splits:
                                splits[split_name] = 0
                            splits[split_name] += 1
            if splits:
                capabilities.add("splits")
        
        return DatasetSchema(
            modality=Modality.TABULAR,
            source_format="parquet",
            root_path=str(root),
            num_samples=total_rows,
            total_size_bytes=total_size,
            splits=splits,
            fields=fields,
            classes=classes,
            capabilities=capabilities,
            analysis_mode=AnalysisMode.SAMPLE if use_sampling else AnalysisMode.FULL,
            sample_size=sample_size if use_sampling else None,
        )


register_loader(ParquetLoader())
