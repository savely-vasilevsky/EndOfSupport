# AWS End-of-Support Tool - User Guide

Press F1 or click the Help button in the application to view this guide.

## Table of Contents

1. Introduction
2. Getting Started
3. Using the GUI
4. Using the CLI
5. Understanding Support Status
6. Output Formats
7. Excel Reports and Pivot Tables
8. HTML Interactive Reports
9. Filtering Options
10. Troubleshooting
11. FAQ

---

## Introduction

The AWS End-of-Support Tool helps you analyze your AWS resource inventory and identify resources that are approaching or have reached their end-of-support dates.

### Key Benefits

- Proactive Planning: Identify resources needing upgrades before they lose support
- Risk Assessment: See at a glance which resources are out of support
- Executive Reporting: Generate professional Excel reports with pivot tables
- Multi-Account Support: Analyze resources across multiple AWS accounts

---

## Getting Started

### Prerequisites

- Windows, macOS, or Linux
- Python 3.9+ (if running from source)
- Microsoft Excel (optional, for best pivot table experience)

### Installation Options

#### Option 1: Windows Executable (Recommended for Windows users)

1. Download EndOfSupportTool.exe from the releases
2. Double-click to run - no installation required

#### Option 2: Run from Source

```bash
git clone https://github.com/savelyvas/EndOfSupport.git
cd EndOfSupport
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m src.gui
```

---

## Preparing Your Data

### Generate the Input CSV File

Before using this tool, you need to generate the input CSV file using the End-of-Support Script:

