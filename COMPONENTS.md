# Software Components and Libraries

This document describes the software components and external libraries used in the AWS End-of-Support Tool.

## Architecture Overview

The tool follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│  ┌─────────────────┐              ┌─────────────────────────┐   │
│  │   CLI (main.py) │              │     GUI (gui.py)        │   │
│  └────────┬────────┘              └────────────┬────────────┘   │
└───────────┼────────────────────────────────────┼────────────────┘
            │                                    │
            ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Processing                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│  │ parser.py   │→ │ classifier.py │→ │   generator.py      │    │
│  │ (CSV Parse) │  │ (Status)      │  │   (Report Build)    │    │
│  └─────────────┘  └──────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Output Formatting                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    formatters.py                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │   │
│  │  │   Text   │ │   CSV    │ │   JSON   │ │   Excel    │  │   │
│  │  │Formatter │ │Formatter │ │Formatter │ │ Formatter  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Data Models (`models.py`)

Defines the data structures used throughout the application:

| Class | Description |
|-------|-------------|
| `Resource` | Represents a single AWS resource with all its attributes |
| `SupportStatus` | Enum for classification states (Supported, Approaching, Extended, Out of Support) |
| `AccountGroup` | Groups resources by AWS account |
| `ServiceGroup` | Groups resources by AWS service |
| `EngineGroup` | Groups resources by engine (e.g., MySQL, PostgreSQL) |
| `VersionGroup` | Groups resources by version |
| `Report` | Top-level container for the complete report |
| `ReportFilters` | Filter criteria for report generation |

### 2. CSV Parser (`parser.py`)

Parses AWS inventory CSV files into structured `Resource` objects.

**Features:**
- Validates required columns
- Handles multiple date formats:
  - `DD-MMM-YY` (e.g., "15-Dec-25")
  - `DD MMM YYYY` (e.g., "30 Jun 2026")
  - `MMM-YY` (e.g., "Dec-25")
  - `MMM YYYY` (e.g., "Nov 2026")
- Handles special values ("Deprecated", "Supported", "Not available")
- UTF-8 encoding with BOM support

### 3. Resource Classifier (`classifier.py`)

Classifies resources into support status categories.

**Classification Logic:**
1. **Out of Support**: Insights contain "deprecated" or "out of support", or EOS date is in the past
2. **Extended Support**: Currently within extended support period
3. **Approaching EOS**: EOS date is within configurable threshold (default: 90 days)
4. **Supported**: All other resources

### 4. Report Generator (`generator.py`)

Builds hierarchical reports from classified resources.

**Features:**
- Groups resources by Account → Service → Engine → Version
- Calculates status counts at each level
- Applies filters (status, account, service)
- Generates summary statistics

### 5. Output Formatters (`formatters.py`)

Converts reports to various output formats:

| Formatter | Output | Features |
|-----------|--------|----------|
| `TextFormatter` | Console text | Hierarchical indentation, status abbreviations |
| `CSVFormatter` | CSV file | Flat table, one row per resource |
| `JSONFormatter` | JSON file | Nested hierarchical structure |
| `ExcelFormatter` | XLSX file | Styled sheets, pivot tables, TOC |

**Excel Formatter Special Features:**
- Table of Contents with hyperlinks
- Color-coded rows by status
- Real pivot tables (Windows COM or template-based)
- Per-account pivot tables
- Auto-adjusted column widths
- Frozen header rows

### 6. CLI Interface (`main.py`)

Command-line interface using `argparse`.

**Arguments:**
- `input_file`: CSV file path
- `--output-format`: text, csv, json, excel
- `--output-file`: Output file path
- `--status`: Filter by status (repeatable)
- `--account`: Filter by account (repeatable)
- `--service`: Filter by service (repeatable)
- `--days-threshold`: Days before EOS to mark as "approaching"
- `--pivot-per-account`: Create separate pivot per account

### 7. GUI Interface (`gui.py`)

Cross-platform graphical interface using tkinter.

**Features:**
- File browser dialogs
- Format selection dropdown
- Excel options panel (pivot method, per-account)
- Status filter checkboxes
- Days threshold spinner
- Progress bar
- Results preview

## External Libraries

### Required Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `openpyxl` | ≥3.1.0 | Excel file creation and manipulation |

### Optional Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `pywin32` | Any | Windows Excel COM automation for native pivot tables |

### Development Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| `pytest` | ≥7.0.0 | Unit testing framework |
| `hypothesis` | ≥6.0.0 | Property-based testing |

## Standard Library Usage

The tool uses these Python standard library modules:

| Module | Purpose |
|--------|---------|
| `argparse` | CLI argument parsing |
| `csv` | CSV file reading |
| `json` | JSON serialization |
| `datetime` | Date parsing and calculations |
| `dataclasses` | Data model definitions |
| `enum` | Status enumeration |
| `pathlib` | File path handling |
| `logging` | Warning and error logging |
| `tkinter` | GUI framework |
| `threading` | Background processing in GUI |
| `abc` | Abstract base classes |
| `io` | String I/O for CSV formatting |
| `os` | File system operations |
| `sys` | System-specific parameters |

## Platform-Specific Features

### Windows
- Native Excel pivot tables via COM automation (`win32com.client`)
- Requires Microsoft Excel installed for COM method

### Mac/Linux
- Template-based pivot tables using `pivot_template.xlsx`
- Pivot refreshes when file is opened in Excel
- No Excel installation required

## File Structure

```
src/
├── __init__.py          # Package initialization
├── main.py              # CLI entry point
├── gui.py               # GUI application
├── parser.py            # CSV parsing
├── classifier.py        # Status classification
├── generator.py         # Report generation
├── models.py            # Data models
├── formatters.py        # Output formatters
└── templates/
    ├── __init__.py      # Templates package
    └── pivot_template.xlsx  # Pivot table template

tests/
├── conftest.py          # Pytest fixtures
├── test_csv_parser.py   # Parser tests
└── test_classifier.py   # Classifier tests
```

## Testing

The project uses a dual testing approach:

1. **Unit Tests**: Specific examples and edge cases
2. **Property-Based Tests**: Universal properties using Hypothesis

Run tests with:
```bash
pytest                    # Run all tests
pytest --cov=src          # With coverage
pytest -v                 # Verbose output
```
