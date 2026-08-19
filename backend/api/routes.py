"""Dataset Inspector - API routes."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from backend.core.models import AnalyzeRequest, DatasetReport, ProgressUpdate
from backend.reports.engine import run_analysis
from backend.reports.html_report import export_html
from backend.reports.json_report import export_json
from backend.reports.markdown_report import export_markdown

router = APIRouter(prefix="/api")

# In-memory store for the current report (single-user local tool)
_current_report: Optional[DatasetReport] = None
_jobs: Dict[str, Dict[str, Any]] = {}

def analysis_task(job_id: str, request: AnalyzeRequest):
    try:
        def progress_cb(update: ProgressUpdate):
            _jobs[job_id]["progress"] = update
            
        sample_size = request.sample_size
        if getattr(request, "mode", "sample") == "full":
            sample_size = None  # None disables sampling threshold overrides
            
        report = run_analysis(
            dataset_path=request.path,
            sample_size=sample_size,
            force_type=request.force_type,
            progress_callback=progress_cb
        )
        
        global _current_report
        _current_report = report
        
        _jobs[job_id]["report"] = report
        _jobs[job_id]["status"] = "complete"
    except Exception as e:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = str(e)

@router.post("/analyze")
async def analyze_dataset(request: AnalyzeRequest, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Start dataset analysis as a background job."""
    path = request.path
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
    
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "running",
        "progress": None,
        "report": None,
        "error": None
    }
    
    background_tasks.add_task(analysis_task, job_id, request)
    return {"status": "success", "job_id": job_id}

@router.get("/analyze/progress/{job_id}")
async def analyze_progress(job_id: str):
    """Stream progress updates using Server-Sent Events."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    async def event_generator():
        last_progress = None
        while True:
            job = _jobs.get(job_id)
            if not job:
                break
                
            if job["status"] == "complete":
                yield f"data: {json.dumps({'status': 'complete'})}\n\n"
                break
            elif job["status"] == "error":
                yield f"data: {json.dumps({'status': 'error', 'error': job['error']})}\n\n"
                break
                
            current_progress = job.get("progress")
            if current_progress and current_progress != last_progress:
                last_progress = current_progress
                yield f"data: {current_progress.model_dump_json()}\n\n"
                
            await asyncio.sleep(0.1)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/analyze/result/{job_id}")
async def analyze_result(job_id: str):
    """Get the final report for a completed job."""
    job = _jobs.get(job_id)
    if not job or job["status"] != "complete":
        raise HTTPException(status_code=404, detail="Result not ready or job not found")
    return {"status": "success", "report": job["report"].model_dump()}


@router.get("/report")
async def get_report() -> Dict[str, Any]:
    """Get the current analysis report."""
    if _current_report is None:
        raise HTTPException(status_code=404, detail="No analysis has been run yet")
    
    return {"status": "success", "report": _current_report.model_dump()}


@router.get("/browse")
async def browse_folder() -> Dict[str, Any]:
    """Open a native folder picker and return the absolute path."""
    import subprocess
    import sys
    try:
        if sys.platform == "darwin":
            # macOS native folder picker via AppleScript
            script = '''
            tell application "System Events" to set frontApp to name of first application process whose frontmost is true
            tell application frontApp
                activate
                set myFolder to choose folder
            end tell
            return POSIX path of myFolder
            '''
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0:
                return {"path": result.stdout.strip()}
        else:
            # Fallback for other OS using tkinter
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            path = filedialog.askdirectory()
            if path:
                return {"path": path}
        return {"path": ""}
    except Exception as e:
        return {"path": "", "error": str(e)}


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
