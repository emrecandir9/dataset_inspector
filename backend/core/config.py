"""Dataset Inspector - Configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    """Application configuration."""
    
    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Analysis
    auto_sample_threshold_bytes: int = 1_000_000_000  # 1 GB
    default_sample_size: int = 50_000
    max_image_sample_size: int = 50_000
    image_sample_thresholds: dict[str, int] = {
        "small": 10_000,   # < 10k → analyze all
        "medium": 10_000,  # 10k-100k → sample 10k
        "large": 50_000,   # 100k+ → sample 50k
    }
    
    # Image analysis
    image_extensions: set[str] = {
        ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"
    }
    
    # Tabular
    tabular_extensions: set[str] = {
        ".csv", ".tsv", ".json", ".jsonl", ".parquet", ".pq",
        ".xlsx", ".xls"
    }
    
    # Ignore patterns
    ignore_patterns: set[str] = {
        "__pycache__", ".git", ".svn", ".hg", ".DS_Store",
        "node_modules", "__MACOSX", "Thumbs.db"
    }
    
    # Limits
    max_file_tree_depth: int = 10
    max_files_in_tree: int = 10_000
    max_preview_rows: int = 100
    max_example_images: int = 50
    
    # Duplicate detection
    phash_threshold: int = 8  # hamming distance for near-duplicates


config = Config()
