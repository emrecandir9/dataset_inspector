"""Dataset Inspector - Image Channel Statistics analyzer."""

from __future__ import annotations

import random
from typing import Any

import numpy as np
from PIL import Image

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, Finding, Severity


class ImageChannelStatsAnalyzer(Analyzer):
    """Calculates RGB Mean and Standard Deviation for normalization."""
    
    analyzer_id = "image_channel_stats"
    name = "Channel Statistics (RGB)"
    required_capabilities = {"images"}
    
    def analyze(self, schema: DatasetSchema, data: Any = None) -> AnalyzerResult:
        if not hasattr(schema, "_file_paths") or not schema._file_paths:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="skipped",
                error_message="No image paths available",
            )
        
        # Sample up to 200 images to keep it fast
        sample_paths = schema._file_paths
        if len(sample_paths) > 200:
            random.seed(42)
            sample_paths = random.sample(sample_paths, 200)
            
        r_means, g_means, b_means = [], [], []
        r_stds, g_stds, b_stds = [], [], []
        
        successful_loads = 0
        
        for path in sample_paths:
            try:
                with Image.open(path) as img:
                    img = img.convert("RGB")
                    # Convert to numpy array and scale to 0-1
                    arr = np.array(img) / 255.0
                    
                    # Calculate mean and std per channel
                    # arr shape is (H, W, 3)
                    means = arr.mean(axis=(0, 1))
                    stds = arr.std(axis=(0, 1))
                    
                    r_means.append(means[0])
                    g_means.append(means[1])
                    b_means.append(means[2])
                    
                    r_stds.append(stds[0])
                    g_stds.append(stds[1])
                    b_stds.append(stds[2])
                    
                    successful_loads += 1
            except Exception:
                continue
                
        if successful_loads == 0:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="error",
                error_message="Failed to load any images for channel statistics",
            )
            
        # Average the stats across all images
        final_mean = [
            round(float(np.mean(r_means)), 4),
            round(float(np.mean(g_means)), 4),
            round(float(np.mean(b_means)), 4),
        ]
        
        final_std = [
            round(float(np.mean(r_stds)), 4),
            round(float(np.mean(g_stds)), 4),
            round(float(np.mean(b_stds)), 4),
        ]
        
        metrics = {
            "RGB Mean": f"[{final_mean[0]:.4f}, {final_mean[1]:.4f}, {final_mean[2]:.4f}]",
            "RGB Std": f"[{final_std[0]:.4f}, {final_std[1]:.4f}, {final_std[2]:.4f}]",
            "Images Sampled": successful_loads,
        }
        
        findings = []
        # Check if it deviates significantly from ImageNet defaults
        imagenet_mean = [0.485, 0.456, 0.406]
        diff_mean = sum(abs(a - b) for a, b in zip(final_mean, imagenet_mean))
        if diff_mean > 0.3:
            findings.append(Finding(
                severity=Severity.INFO,
                code="non_standard_rgb",
                title="Non-Standard Distribution",
                message="Dataset RGB means deviate significantly from ImageNet defaults. We recommend using these specific means for normalization in your dataloader."
            ))
        else:
            findings.append(Finding(
                severity=Severity.INFO,
                code="imagenet_like_rgb",
                title="ImageNet-like Distribution",
                message="Dataset RGB means are similar to ImageNet. Default normalization parameters should work well."
            ))

        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics=metrics,
            findings=findings,
            chart_data=None,
        )

register_analyzer(ImageChannelStatsAnalyzer())
