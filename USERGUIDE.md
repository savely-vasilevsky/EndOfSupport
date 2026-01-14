# AWS End-of-Support Tool - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Using the GUI](#using-the-gui)
4. [Using the CLI](#using-the-cli)
5. [Understanding Support Status](#understanding-support-status)
6. [Output Formats](#output-formats)
7. [Excel Reports & Pivot Tables](#excel-reports--pivot-tables)
8. [Filtering Options](#filtering-options)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Introduction

The AWS End-of-Support Tool helps you analyze your AWS resource inventory and identify resources that are approaching or have reached their end-of-support dates. It processes CSV exports from AWS and generates comprehensive reports in multiple formats.

### Key Benefits

- **Proactive Planning**: Identify resources needing upgrades before they lose support
- **Risk Assessment**: See at a glance which resources are out of support
- **Executive Reporting**: Generate professional Excel reports with pivot tables
- **Multi-Account Support**: Analyze resources across multiple AWS accounts

---

## Getting Started

### Prerequisites

- Windows, macOS, or Linux
- Python 3.9+ (if running from source)
- Microsoft Excel (optional, for best pivot table experience)

### Installation Options

**Option 1: Windows Executable (Recommended for Windows users)**
- Download `EndOfSupportTool.exe` from the releases
- Double-click to run - no installation required

**Option 2: Run from Source**
```bash
git clone https://github.com/savelyvas/EndOfSupport.git
cd EndOfSupport
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e .
python -m src.gui       # Launch GUI
```

### Preparing Your Data

Export your AWS resource inventory as a CSV file. The tool expects these columns:
- Account, Payer ID, Service, Resource Type
- Resource ARN, Resource Name, Regions / AZs
- Engine, Version, End-of-Support
- Extended Support dates (optional)
- Insights

---

## Using the GUI

### Main Window Overview

```
┌─────────────────────────────────────────────────────────┐
│  AWS End-of-Support Tool                          [?]   │
├─────────────────────────────────────────────────────────┤
│  INPUT                                                  │
│  CSV File: [________________________] [Browse...]       │
├─────────────────────────────────────────────────────────┤
│  OUTPUT                                                 │
│  Format: [text ▼]                                       │
│  Output File: [____________________] [Browse...]        │
├─────────────────────────────────────────────────────────┤
│  EXCEL OPTIONS (shown when Excel format selected)       │
│  ☑ Include Pivot Table                                  │
│  Pivot Method: [auto ▼] (Will use Windows Excel COM)    │
│  ☐ Create Pivot per Account                             │
├─────────────────────────────────────────────────────────┤
│  FILTERS                                                │
│  Status Filters: ☐ Supported  ☐ Approaching EOS         │
│                  ☐ Extended   ☐ Out of Support          │
│  Days Threshold: [90]                                   │
├─────────────────────────────────────────────────────────┤
│  [Generate Report]  [Clear]                             │
├─────────────────────────────────────────────────────────┤
│  RESULTS / PREVIEW                                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │                                                  │   │
│  │  (Report preview appears here)                   │   │
│  │                                                  │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Ready                                                  │
└─────────────────────────────────────────────────────────┘
```

### Step-by-Step Guide

#### Step 1: Select Input File
1. Click **Browse...** next to "CSV File"
2. Navigate to your AWS inventory CSV file
3. Select the file and click **Open**

#### Step 2: Choose Output Format
Select from the **Format** dropdown:
- **text**: Human-readable console output
- **csv**: Flat table format for spreadsheets
- **json**: Structured data for programmatic use
- **excel**: Professional report with pivot tables

#### Step 3: Set Output File (Optional)
- For **text/csv/json**: Optional - results shown in preview if not set
- For **excel**: Required - click **Browse...** to choose save location

#### Step 4: Configure Excel Options (Excel format only)
When you select "excel" format, additional options appear:

- **Include Pivot Table**: Creates an interactive pivot table sheet
- **Pivot Method**:
  - `auto`: Best method for your platform (recommended)
  - `windows`: Force Windows Excel COM (requires Excel installed)
  - `cross-platform`: Template-based approach (works everywhere)
- **Create Pivot per Account**: Generates separate pivot tabs for each AWS account

#### Step 5: Apply Filters (Optional)
- **Status Filters**: Check boxes to include only specific statuses
  - Leave all unchecked to include all resources
- **Days Threshold**: Resources within this many days of EOS are marked "Approaching"

#### Step 6: Generate Report
1. Click **Generate Report**
2. Watch the progress bar
3. View results in the preview area
4. If output file was specified, the file is saved automatically

---

## Using the CLI

The command-line interface is ideal for automation and scripting.

### Basic Syntax
```bash
python -m src.main <input.csv> [options]
```

### Common Examples

```bash
# View report in console
python -m src.main inventory.csv

# Generate Excel report
python -m src.main inventory.csv --output-format excel --output-file report.xlsx

# Excel with per-account pivots
python -m src.main inventory.csv --output-format excel --output-file report.xlsx --pivot-per-account

# Filter to only out-of-support resources
python -m src.main inventory.csv --status out-of-support

# Custom threshold (60 days instead of 90)
python -m src.main inventory.csv --days-threshold 60

# Filter by account
python -m src.main inventory.csv --account "Production Account"
```

### All CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output-format` | text, csv, json, excel | text |
| `--output-file` | Path to save output | (console) |
| `--status` | Filter by status (can repeat) | (all) |
| `--account` | Filter by account name | (all) |
| `--service` | Filter by service name | (all) |
| `--days-threshold` | Days before EOS to mark "approaching" | 90 |
| `--no-pivot` | Exclude pivot table from Excel | (include) |
| `--pivot-per-account` | Create pivot per account | (single) |

---

## Understanding Support Status

The tool classifies each resource into one of four statuses:

### 🟢 Supported
- End-of-support date is more than the threshold days away
- No action required

### 🟡 Approaching End-of-Support
- End-of-support date is within the threshold (default: 90 days)
- Plan upgrades soon

### 🔵 Extended Support
- Resource is in AWS Extended Support period
- May incur additional costs
- Plan migration to supported version

### 🔴 Out of Support
- End-of-support date has passed
- No longer receiving security updates
- Immediate action recommended

---

## Output Formats

### Text Format
Best for quick console viewing:
```
================================================================================
AWS Resource Support Status Report
Generated: 2026-01-14T20:30:00
================================================================================

SUMMARY
----------------------------------------
Total Resources: 150

Status Breakdown:
  Supported: 80
  Approaching End-of-Support: 25
  Extended Support: 15
  Out of Support: 30
```

### CSV Format
Flat table with one row per resource. Ideal for:
- Importing into other tools
- Custom analysis in Excel/Google Sheets
- Data pipelines

### JSON Format
Hierarchical structure preserving groupings:
```json
{
  "generated_at": "2026-01-14T20:30:00",
  "total_resources": 150,
  "accounts": {
    "Production": {
      "services": { ... }
    }
  }
}
```

### Excel Format
Professional spreadsheet with multiple sheets:
1. **Table of Contents** - Clickable links to all sheets
2. **Support Status Report** - All data with color coding
3. **Pivot** - Interactive pivot table
4. **Pivot_AccountName** - Per-account pivots (if enabled)

---

## Excel Reports & Pivot Tables

### Sheet Structure

#### Table of Contents
- Lists all sheets with descriptions
- Click any sheet name to navigate directly

#### Support Status Report
- Contains all resource data
- Color-coded rows by status
- Auto-filter enabled on all columns
- Frozen header row for easy scrolling

#### Pivot Table
Interactive summary showing:
- **Rows**: Service → Engine → Version (expandable)
- **Values**: Count of resources
- **Filters**: Account, Days to EOS

### Working with Pivot Tables

**Expanding/Collapsing**:
- Click the +/- buttons next to Service names
- Double-click a cell to drill down

**Filtering**:
- Use the dropdown arrows in filter area
- Select specific accounts or date ranges

**Refreshing Data**:
- If data doesn't appear, right-click pivot → Refresh
- Or: PivotTable Analyze → Refresh

### Cross-Platform Pivot Notes

On Mac/Linux (without Excel COM):
1. Pivot is created from a template
2. First time opening: Click "Refresh" on the pivot
3. Or enable "Refresh data when opening file" in pivot options

---

## Filtering Options

### Status Filters
Filter to show only specific support statuses:
- Check one or more status boxes
- Leave all unchecked to show everything

### Days Threshold
Controls when resources are marked "Approaching EOS":
- Default: 90 days
- Lower value = fewer resources marked as approaching
- Higher value = more advance warning

### Account/Service Filters (CLI only)
```bash
# Single account
python -m src.main data.csv --account "Production"

# Multiple accounts
python -m src.main data.csv --account "Prod" --account "Dev"

# Filter by service
python -m src.main data.csv --service "RDS" --service "Lambda"
```

---

## Troubleshooting

### Common Issues

#### "CSV Parse Error"
- **Cause**: CSV file format doesn't match expected columns
- **Solution**: Verify your CSV has the required columns (see Getting Started)

#### "Excel output requires openpyxl"
- **Cause**: openpyxl library not installed
- **Solution**: Run `pip install openpyxl`

#### Pivot table is empty
- **Cause**: Pivot needs to refresh after opening
- **Solution**: Right-click pivot → Refresh, or press Ctrl+Alt+F5

#### "Windows method not available"
- **Cause**: Excel not installed or pywin32 not available
- **Solution**: Use "cross-platform" pivot method instead

#### Dates not parsing correctly
- **Cause**: Unsupported date format
- **Supported formats**:
  - DD-MMM-YY (e.g., 30-Jun-26)
  - DD MMM YYYY (e.g., 30 Jun 2026)
  - MMM-YY (e.g., Jun-26)
  - MMM YYYY (e.g., Jun 2026)

### Getting Help

1. Check this user guide
2. Review the README.md file
3. Open an issue on GitHub

---

## FAQ

**Q: Can I analyze multiple CSV files at once?**
A: Currently, the tool processes one file at a time. Combine your CSVs first, or run the tool multiple times.

**Q: How do I automate report generation?**
A: Use the CLI with a batch script or scheduled task:
```bash
python -m src.main inventory.csv --output-format excel --output-file "report_%date%.xlsx"
```

**Q: Why are some resources showing "Unknown" status?**
A: The resource may be missing an End-of-Support date in the CSV, or the date format isn't recognized.

**Q: Can I customize the Excel colors?**
A: Not through the UI, but you can modify `STATUS_COLORS` in `formatters.py`.

**Q: Does the tool send data anywhere?**
A: No. All processing is done locally. No data is transmitted over the network.

**Q: What's the difference between "Extended Support" and "Out of Support"?**
A: Extended Support means AWS still provides updates but may charge extra. Out of Support means no updates are available.

---

## Keyboard Shortcuts (GUI)

| Shortcut | Action |
|----------|--------|
| Enter | Generate Report (when input is focused) |
| Ctrl+O | Browse for input file |
| Ctrl+S | Browse for output file |
| F1 | Open this help guide |

---

*Last updated: January 2026*
