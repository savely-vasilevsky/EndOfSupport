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

**Step 1: Generate the CSV file using the End-of-Support Script**

Run the End-of-Support Script from Command Center to generate the input CSV file:
- [End-of-Support Script Runner](http://command-center.support.aws.a2z.com/troubleshooting#/script-runner/End-of-Support-Tool_contributionmodelasset_End-of-Support-Tool?_inputParameters=%7B%7D)

**Step 2: Download the generated CSV file**

The script will generate a CSV file with these columns:
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
│  ☑ Include Timeline View                                │
├─────────────────────────────────────────────────────────┤
│  FILTERS                                                │
│  Status Filters: ☐ Supported  ☐ Approaching EOS         │
│                  ☐ Ext Sup Y1 ☐ Ext Sup Y2 ☐ Ext Sup Y3 │
│                  ☐ Out of Support                       │
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
- **Include Timeline View**: Adds a visual timeline sheet showing support events

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

# Generate HTML report
python -m src.main inventory.csv --output-format html --output-file report.html

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
| `--output-format` | text, csv, json, excel, html | text |
| `--output-file`, `-o` | Path to save output (required for excel/html) | (console) |
| `--status` | Filter by status (can repeat) | (all) |
| `--account` | Filter by account name (can repeat) | (all) |
| `--service` | Filter by service name (can repeat) | (all) |
| `--days-threshold` | Days before EOS to mark "approaching" | 90 |
| `--pivot-per-account` | Create pivot per account (excel only) | (single) |
| `--include-timeline` | Include timeline visualization (excel) | enabled |
| `--no-timeline` | Exclude timeline from Excel output | - |

---

## Understanding Support Status

The tool classifies each resource into one of six statuses:

### 🟢 Supported
- End-of-support date is more than the threshold days away
- No action required

### 🟡 Approaching End-of-Support
- End-of-support date is within the threshold (default: 90 days)
- Plan upgrades soon

### 🔵 Extended Support Y1 (Year 1)
- Resource is in the first year of AWS Extended Support
- May incur additional costs
- Plan migration to supported version

### 🔵 Extended Support Y2 (Year 2)
- Resource is in the second year of AWS Extended Support
- Higher costs than Year 1
- Migration should be prioritized

### 🔵 Extended Support Y3 (Year 3)
- Resource is in the third year of AWS Extended Support
- Highest extended support costs
- Immediate migration recommended

### 🔴 Out of Support
- End-of-support date has passed and not in extended support
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
4. **Timeline** - Visual timeline of support events
5. **Pivot_AccountName** - Per-account pivots (if enabled)

### HTML Format
Interactive web-based report that can be opened in any browser. Styled similar to AWS TAM reports.

**Features**:

- **Loading Indicator** - Spinning wheel animation while data loads, automatically hides when ready

- **Filter Bar** - Multi-select filters at the top of the page:
  - **Service Filter**: Select/deselect services to show (all selected by default)
  - **Account Filter**: Select/deselect accounts to show (all selected by default)
  - **Status Filter**: Select/deselect statuses (Supported, Approaching EOS, Extended Support Y1/Y2/Y3, Out of Support)
  - **Apply Filters**: Click to apply selected filters to ALL sections including charts, timeline, and tables
  - **Reset All**: Restore all filters to default (all selected)
  - Filters update: Summary counts, All charts, Resources table, Timeline, By Service section, Version Details

- **Summary Dashboard** - Visual cards showing total resources and status counts with gradient backgrounds
  - Cards update dynamically when filters are applied
  - **Click any card** to open a popup with matching resources (respects current filters)
  - **Hover on cards** to see service breakdown tooltip (shows filtered counts)

- **Status Breakdown Charts**:
  - Stacked bar chart by Service (shows all statuses per service)
  - Stacked bar chart by Account (shows all statuses per account)
  - Doughnut chart for overall status distribution
  - Pie chart for resources by service
  - **Click any chart segment** to view resources (respects current filters)
  - Charts update when filters are applied
  - Collapsible section (click −/+ button)

- **All Resources Table** - Interactive DataTable with:
  - Search/filter across all columns
  - Sortable columns (click headers)
  - Pagination (25 rows per page default)
  - Export buttons: Copy, CSV, Excel
  - Color-coded status badges
  - **ARN column** with truncated display and full ARN tooltip on hover
  - **Version Details column** with links to service detail cards
  - Responds to filter bar selections

- **Timeline View**:
  - Stacked bar chart showing resources by End-of-Support month
  - Color-coded by status (red=Out of Support, blue=Extended, yellow=Approaching, green=Supported)
  - **Click chart bars** to view resources for that month (respects current filters)
  - **Chart updates with filters** - Timeline chart reflects current Service/Account/Status filters
  - Scrollable list of upcoming EOS events with service/engine/version details
  - **List items filtered** - Events list shows/hides based on current filters
  - Date range filter with Apply/Reset buttons
  - Collapsible section

- **Version Details by Service** - Accordion-style cards for each Service+Engine:
  - Summary statistics (total resources, version count, status breakdown)
  - Expand/Collapse All buttons
  - Version detail tables with counts and EOS dates
  - Cards filtered based on Service filter selection

- **By Service Breakdown** - Collapsible accordion sections:
  - Click service header to expand/collapse
  - Shows status badge counts in header (updates with filters)
  - **Paginated DataTable per service** with:
    - 10 rows per page (configurable: 10, 25, 50, All)
    - Search within service
    - Sortable columns
  - Service groups hide when filtered out
  - Resource counts update based on active filters

- **Navigation**:
  - Sticky menu bar with section links (Summary, Status Breakdown, All Resources, Timeline, Version Details, By Service)
  - Smooth scroll to sections when clicking menu links
  - Go-to-top button (appears after scrolling down 300px)
  - Collapsible sections with −/+ buttons

**Using the Filter Bar**:
1. Click filter options to toggle selection (checkmark = selected)
2. Click "Apply Filters" to filter all data
3. Summary cards, ALL charts, timeline, tables, and service groups update accordingly
4. Click "Reset All" to restore all selections

**Chart Click-Through**:
1. Click on any chart segment (bar, pie slice, etc.)
2. A new browser tab opens with matching resources
3. Resources shown respect current page filters
4. The popup includes its own filter bar for further refinement

**Generating HTML Reports**:
```bash
# CLI
python -m src.main inventory.csv --output-format html --output-file report.html

# GUI
1. Select "html" from Format dropdown
2. Click Browse to set output file path
3. Click Generate Report
4. Open the .html file in any browser
```

**Note**: HTML reports require internet connection to load Chart.js and DataTables libraries from CDN. For offline use, the report will still display but charts and advanced table features won't work.

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

#### Timeline View
Visual Gantt-chart style timeline showing support lifecycle events:

**Structure**:
- **Column A (Service)**: AWS service name (e.g., "Amazon RDS", "Amazon ElastiCache", "Amazon EKS")
- **Column B (Engine-Version)**: Engine and version combination (e.g., "mysql 8.0", "redis 6.2")
- **Column C onwards**: Daily columns from today to the furthest future support event

**Row Grouping by Service**:
- Rows are automatically grouped by Service for easy navigation
- Use Excel's outline controls (+/-) on the left side to expand/collapse service groups
- Data is sorted alphabetically by Service, then by Engine-Version within each service
- First row of each service group is always visible; subsequent rows can be collapsed

**Column Grouping (Time Drill-down)**:
- **Months view (default)**: Shows only the first day of each month - collapsed view for high-level overview
- **Weeks view**: Expand to see first day of each week for medium-level detail
- **Days view**: Expand fully to see all individual days for detailed planning
- Use Excel's outline controls (1, 2, 3 buttons at top-left) to expand/collapse time granularity

**Header Rows**:
- Row 1: Year headers (alternating dark blue shades) with merged cells spanning each year
- Row 2: Month headers with vertical text (alternating medium blue shades) for compact display
- Row 3: Week numbers (W1, W2, etc.) with light blue background
- Row 4: Day of week abbreviations (Mon, Tue, Wed, Thu, Fri, Sat, Sun) - horizontal text
- Row 5: Day numbers (1-31)
- Row 6: Column labels ("Service" in A6, "Engine-Version" in B6)

**Color Coding**:
- 🟡 Yellow (`FFEB9C`): Approaching End-of-Support (within threshold days)
- 🔵 Light Blue (`BBDEFB`): Extended Support Year 1
- 🔵 Medium Blue (`90CAF9`): Extended Support Year 2
- 🔵 Dark Blue (`64B5F6`): Extended Support Year 3
- 🔴 Light Red (`FFC7CE`): Out of Support period
- 🔴 Red marker (`FF0000`): End of Support event date
- 🔵 Blue marker (`0070C0`): Extended Support Start date
- 🔴 Dark Red marker (`C00000`): Extended Support End date
- Gray (`F0F0F0`): Weekend days (Saturday/Sunday)
- Gold border (`FFD700`): Today's date marker

**Frozen Panes**:
- Columns A and B (Service and Engine-Version) are frozen - always visible when scrolling horizontally
- Header rows 1-6 are frozen - always visible when scrolling vertically
- Freeze point is at cell C7 (first data cell)
- Scroll through dates while keeping service/engine labels and time headers visible

**Legend**: Color key at the bottom of the timeline explains all color codes with sample cells

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

*Last updated: February 16, 2026 - Version 2.4.1*
