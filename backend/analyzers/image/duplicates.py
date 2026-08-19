"""Dataset Inspector - Image duplicate detection."""

from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Any

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.config import config
from backend.core.models import AnalyzerResult, DatasetSchema, Finding, Severity


class ImageDuplicateAnalyzer(Analyzer):
    """Detects exact and near-duplicate images using SHA256 and perceptual hashing."""
    
    analyzer_id = "image_duplicates"
    name = "Image Duplicates"
    required_capabilities = {"images"}
    
    def analyze(
        self,
        schema: DatasetSchema,
        data: Any = None,
    ) -> AnalyzerResult:
        file_paths = schema._file_paths
        if not file_paths:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No image file paths available",
            )
        
        # Sample if needed
        sample_paths = file_paths
        max_dup_samples = min(10000, len(file_paths))
        if len(file_paths) > max_dup_samples:
            random.seed(42)
            sample_paths = random.sample(file_paths, max_dup_samples)
        
        findings: list[Finding] = []
        
        # Stage 1: Exact duplicates via SHA256
        hash_to_files: dict[str, list[str]] = {}
        
        for fp in sample_paths:
            try:
                sha = hashlib.sha256()
                with open(fp, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha.update(chunk)
                file_hash = sha.hexdigest()
                
                name = Path(fp).name
                if file_hash not in hash_to_files:
                    hash_to_files[file_hash] = []
                hash_to_files[file_hash].append(name)
            except Exception:
                continue
        
        # Find exact duplicate groups
        exact_groups = {h: files for h, files in hash_to_files.items() if len(files) > 1}
        exact_duplicate_count = sum(len(f) - 1 for f in exact_groups.values())
        
        # Stage 2: Near-duplicates via perceptual hashing
        near_duplicate_pairs: list[dict[str, str]] = []
        
        try:
            import imagehash
            from PIL import Image
            
            phash_to_files: dict[str, list[tuple[str, Any]]] = {}
            
            near_dup_paths = sample_paths[:5000]  # Limit for pHash
            
            for fp in near_dup_paths:
                try:
                    with Image.open(fp) as img:
                        ph = imagehash.phash(img)
                        name = Path(fp).name
                        
                        # Check against existing hashes
                        for existing_hash_str, existing_files in phash_to_files.items():
                            existing_hash = imagehash.hex_to_hash(existing_hash_str)
                            distance = ph - existing_hash
                            if distance <= config.phash_threshold and distance > 0:
                                near_duplicate_pairs.append({
                                    "file_a": existing_files[0][0],
                                    "file_b": name,
                                    "distance": distance,
                                })
                        
                        ph_str = str(ph)
                        if ph_str not in phash_to_files:
                            phash_to_files[ph_str] = []
                        phash_to_files[ph_str].append((name, ph))
                except Exception:
                    continue
        except ImportError:
            # imagehash not available
            pass
        
        # Findings
        if exact_duplicate_count > 0:
            severity = Severity.WARNING if exact_duplicate_count > 10 else Severity.INFO
            findings.append(Finding(
                severity=severity,
                code="exact_duplicates",
                title=f"{exact_duplicate_count} exact duplicate images",
                message=f"Found {len(exact_groups)} groups of identical images ({exact_duplicate_count} duplicates total).",
                details={
                    "groups": [
                        {"files": files, "count": len(files)}
                        for files in list(exact_groups.values())[:10]
                    ]
                },
            ))
        
        if near_duplicate_pairs:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="near_duplicates",
                title=f"{len(near_duplicate_pairs)} near-duplicate image pairs",
                message=f"Found {len(near_duplicate_pairs)} pairs of visually similar images using perceptual hashing.",
                details={
                    "pairs": near_duplicate_pairs[:20],
                },
            ))
        
        # Cross-split duplicate check
        if schema.splits and len(schema.splits) > 1:
            cross_split_dupes = _check_cross_split_duplicates(file_paths, schema)
            if cross_split_dupes:
                findings.append(Finding(
                    severity=Severity.ERROR,
                    code="cross_split_duplicates",
                    title=f"Potential train/test leakage: {cross_split_dupes} duplicates across splits",
                    message=f"{cross_split_dupes} identical images appear in multiple splits. This may cause overly optimistic evaluation results.",
                    details={"count": cross_split_dupes},
                ))
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "analyzed": len(sample_paths),
                "exact_duplicate_groups": len(exact_groups),
                "exact_duplicate_count": exact_duplicate_count,
                "near_duplicate_pairs": len(near_duplicate_pairs),
            },
            findings=findings,
        )


def _check_cross_split_duplicates(file_paths: list[str], schema: DatasetSchema) -> int:
    """Check for duplicate images across train/test/val splits."""
    split_hashes: dict[str, set[str]] = {}
    
    for fp in file_paths:
        parts = Path(fp).relative_to(schema.root_path).parts
        if len(parts) < 2:
            continue
        
        split_name = parts[0].lower()
        if split_name not in {"train", "training", "test", "testing", "val", "validation"}:
            continue
        
        try:
            sha = hashlib.sha256()
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha.update(chunk)
            file_hash = sha.hexdigest()
            
            if split_name not in split_hashes:
                split_hashes[split_name] = set()
            split_hashes[split_name].add(file_hash)
        except Exception:
            continue
    
    # Count overlaps
    cross_dupes = 0
    splits = list(split_hashes.keys())
    for i in range(len(splits)):
        for j in range(i + 1, len(splits)):
            overlap = split_hashes[splits[i]] & split_hashes[splits[j]]
            cross_dupes += len(overlap)
    
    return cross_dupes


register_analyzer(ImageDuplicateAnalyzer())
