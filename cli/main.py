"""Dataset Inspector - CLI entry point."""

from __future__ import annotations

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from backend.core.models import AnalysisStatus, ProgressUpdate, Severity
from backend.reports.engine import run_analysis
from backend.reports.json_report import export_json
from backend.reports.html_report import export_html
from backend.reports.markdown_report import export_markdown

console = Console()


@click.group()
def cli():
    """Dataset Inspector — Analyze any dataset instantly."""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--report", "-r", type=click.Path(), help="Export report to file")
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "html", "markdown"]),
              default=None, help="Report format (auto-detected from extension)")
@click.option("--sample", "-s", type=int, default=None, help="Sample size")
@click.option("--type", "-t", "force_type", type=str, default=None,
              help="Force dataset type (csv, parquet, image_folder, etc.)")
def analyze(path: str, report: str | None, fmt: str | None, sample: int | None, force_type: str | None):
    """Analyze a dataset directory."""
    console.print()
    console.print(Panel.fit(
        "[bold]Dataset Inspector[/bold]",
        subtitle=path,
        border_style="blue",
    ))
    console.print()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Starting analysis...", total=None)
        
        def on_progress(update: ProgressUpdate):
            progress.update(task, description=f"{update.stage}: {update.message}")
        
        result = run_analysis(
            dataset_path=path,
            sample_size=sample,
            force_type=force_type,
            progress_callback=on_progress,
        )
    
    console.print()
    
    # Display results
    if result.schema:
        s = result.schema
        
        # Overview table
        overview = Table(title="Overview", show_header=False, border_style="dim")
        overview.add_column("Property", style="dim")
        overview.add_column("Value", style="bold")
        
        overview.add_row("Modality", s.modality.value.title())
        overview.add_row("Format", s.source_format)
        overview.add_row("Samples", f"{s.num_samples:,}")
        overview.add_row("Size", _format_bytes(s.total_size_bytes))
        
        if s.fields:
            overview.add_row("Fields", str(len(s.fields)))
        if s.classes:
            overview.add_row("Classes", str(len(s.classes)))
        if s.splits:
            splits_str = ", ".join(f"{k}: {v:,}" for k, v in s.splits.items())
            overview.add_row("Splits", splits_str)
        
        if s.analysis_mode.value == "sample" and s.sample_size:
            overview.add_row("Mode", f"Sampled ({s.sample_size:,} of {s.num_samples:,})")
        
        console.print(overview)
        console.print()
    
    # Health score
    if result.health:
        h = result.health
        color = "green" if h.score >= 80 else "yellow" if h.score >= 60 else "red"
        console.print(Panel.fit(
            f"[bold {color}]{h.score:.0f}[/bold {color}] / 100  ·  Grade [bold]{h.grade}[/bold]"
            f"  ·  {h.num_errors} errors  ·  {h.num_warnings} warnings  ·  {h.num_info} info",
            title="Health Score",
            border_style=color,
        ))
        console.print()
    
    # Findings
    all_findings = []
    for r in result.analyzer_results:
        all_findings.extend(r.findings)
    
    if all_findings:
        findings_table = Table(title="Findings", border_style="dim")
        findings_table.add_column("", width=3)
        findings_table.add_column("Finding", ratio=1)
        
        for f in sorted(all_findings, key=lambda x: {"error": 0, "warning": 1, "info": 2}[x.severity.value]):
            icon = {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}[f.severity.value]
            findings_table.add_row(icon, f"[bold]{f.title}[/bold]\n{f.message}")
        
        console.print(findings_table)
        console.print()
    
    # Analysis duration
    console.print(f"[dim]Analysis completed in {result.analysis_duration_seconds:.1f}s[/dim]")
    console.print()
    
    # Export report if requested
    if report:
        # Auto-detect format from extension
        if fmt is None:
            ext = os.path.splitext(report)[1].lower()
            fmt = {".json": "json", ".html": "html", ".md": "markdown"}.get(ext, "json")
        
        if fmt == "json":
            export_json(result, report)
        elif fmt == "html":
            export_html(result, report)
        elif fmt == "markdown":
            export_markdown(result, report)
        
        console.print(f"[green]Report saved to:[/green] {report}")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
def serve(host: str, port: int):
    """Start the web UI server."""
    import uvicorn
    
    console.print()
    console.print(Panel.fit(
        f"[bold]Dataset Inspector[/bold]\n"
        f"Server running at [blue]http://{host}:{port}[/blue]",
        border_style="blue",
    ))
    console.print()
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=False,
    )


def _format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


if __name__ == "__main__":
    cli()
