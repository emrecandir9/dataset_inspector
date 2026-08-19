"""Dataset Inspector - JSON report exporter."""

from __future__ import annotations

import json
from pathlib import Path

from backend.core.models import DatasetReport


def export_json(report: DatasetReport, output_path: str | None = None) -> str:
    """Export report as JSON.
    
    Args:
        report: The complete dataset report.
        output_path: Optional path to save the JSON file.
        
    Returns:
        JSON string.
    """
    json_str = report.model_dump_json(indent=2)
    
    if output_path:
        Path(output_path).write_text(json_str)
    
    return json_str
