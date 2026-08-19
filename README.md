# Dataset Inspector

A local-first dataset inspection platform that automatically discovers, analyzes, and reports on tabular and image datasets.

## Features

- **Automatic format detection** — Drop a dataset folder, get instant analysis
- **Tabular profiling** — CSV, JSON, JSONL, Parquet, Excel with per-column statistics
- **Image profiling** — Resolution, quality, duplicates, corrupted files
- **Class balance analysis** — Detect imbalance across classification datasets
- **Dataset health score** — Weighted composite quality metric
- **Premium UI** — Apple-inspired dark interface with interactive charts
- **CLI** — Use in pipelines: `dataset-inspector /path/to/data --report report.html`
- **Export** — HTML, JSON, Markdown reports

## Quick Start

```bash
# Install
pip install -e .

# Run UI
dataset-inspector serve

# Or analyze from CLI
dataset-inspector analyze /path/to/dataset
dataset-inspector analyze /path/to/dataset --report report.html
```

## Architecture

```
Dataset Directory → Scanner → Format Detector → Loader → Unified Dataset → Analyzers → Report → UI
```

## Tech Stack

- **Backend**: Python, FastAPI, DuckDB, Polars, Pillow
- **Frontend**: React, TypeScript, Vite, Recharts
