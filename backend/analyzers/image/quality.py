"""Dataset Inspector - Image quality analyzer (brightness, contrast, blur)."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageStat

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, Finding, Severity


class ImageQualityAnalyzer(Analyzer):
    """Analyzes image quality metrics: brightness, contrast, blur score."""
    
    analyzer_id = "image_quality"
    name = "Image Quality"
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
        
        # Sample for quality analysis (it's expensive)
        sample_paths = file_paths
        max_quality_samples = min(5000, len(file_paths))
        if len(file_paths) > max_quality_samples:
            random.seed(42)
            sample_paths = random.sample(file_paths, max_quality_samples)
        
        brightness_values: list[float] = []
        contrast_values: list[float] = []
        blur_scores: list[float] = []
        quality_data: list[dict[str, Any]] = []
        
        dark_images: list[str] = []
        bright_images: list[str] = []
        blurry_images: list[str] = []
        
        findings: list[Finding] = []
        
        for fp in sample_paths:
            try:
                with Image.open(fp) as img:
                    # Convert to RGB if needed
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    
                    # Resize for faster analysis
                    thumb = img.copy()
                    thumb.thumbnail((256, 256))
                    
                    # Brightness (mean of grayscale)
                    gray = thumb.convert("L")
                    stat = ImageStat.Stat(gray)
                    brightness = stat.mean[0] / 255.0  # Normalize to 0-1
                    brightness_values.append(brightness)
                    
                    # Contrast (std of grayscale)
                    contrast = stat.stddev[0] / 128.0  # Normalize roughly
                    contrast_values.append(contrast)
                    
                    # Blur score (variance of Laplacian approximation)
                    gray_array = np.array(gray, dtype=np.float64)
                    # Simple Laplacian using convolution
                    laplacian = (
                        gray_array[:-2, 1:-1] + gray_array[2:, 1:-1]
                        + gray_array[1:-1, :-2] + gray_array[1:-1, 2:]
                        - 4 * gray_array[1:-1, 1:-1]
                    )
                    blur_score = float(laplacian.var())
                    blur_scores.append(blur_score)
                    
                    name = Path(fp).name
                    
                    quality_data.append({
                        "file": name,
                        "brightness": round(brightness, 3),
                        "contrast": round(contrast, 3),
                        "blur_score": round(blur_score, 1),
                    })
                    
                    # Flag extremes
                    if brightness < 0.15:
                        dark_images.append(name)
                    elif brightness > 0.85:
                        bright_images.append(name)
                    
                    if blur_score < 50:
                        blurry_images.append(name)
                        
            except Exception:
                continue
        
        analyzed = len(brightness_values)
        
        if analyzed == 0:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="error",
                error_message="Could not analyze any images for quality",
            )
        
        # Findings
        dark_pct = len(dark_images) / analyzed * 100
        if dark_pct > 10:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="many_dark_images",
                title=f"{dark_pct:.0f}% extremely dark images",
                message=f"{len(dark_images)} images have very low brightness (< 15%).",
                details={"count": len(dark_images), "examples": dark_images[:10]},
            ))
        
        bright_pct = len(bright_images) / analyzed * 100
        if bright_pct > 10:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="many_bright_images",
                title=f"{bright_pct:.0f}% extremely bright images",
                message=f"{len(bright_images)} images have very high brightness (> 85%).",
                details={"count": len(bright_images), "examples": bright_images[:10]},
            ))
        
        blurry_pct = len(blurry_images) / analyzed * 100
        if blurry_pct > 10:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="many_blurry_images",
                title=f"{blurry_pct:.0f}% potentially blurry images",
                message=f"{len(blurry_images)} images have low sharpness scores.",
                details={"count": len(blurry_images), "examples": blurry_images[:10]},
            ))
        
        # Build histogram data for charts
        charts = [
            {
                "type": "histogram",
                "title": "Brightness Distribution",
                "data": _histogram(brightness_values, 20, "Brightness"),
                "xKey": "bin",
                "yKey": "count",
            },
            {
                "type": "histogram",
                "title": "Contrast Distribution",
                "data": _histogram(contrast_values, 20, "Contrast"),
                "xKey": "bin",
                "yKey": "count",
            },
        ]
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "analyzed": analyzed,
                "brightness_mean": round(float(np.mean(brightness_values)), 3),
                "brightness_std": round(float(np.std(brightness_values)), 3),
                "contrast_mean": round(float(np.mean(contrast_values)), 3),
                "contrast_std": round(float(np.std(contrast_values)), 3),
                "blur_score_mean": round(float(np.mean(blur_scores)), 1),
                "blur_score_std": round(float(np.std(blur_scores)), 1),
                "dark_images": len(dark_images),
                "bright_images": len(bright_images),
                "blurry_images": len(blurry_images),
            },
            findings=findings,
            charts=charts,
        )


def _histogram(values: list[float], bins: int, label: str) -> list[dict]:
    """Compute histogram data."""
    arr = np.array(values)
    counts, edges = np.histogram(arr, bins=bins)
    return [
        {"bin": f"{edges[i]:.2f}", "count": int(counts[i])}
        for i in range(len(counts))
    ]


register_analyzer(ImageQualityAnalyzer())
