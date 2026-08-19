"""Dataset Inspector - Corrupted image detector."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from backend.analyzers.base import Analyzer
from backend.analyzers.registry import register_analyzer
from backend.core.models import AnalyzerResult, DatasetSchema, Finding, Severity


class CorruptedImageAnalyzer(Analyzer):
    """Detects corrupted or unreadable images."""
    
    analyzer_id = "corrupted_images"
    name = "Corrupted Images"
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
        
        corrupted: list[dict[str, str]] = []
        truncated: list[dict[str, str]] = []
        zero_size: list[str] = []
        total_checked = 0
        findings: list[Finding] = []
        
        for fp in file_paths:
            total_checked += 1
            path = Path(fp)
            name = path.name
            
            # Zero-size check
            try:
                if path.stat().st_size == 0:
                    zero_size.append(name)
                    continue
            except OSError:
                corrupted.append({"file": name, "error": "Cannot access file"})
                continue
            
            # Try opening with PIL
            try:
                with Image.open(fp) as img:
                    # Force full decode
                    img.load()
            except (OSError, SyntaxError, ValueError) as e:
                error_msg = str(e)
                if "truncated" in error_msg.lower():
                    truncated.append({"file": name, "error": error_msg})
                else:
                    corrupted.append({"file": name, "error": error_msg})
            except Exception as e:
                corrupted.append({"file": name, "error": str(e)})
        
        total_issues = len(corrupted) + len(truncated) + len(zero_size)
        
        if corrupted:
            findings.append(Finding(
                severity=Severity.ERROR,
                code="corrupted_images",
                title=f"{len(corrupted)} corrupted image(s)",
                message=f"{len(corrupted)} images could not be read or decoded.",
                details={"files": corrupted[:20]},
            ))
        
        if truncated:
            findings.append(Finding(
                severity=Severity.WARNING,
                code="truncated_images",
                title=f"{len(truncated)} truncated image(s)",
                message=f"{len(truncated)} images appear to be truncated (incomplete download or write).",
                details={"files": truncated[:20]},
            ))
        
        if zero_size:
            findings.append(Finding(
                severity=Severity.ERROR,
                code="zero_size_images",
                title=f"{len(zero_size)} zero-byte file(s)",
                message=f"{len(zero_size)} files are empty (0 bytes).",
                details={"files": zero_size[:20]},
            ))
        
        return AnalyzerResult(
            analyzer_id=self.analyzer_id,
            analyzer_name=self.name,
            status="success",
            metrics={
                "total_checked": total_checked,
                "corrupted": len(corrupted),
                "truncated": len(truncated),
                "zero_size": len(zero_size),
                "total_issues": total_issues,
                "healthy_pct": round((total_checked - total_issues) / max(total_checked, 1) * 100, 2),
            },
            findings=findings,
        )


register_analyzer(CorruptedImageAnalyzer())
