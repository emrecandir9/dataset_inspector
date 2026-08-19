"""Dataset Inspector - Excel loader."""

from __future__ import annotations

from pathlib import Path

import polars as pl

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


class ExcelLoader(DatasetLoader):
    """Loader for Excel files (.xlsx, .xls)."""
    
    loader_id = "excel"
    name = "Excel Loader"
    
    def can_load(self, scan: ScanResult) -> DetectionResult | None:
        excel_files = [
            f for f in scan.file_list
            if f.extension in {".xlsx", ".xls"}
        ]
        if not excel_files:
            return None
        
        return DetectionResult(
            dataset_type="excel",
            modality=Modality.TABULAR,
            confidence=0.9,
            reason=f"Found {len(excel_files)} Excel file(s)",
            loader_id=self.loader_id,
        )
    
    def load(
        self,
        scan: ScanResult,
        sample_size: int | None = None,
    ) -> DatasetSchema:
        root = Path(scan.root_path)
        
        excel_files = [
            f for f in scan.file_list
            if f.extension in {".xlsx", ".xls"}
        ]
        
        if not excel_files:
            raise ValueError("No Excel files found")
        
        main_file = max(excel_files, key=lambda f: f.size_bytes)
        filepath = root / main_file.path
        
        # Read with Polars (uses openpyxl under the hood)
        df = pl.read_excel(filepath)
        total_rows = len(df)
        
        if sample_size and len(df) > sample_size:
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
            source_format="excel",
            root_path=str(root),
            num_samples=total_rows,
            total_size_bytes=main_file.size_bytes,
            splits={},
            fields=fields,
            classes=classes,
            capabilities=capabilities,
            analysis_mode=AnalysisMode.FULL,
        )


register_loader(ExcelLoader())
