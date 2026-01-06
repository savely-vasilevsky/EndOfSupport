# AWS End-of-Support Tool

A CLI tool to analyze AWS resource inventory CSV files and generate support status reports.

## Features

- **Support Status Classification**: Classifies resources as Supported, Approaching End-of-Support, Extended Support, or Out of Support
- **Hierarchical Grouping**: Groups resources by Account → Service → Engine → Version
- **Multiple Output Formats**: Text, CSV, JSON, and Excel
- **Excel with PivotTable**: Excel output includes a real interactive PivotTable (Windows only)
- **Flexible Filtering**: Filter by status, account, or service
- **Configurable Threshold**: Set custom days threshold for "approaching" status

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/EndOfSupportTool.git
cd EndOfSupportTool

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -e .
```

## Usage

```bash
# Basic usage - outputs to console
python -m src.main inventory.csv

# Generate JSON report
python -m src.main inventory.csv --output-format json --output-file report.json

# Generate Excel report with PivotTable
python -m src.main inventory.csv --output-format excel --output-file report.xlsx

# Filter by status
python -m src.main inventory.csv --status out-of-support --status approaching

# Filter by account and service
python -m src.main inventory.csv --account prod-account --service Lambda

# Custom days threshold (default: 90)
python -m src.main inventory.csv --days-threshold 60
```

## Input CSV Format

The tool expects a CSV file with the following columns:
- Account
- Payer ID
- Service
- Resource Type
- Resource ARN
- Resource Name
- Regions / AZs
- Engine (optional)
- Version
- End-of-Support
- Auto Minor Version Upgrade (optional)
- Extended Support Start (optional)
- Extended Support Year 1 Start (optional)
- Extended Support Year 3 Start (optional)
- Extended Support End (optional)
- Insights

## Output Formats

### Text (default)
Human-readable hierarchical output for console viewing.

### CSV
Flat table format with one row per resource.

### JSON
Nested hierarchical structure preserving the grouping.

### Excel
Professional spreadsheet with:
- Color-coded status rows (green=supported, yellow=approaching, blue=extended, red=out-of-support)
- Auto-filters on data sheet
- Real PivotTable with Service → Engine → Version hierarchy (Windows only)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src
```

## Requirements

- Python 3.10+
- openpyxl (for Excel output)
- pywin32 (optional, for real PivotTable on Windows)

## License

MIT