**[🔗 Open End-of-Support Script Runner](http://command-center.support.aws.a2z.com/troubleshooting#/script-runner/End-of-Support-Tool_contributionmodelasset_End-of-Support-Tool?_inputParameters=%7B%7D)**

1. Open the link above to access Command Center Script Runner
2. Run the End-of-Support Script for your target accounts
3. Download the generated CSV file
4. Use this CSV file as input for the End-of-Support Tool

---

## Using the GUI

### Main Window Overview

The GUI provides an intuitive interface for generating reports with the following sections:

- Input file selection
- Output format and file selection
- Excel-specific options
- Status filters
- Generate button and results preview

### Step-by-Step Guide

#### Step 1: Select Input File

1. Click the Browse button next to CSV File
2. Navigate to your AWS inventory CSV file
3. Select the file and click Open

#### Step 2: Choose Output Format

Select from the Format dropdown:

- html: Interactive web report (recommended)
- excel: Professional report with pivot tables
- text: Human-readable console output
- csv: Flat table format
- json: Structured data format

#### Step 3: Set Output File

For Excel and HTML formats:

1. Click Browse next to Output File
2. Choose where to save your report
3. Enter a filename

#### Step 4: Configure Excel Options (Excel format only)

When you select excel format, additional options appear:

- Include Pivot Table: Creates an interactive pivot table sheet
- Pivot Method: auto (recommended), windows, or cross-platform
- Create Pivot per Account: Generates separate pivot tabs for each AWS account
- Include Timeline View: Adds a visual timeline sheet showing support events

#### Step 5: Apply Filters (Optional)

Status Filters: Check boxes to include only specific statuses. Leave all unchecked to include all resources.

Days Threshold: Resources within this many days of EOS are marked Approaching. Default is 90 days.

#### Step 6: Generate Report

1. Click Generate Report
2. Watch the progress bar
3. View results in the preview area

#### Step 7: View Results

Results appear in the preview area at the bottom. For Excel/HTML files, the file is saved automatically.

---

## Using the CLI

The command-line interface is ideal for automation and scripting.

### Basic Syntax

```bash
python -m src.main input.csv [options]
```

### Common Examples

View report in console:

```bash
python -m src.main inventory.csv
```

Generate Excel report:

```bash
python -m src.main inventory.csv --output-format excel --output-file report.xlsx
```

Generate HTML report:

```bash
python -m src.main inventory.csv --output-format html --output-file report.html
```

Filter to only out-of-support resources:

```bash
python -m src.main inventory.csv --status out-of-support
```

Custom threshold (60 days instead of 90):

```bash
python -m src.main inventory.csv --days-threshold 60
```

### All CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| --output-format | text, csv, json, excel, html | text |
| --output-file, -o | Path to save output | console |
| --status | Filter by status (can repeat) | all |
| --account | Filter by account name (can repeat) | all |
| --service | Filter by service name (can repeat) | all |
| --days-threshold | Days before EOS to mark approaching | 90 |
| --pivot-per-account | Create pivot per account (excel only) | single |
| --include-timeline | Include timeline visualization (excel) | enabled |
| --no-timeline | Exclude timeline from Excel output | - |

---

## Understanding Support Status

The tool classifies each resource into one of four statuses:

### Supported

- End-of-support date is more than the threshold days away
- Action: No action required

### Approaching End-of-Support

- End-of-support date is within the threshold (default: 90 days)
- Action: Plan upgrades soon

### Extended Support

- Resource is in AWS Extended Support period
- May incur additional costs
- Action: Plan migration to supported version

### Out of Support

- End-of-support date has passed
- No longer receiving security updates
- Action: Immediate action recommended

---

## Output Formats

### Text Format

Best for quick console viewing - displays a formatted table in the terminal.

### CSV Format

Flat table with one row per resource. Ideal for importing into other tools or custom analysis.

### JSON Format

Hierarchical structure preserving groupings - useful for programmatic processing.

### Excel Format

Professional spreadsheet with multiple sheets:

1. Table of Contents - Clickable links to all sheets
2. Support Status Report - All data with color coding
3. Pivot - Interactive pivot table
4. Timeline - Visual timeline of support events
5. Pivot_AccountName - Per-account pivots (if enabled)

### HTML Format

Interactive web-based report with filtering, charts, and data tables.

---

## Excel Reports and Pivot Tables

### Sheet Structure

#### Table of Contents

Lists all sheets with descriptions and clickable links.

#### Support Status Report

Contains all resource data with color-coded rows based on status.

#### Pivot Table

Interactive summary showing:

- Rows: Service, Engine, Version (expandable)
- Values: Count of resources
- Filters: Account, Days to EOS

#### Timeline View

Visual Gantt-chart style timeline with:

- Row grouping by Service
- Column grouping: Months, Weeks, Days
- Color-coded periods and event markers
- Frozen panes for easy navigation

Color Coding:

- Yellow: Approaching End-of-Support
- Light Blue: Extended Support period
- Light Red: Out of Support period
- Red marker: End of Support event
- Blue marker: Extended Support Start
- Dark Red marker: Extended Support End
- Gray: Weekend
- Gold border: Today

### Working with Pivot Tables

Expanding/Collapsing: Click the +/- buttons next to Service names or double-click a cell to drill down.

Filtering: Use the dropdown arrows in filter area to select specific accounts or date ranges.

Refreshing Data: Right-click pivot then Refresh, or use PivotTable Analyze then Refresh.

---

## HTML Interactive Reports

The HTML format creates a fully interactive web-based report.

### Key Features

#### Filter Bar

Multi-select filters at the top for Service, Account, and Status. Click Apply Filters to filter ALL data including charts, timeline, and tables. Click Reset All to restore defaults.

#### Summary Dashboard

Visual cards showing resource counts with gradient backgrounds. Click any card to view matching resources (respects current filters). Hover to see service breakdown tooltip with filtered counts.

#### Status Breakdown Charts

- Stacked bar chart by Service
- Stacked bar chart by Account
- Doughnut chart for status distribution
- Pie chart for resources by service
- Click any chart segment to view resources (respects current filters)
- All charts update when filters are applied

#### All Resources Table

Interactive DataTable with search, sortable columns, pagination, and export buttons (Copy, CSV, Excel). Includes ARN column with truncated display and full ARN tooltip on hover. Version Details column links to service detail cards.

#### Timeline View

Stacked bar chart by EOS month with scrollable list of upcoming events. Click chart bars to view resources for that month (respects current filters). Chart and list update when filters are applied.

#### Version Details by Service

Accordion-style cards for each Service+Engine combination showing version breakdown, resource counts, and status summary. Expand/Collapse All buttons available. Cards filtered based on Service filter selection.

#### By Service Breakdown

Collapsible accordion sections with paginated tables per service.

#### Navigation

Sticky menu bar with section links (including Version Details), smooth scroll, and go-to-top button.

---

## Filtering Options

### Status Filters

Filter to show only specific support statuses.

### Days Threshold

Controls when resources are marked Approaching EOS. Default is 90 days. Lower value means fewer resources marked as approaching, higher value means more advance warning.

### Account/Service Filters (CLI only)

Single account:

```bash
python -m src.main data.csv --account "Production"
```

Multiple accounts:

```bash
python -m src.main data.csv --account "Prod" --account "Dev"
```

Filter by service:

```bash
python -m src.main data.csv --service "RDS" --service "Lambda"
```

---

## Troubleshooting

### Common Issues

#### CSV Parse Error

- Cause: CSV file format does not match expected columns
- Solution: Verify your CSV has the required columns

#### Excel output requires openpyxl

- Cause: openpyxl library not installed
- Solution: Run the following command:

```bash
pip install openpyxl
```

#### Pivot table is empty

- Cause: Pivot needs to refresh after opening
- Solution: Right-click pivot then Refresh

#### Windows method not available

- Cause: Excel not installed or pywin32 not available
- Solution: Use cross-platform pivot method instead

#### Dates not parsing correctly

- Cause: Unsupported date format
- Supported formats: DD-MMM-YY, DD MMM YYYY, MMM-YY, MMM YYYY

---

## FAQ

Q: Can I analyze multiple CSV files at once?
A: Currently, the tool processes one file at a time. Combine your CSVs first, or run the tool multiple times.

Q: How do I automate report generation?
A: Use the CLI with a batch script or scheduled task.

Q: Why are some resources showing Unknown status?
A: The resource may be missing an End-of-Support date in the CSV, or the date format is not recognized.

Q: Can I customize the Excel colors?
A: Not through the UI, but you can modify STATUS_COLORS in formatters.py.

Q: Does the tool send data anywhere?
A: No. All processing is done locally. No data is transmitted over the network.

Q: What is the difference between Extended Support and Out of Support?
A: Extended Support means AWS still provides updates but may charge extra. Out of Support means no updates are available.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| F1 | Open this help guide |
| Ctrl+O | Browse for input file |
| Ctrl+S | Browse for output file |
| Enter | Generate Report (when input is focused) |

---

Last updated: February 2026
