"""Dataset Inspector - Image resolution analyzer."""

from __future__ import annotations

import random
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, Finding, Severity


class ResolutionAnalyzer(Analyzer):
    """Analyzes image resolution, aspect ratio, and color mode distribution."""
    
    analyzer_id = "image_resolution"
    name = "Image Resolution"
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
        if schema.sample_size and len(file_paths) > schema.sample_size:
            random.seed(42)
            sample_paths = random.sample(file_paths, schema.sample_size)
        
        widths: list[int] = []
        heights: list[int] = []
        resolutions: Counter[str] = Counter()
        aspect_ratios: Counter[str] = Counter()
        color_modes: Counter[str] = Counter()
        file_sizes: list[int] = []
        formats: Counter[str] = Counter()
        findings: list[Finding] = []
        
        very_small: list[str] = []
        very_large: list[str] = []
        
        for fp in sample_paths:
            try:
                path = Path(fp)
                file_sizes.append(path.stat().st_size)
                
                with Image.open(fp) as img:
                    w, h = img.size
                    widths.append(w)
                    heights.append(h)
                    
                    # Resolution bucket
                    res_key = f"{w}×{h}"
                    resolutions[res_key] += 1
                    
                    # Aspect ratio bucket
                    if h > 0:
                        ratio = w / h
                        if abs(ratio - 1.0) < 0.05:
                            ar_key = "1:1"
                        elif abs(ratio - 4/3) < 0.1:
                            ar_key = "4:3"
                        elif abs(ratio - 3/4) < 0.1:
                            ar_key = "3:4"
                        elif abs(ratio - 16/9) < 0.1:
                            ar_key = "16:9"
                        elif abs(ratio - 9/16) < 0.1:
                            ar_key = "9:16"
                        elif abs(ratio - 3/2) < 0.1:
                            ar_key = "3:2"
                        elif abs(ratio - 2/3) < 0.1:
                            ar_key = "2:3"
                        else:
                            ar_key = f"{ratio:.2f}"
                        aspect_ratios[ar_key] += 1
                    
                    # Color mode
                    color_modes[img.mode] += 1
                    
                    # Format
                    if img.format:
                        formats[img.format] += 1
                    
                    # Flag extremes
                    if w < 32 or h < 32:
                        very_small.append(str(path.name))
                    if w > 8000 or h > 8000:
                        very_large.append(str(path.name))
                        
            except Exception:
                continue
        
        analyzed = len(widths)
        
        if analyzed == 0:
            return AnalyzerResult(
                analyzer_id=self.analyzer_id,
                analyzer_name=self.name,
                status="error",
                error_message="Could not analyze any images",
            )
        
        # Findings
        if very_small:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="very_small_images",
                title=f"{len(very_small)} very small images (< 32px)",
                message=f"Found {len(very_small)} images smaller than 32×32 pixels.",
                details={"examples": very_small[:10]},
            ))
        
        if very_large:
            findings.append(Finding(
                severity=Severity.INFO,
                code="very_large_images",
                title=f"{len(very_large)} very large images (> 8000px)",
                message=f"Found {len(very_large)} images larger than 8000×8000 pixels.",
                details={"examples": very_large[:10]},
            ))
        
        # Resolution consistency
        if len(resolutions) == 1:
            findings.append(Finding(
                severity=Severity.INFO,
                code="uniform_resolution",
                title="All images have the same resolution",
                message=f"All {analyzed} images are {list(resolutions.keys())[0]}.",
            ))
        elif len(resolutions) > analyzed * 0.5:
            findings.append(Finding(
                severity=Severity.INFO,
                code="diverse_resolutions",
                title="Highly diverse image resolutions",
                message=f"{len(resolutions)} different resolutions across {analyzed} images.",
            ))
        
        # Mixed color modes
        if len(color_modes) > 1:
            findings.append(Finding(
                severity=Severity.INFO,
                code="mixed_color_modes",
                title="Mixed color modes",
                message=f"Images use {len(color_modes)} different color modes: {', '.join(f'{k} ({v})' for k, v in color_modes.most_common())}.",
            ))
        
        # Top resolutions chart
        top_res = resolutions.most_common(10)
        res_chart = [{"name": r[0], "value": r[1]} for r in top_res]
        
        # Aspect ratio chart
        ar_chart = [{"name": r[0], "value": r[1]} for r in aspect_ratios.most_common(10)]
        
        # Color mode chart
        cm_chart = [{"name": r[0], "value": r[1]} for r in color_modes.most_common()]
        
        import numpy as np
        
        charts = [
            {
                "type": "bar",
                "title": "Top Resolutions",
                "data": res_chart,
                "xKey": "name",
                "yKey": "value",
                "yLabel": "Count",
            },
            {
                "type": "bar",
                "title": "Aspect Ratios",
                "data": ar_chart,
                "xKey": "name",
                "yKey": "value",
                "yLabel": "Count",
            },
            {
                "type": "bar",
                "title": "Color Modes",
                "data": cm_chart,
                "xKey": "name",
                "yKey": "value",
                "yLabel": "Count",
            },
        ]
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "analyzed": analyzed,
                "total": len(file_paths),
                "width_min": min(widths),
                "width_max": max(widths),
                "width_mean": round(sum(widths) / len(widths), 1),
                "height_min": min(heights),
                "height_max": max(heights),
                "height_mean": round(sum(heights) / len(heights), 1),
                "file_size_min": min(file_sizes) if file_sizes else 0,
                "file_size_max": max(file_sizes) if file_sizes else 0,
                "file_size_mean": round(sum(file_sizes) / len(file_sizes)) if file_sizes else 0,
                "unique_resolutions": len(resolutions),
                "top_resolutions": [{"resolution": r[0], "count": r[1]} for r in top_res],
                "aspect_ratios": dict(aspect_ratios.most_common(20)),
                "color_modes": dict(color_modes),
                "formats": dict(formats),
                "very_small_count": len(very_small),
                "very_large_count": len(very_large),
            },
            findings=findings,
            charts=charts,
        )


register_analyzer(ResolutionAnalyzer())
