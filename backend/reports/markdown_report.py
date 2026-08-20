"""Dataset Inspector - Markdown report exporter."""

from __future__ import annotations

from pathlib import Path

from backend.core.models import DatasetReport, Severity


def export_markdown(report: DatasetReport, output_path: str | None = None) -> str:
    """Export report as Markdown.
    
    Args:
        report: The complete dataset report.
        output_path: Optional path to save the Markdown file.
        
    Returns:
        Markdown string.
    """
    lines: list[str] = []
    
    lines.append("# Dataset Inspector Report\n")
    lines.append(f"Generated: {report.generated_at}\n")
    lines.append(f"Path: `{report.dataset_path}`\n")
    
    if report.analysis_duration_seconds:
        lines.append(f"Analysis time: {report.analysis_duration_seconds:.1f}s\n")
    
    # Overview
    if report.schema:
        s = report.schema
        lines.append("## Overview\n")
        lines.append(f"| Property | Value |")
        lines.append(f"|----------|-------|")
        lines.append(f"| Modality | {s.modality.value} |")
        lines.append(f"| Format | {s.source_format} |")
        lines.append(f"| Samples | {s.num_samples:,} |")
        lines.append(f"| Size | {_format_bytes(s.total_size_bytes)} |")
        
        if s.fields:
            lines.append(f"| Fields | {len(s.fields)} |")
        if s.classes:
            lines.append(f"| Classes | {len(s.classes)} |")
        if s.splits:
            lines.append(f"| Splits | {', '.join(f'{k}: {v:,}' for k, v in s.splits.items())} |")
        lines.append("")
    
    # Health
    if report.health:
        h = report.health
        lines.append("## Health Score\n")
        lines.append(f"**{h.score:.0f}/100** (Grade: {h.grade})\n")
        lines.append(f"- Errors: {h.num_errors}")
        lines.append(f"- Warnings: {h.num_warnings}")
        lines.append(f"- Info: {h.num_info}\n")
        
        lines.append("### Breakdown\n")
        lines.append("| Category | Score | Weight |")
        lines.append("|----------|-------|--------|")
        for b in h.breakdown:
            lines.append(f"| {b.category} | {b.score:.0f}/100 | {b.weight:.0%} |")
        lines.append("")
    
    # Findings
    all_findings = []
    for r in report.analyzer_results:
        all_findings.extend(r.findings)
    
    if all_findings:
        lines.append("## Findings\n")
        
        errors = [f for f in all_findings if f.severity == Severity.ERROR]
        warnings = [f for f in all_findings if f.severity == Severity.WARNING]
        infos = [f for f in all_findings if f.severity == Severity.INFO]
        
        if errors:
            lines.append("### Errors\n")
            for f in errors:
                lines.append(f"- ❌ **{f.title}** — {f.message}")
            lines.append("")
        
        if warnings:
            lines.append("### Warnings\n")
            for f in warnings:
                lines.append(f"- ⚠️ **{f.title}** — {f.message}")
            lines.append("")
        
        if infos:
            lines.append("### Info\n")
            for f in infos:
                lines.append(f"- ℹ️ **{f.title}** — {f.message}")
            lines.append("")
    
    # Analyzer details
    for r in report.analyzer_results:
        if r.status == "success" and r.metrics:
            lines.append(f"## {r.analyzer_name}\n")
            for key, value in r.metrics.items():
                if not isinstance(value, (list, dict)):
                    lines.append(f"- **{key}**: {value}")
            lines.append("")
            
    # Examples
    if report.examples:
        lines.append("## Examples\n")
        img_examples = [e for e in report.examples if e["type"] == "image"]
        if img_examples:
            lines.append(f"**{len(img_examples)} Image Examples Available** (View in UI to see thumbnails)")
            for ex in img_examples[:5]:
                lines.append(f"- {ex.get('relative_path', ex.get('path'))}")
            lines.append("")
            
        tab_examples = [e for e in report.examples if e["type"] == "tabular"]
        if tab_examples:
            lines.append(f"**{len(tab_examples)} Tabular Examples**")
            cols = list(tab_examples[0]["data"].keys())
            lines.append(f"| {' | '.join(cols)} |")
            lines.append(f"|{'|'.join(['---'] * len(cols))}|")
            for ex in tab_examples[:5]:
                row = [str(ex["data"].get(c, "")) for c in cols]
                lines.append(f"| {' | '.join(row)} |")
            lines.append("")
            
    md = "\n".join(lines)
    
    if output_path:
        Path(output_path).write_text(md)
    
    return md


def _format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
