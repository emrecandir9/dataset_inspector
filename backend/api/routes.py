"""Dataset Inspector - API routes."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from backend.core.models import AnalyzeRequest, DatasetReport
from backend.reports.engine import run_analysis
from backend.reports.html_report import export_html
from backend.reports.json_report import export_json
from backend.reports.markdown_report import export_markdown

router = APIRouter(prefix="/api")

# In-memory store for the current report (single-user local tool)
_current_report: Optional[DatasetReport] = None


@router.post("/analyze")
async def analyze_dataset(request: AnalyzeRequest) -> Dict[str, Any]:
    """Start dataset analysis."""
    global _current_report
    
    path = request.path
    
    # Validate path
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
    
    try:
        report = run_analysis(
            dataset_path=path,
            sample_size=request.sample_size,
            force_type=request.force_type,
        )
        _current_report = report
        
        return {"status": "success", "report": report.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_report() -> Dict[str, Any]:
    """Get the current analysis report."""
    if _current_report is None:
        raise HTTPException(status_code=404, detail="No analysis has been run yet")
    
    return {"status": "success", "report": _current_report.model_dump()}


@router.get("/report/export")
async def export_report(
    format: str = Query(default="json", description="Export format: json, html, markdown"),
):
    """Export the current report in the specified format."""
    if _current_report is None:
        raise HTTPException(status_code=404, detail="No analysis has been run yet")
    
    if format == "json":
        content = export_json(_current_report)
        return HTMLResponse(content=content, media_type="application/json")
    elif format == "html":
        content = export_html(_current_report)
        return HTMLResponse(content=content)
    elif format == "markdown":
        content = export_markdown(_current_report)
        return HTMLResponse(content=content, media_type="text/markdown")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


@router.get("/examples")
async def get_examples(
    filter: str = Query(default="random", description="Filter: random, per_class, largest, smallest"),
    limit: int = Query(default=20, ge=1, le=100),
    class_name: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Get example samples."""
    if _current_report is None:
        raise HTTPException(status_code=404, detail="No analysis has been run yet")
    
    examples = _current_report.examples
    
    if filter == "per_class" and class_name:
        examples = [e for e in examples if e.get("label") == class_name]
    
    return {"examples": examples[:limit]}


@router.get("/image")
async def get_image(path: str = Query(..., description="Absolute image path")):
    """Serve a local image file."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Security: only serve from the dataset path
    if _current_report and _current_report.dataset_path:
        dataset_root = os.path.abspath(_current_report.dataset_path)
        requested = os.path.abspath(path)
        if not requested.startswith(dataset_root):
            raise HTTPException(status_code=403, detail="Access denied")
    
    return FileResponse(path)


@router.get("/image/thumbnail")
async def get_thumbnail(
    path: str = Query(..., description="Absolute image path"),
    size: int = Query(default=256, ge=32, le=1024),
) -> Dict[str, str]:
    """Get a base64-encoded thumbnail."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Security check
    if _current_report and _current_report.dataset_path:
        dataset_root = os.path.abspath(_current_report.dataset_path)
        requested = os.path.abspath(path)
        if not requested.startswith(dataset_root):
            raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        from PIL import Image
        import io
        
        with Image.open(path) as img:
            img.thumbnail((size, size))
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80)
            b64 = base64.b64encode(buffer.getvalue()).decode()
            
            return {"data": f"data:image/jpeg;base64,{b64}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
