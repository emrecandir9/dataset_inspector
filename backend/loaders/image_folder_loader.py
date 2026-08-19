"""Dataset Inspector - Image folder loader.

Handles image classification folder structures:
  - class_a/*.jpg, class_b/*.jpg  (flat)
  - train/class_a/*.jpg, test/class_b/*.jpg  (with splits)
"""

from __future__ import annotations

import os
from pathlib import Path

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


SPLIT_NAMES = {"train", "training", "test", "testing", "val", "validation", "dev"}


class ImageFolderLoader(DatasetLoader):
    """Loader for image classification folder structures."""
    
    loader_id = "image_folder"
    name = "Image Folder Loader"
    
    def can_load(self, scan: ScanResult) -> DetectionResult | None:
        image_files = [
            f for f in scan.file_list
            if f.extension in config.image_extensions
        ]
        
        if not image_files:
            return None
        
        image_ratio = len(image_files) / max(scan.total_files, 1)
        if image_ratio < 0.5:
            return None
        
        return DetectionResult(
            dataset_type="image_classification",
            modality=Modality.IMAGE,
            confidence=image_ratio * 0.9,
            reason=f"Found {len(image_files)} image files ({image_ratio:.0%})",
            loader_id=self.loader_id,
        )
    
    def load(
        self,
        scan: ScanResult,
        sample_size: int | None = None,
    ) -> DatasetSchema:
        root = Path(scan.root_path)
        
        # Collect all image files
        image_files = [
            f for f in scan.file_list
            if f.extension in config.image_extensions
        ]
        
        if not image_files:
            raise ValueError("No image files found")
        
        total_images = len(image_files)
        total_size = sum(f.size_bytes for f in image_files)
        
        # Detect structure: flat (class dirs at root) or nested (split dirs > class dirs)
        splits: dict[str, int] = {}
        classes: dict[str, int] = {}
        has_splits = False
        
        # Check if top-level dirs are split names
        top_level = set()
        for f in image_files:
            parts = Path(f.path).parts
            if len(parts) >= 1:
                top_level.add(parts[0])
        
        split_dirs = top_level & SPLIT_NAMES
        
        if split_dirs:
            # Structure: split/class/image.jpg
            has_splits = True
            for f in image_files:
                parts = Path(f.path).parts
                if len(parts) >= 3:
                    split_name = parts[0].lower()
                    class_name = parts[1]
                    
                    # Count per split
                    if split_name not in splits:
                        splits[split_name] = 0
                    splits[split_name] += 1
                    
                    # Count per class
                    if class_name not in classes:
                        classes[class_name] = 0
                    classes[class_name] += 1
                elif len(parts) >= 2:
                    split_name = parts[0].lower()
                    if split_name not in splits:
                        splits[split_name] = 0
                    splits[split_name] += 1
        else:
            # Structure: class/image.jpg (no splits)
            for f in image_files:
                parts = Path(f.path).parts
                if len(parts) >= 2:
                    class_name = parts[0]
                    if class_name not in classes:
                        classes[class_name] = 0
                    classes[class_name] += 1
        
        # Build capabilities
        capabilities: set[str] = {"images"}
        if classes:
            capabilities.add("labels")
        if has_splits:
            capabilities.add("splits")
        
        # Build fields
        fields: list[DatasetField] = [
            DatasetField(
                name="image",
                dtype=FieldType.IMAGE,
                nullable=False,
            ),
        ]
        
        if classes:
            fields.append(DatasetField(
                name="label",
                dtype=FieldType.CATEGORICAL,
                nullable=False,
                sample_values=list(classes.keys())[:10],
            ))
        
        # Sampling
        use_sampling = False
        actual_sample_size = None
        
        if sample_size is None:
            if total_images > 100_000:
                actual_sample_size = config.image_sample_thresholds["large"]
                use_sampling = True
            elif total_images > 10_000:
                actual_sample_size = config.image_sample_thresholds["medium"]
                use_sampling = True
        elif sample_size:
            actual_sample_size = sample_size
            use_sampling = total_images > sample_size
        
        schema = DatasetSchema(
            modality=Modality.IMAGE,
            source_format="image_folder",
            root_path=str(root),
            num_samples=total_images,
            total_size_bytes=total_size,
            splits=splits,
            fields=fields,
            classes=classes if classes else None,
            capabilities=capabilities,
            analysis_mode=AnalysisMode.SAMPLE if use_sampling else AnalysisMode.FULL,
            sample_size=actual_sample_size if use_sampling else None,
        )
        
        # Store file paths for image analyzers
        schema._file_paths = [str(root / f.path) for f in image_files]
        
        return schema


register_loader(ImageFolderLoader())
