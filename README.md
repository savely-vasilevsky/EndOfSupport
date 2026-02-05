# AWS End-of-Support Tool

A CLI and GUI tool to analyze AWS resource inventory CSV files and generate support status reports with real Excel PivotTables.

## Features

- **Support Status Classification**: Classifies resources as Supported, Approaching End-of-Support, Extended Support, or Out of Support
- **Hierarchical Grouping**: Groups resources by Account → Service → Engine → Version
- **Multiple Output Formats**: Text, CSV, JSON, Excel, and HTML
- **Cross-Platform PivotTable**: Real Excel PivotTables on Windows, Mac, and Linux
- **Pivot Per Account**: Optional separate pivot tables for each AWS account
- **Timeline View**: Visual Gantt-chart style timeline showing support lifecycle events with Service grouping
- **Table of Contents**: Excel reports include a TOC sheet with hyperlinks to all tabs
- **Flexible Filtering**: Filter by status, account, or service
- **Configurable Threshold**: Set custom days threshold for "approaching" status
- **GUI Interface**: Cross-platform graphical interface using tkinter
- **Multiple Date Formats**: Supports various date formats (DD-MMM-YY, DD MMM YYYY, MMM-YY, MMM YYYY)

## Installation

```bash
# Clone the repository
git clone https://github.com/savelyvas/EndOfSupport.git
cd EndOfSupport

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -e .
```

## Usage

### GUI Mode

```bash
# Launch the graphical interface
python -m src.gui
```

The GUI provides:
- File browser for input CSV
- Output format selection (text, csv, json, excel)
- Excel options with pivot method selection
- Status filters (checkboxes)
- Days threshold configuration
- Live preview of results

### CLI Mode

```bash
# Basic usage - outputs to console
python -m src.main inventory.csv

# Generate JSON report
python -m src.main inventory.csv --output-format json --output-file report.json

# Generate Excel report with PivotTable
python -m src.main inventory.csv --output-format excel --output-file report.xlsx

# Generate HTML report (interactive web page)
python -m src.main inventory.csv --output-format html --output-file report.html

# Generate Excel report with per-account pivot tables
python -m src.main inventory.csv --output-format excel --output-file report.xlsx --pivot-per-account

# Generate Excel report without timeline
python -m src.main inventory.csv --output-format excel --output-file report.xlsx --no-timeline

# Filter by status
python -m src.main inventory.csv --status out-of-support --status approaching

# Filter by account and service
python -m src.main inventory.csv --account prod-account --service Lambda

# Custom days threshold (default: 90)
python -m src.main inventory.csv --days-threshold 60
```

## Excel PivotTable Support

The tool creates real, interactive Excel PivotTables with the following hierarchy:
- **Rows**: Service → Engine → Version
- **Values**: Count of Resources
- **Filters**: Account, Days to EOS

### Pivot Generation Methods

| Method | Platform | Description |
|--------|----------|-------------|
| **Windows** | Windows only | Uses Excel COM automation (requires Excel installed) |
| **Cross-platform** | All platforms | Uses template-based approach (works on Mac/Linux) |
| **Auto** | All platforms | Automatically selects the best method for your platform |

In the GUI, select "excel" format to see the Excel Options panel where you can choose the pivot method.

### How Cross-Platform Pivot Works

1. A minimal template file (`src/templates/pivot_template.xlsx`) contains pre-configured pivot metadata
2. When generating a report, the tool copies the pivot structure to your output file
3. The pivot is set to refresh automatically when opened in Excel
4. **First time opening**: Click "Refresh" on the pivot or enable "Refresh data when opening file" in pivot options

## Timeline View

The Timeline sheet provides a visual Gantt-chart style view of support lifecycle events.

### Structure
- **Column A**: Service name (e.g., "Amazon RDS", "Amazon ElastiCache")
- **Column B**: Engine-Version (e.g., "mysql 8.0", "redis 6.2")
- **Column C onwards**: Daily date columns

### Grouping Features
- **Row Grouping**: Rows are grouped by Service - use Excel's +/- controls to expand/collapse
- **Column Grouping**: Time drill-down from Months → Weeks → Days (default: months view)

### Color Coding
| Color | Meaning |
|-------|---------|
| Yellow | Approaching End-of-Support |
| Light Blue | Extended Support period |
| Light Red | Out of Support |
| Red marker | End of Support event |
| Blue marker | Extended Support Start |
| Dark Red marker | Extended Support End |
| Gray | Weekend |
| Gold border | Today |

### Navigation
- Frozen panes keep Service/Engine-Version columns and header rows visible while scrolling
- Legend at bottom explains all color codes

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
- **Table of Contents**: First sheet with hyperlinks to all other sheets
- **Support Status Report**: Data sheet with all resources
- **Pivot Table**: Interactive pivot with Service → Engine → Version hierarchy
- **Timeline View**: Visual timeline showing support events grouped by Service → Engine-Version
- **Per-Account Pivots**: Optional separate pivot for each AWS account
- Color-coded status rows:
  - 🟢 Green: Supported
  - 🟡 Yellow: Approaching End-of-Support
  - 🔵 Blue: Extended Support
  - 🔴 Red: Out of Support
- Auto-filters on data sheet

### HTML
Interactive web-based report with:
- **Summary Dashboard**: Visual cards showing resource counts by status
- **Charts**: Stacked bar charts by service/account, pie charts for distribution
- **Searchable Data Table**: All resources with search, sort, and export (CSV/Excel)
- **Timeline Visualization**: Support events sorted by end-of-support date
- **By Service Breakdown**: Collapsible sections showing resources per service
- Works offline - all dependencies loaded from CDN
- Responsive design for desktop and mobile

## Documentation

### User Guides

- **[USERGUIDE.md](USERGUIDE.md)** - Text user guide
- **[docs/USERGUIDE.html](docs/USERGUIDE.html)** - Visual HTML guide with 40 screenshots
  - Access from GUI: Press **F1** or click **Help** button
  - Open directly: `start docs/USERGUIDE.html` (Windows) or `open docs/USERGUIDE.html` (Mac)

### Generating Documentation

To regenerate the HTML user guide with screenshots:

```bash
# One command - fully automated (captures screenshots, updates markdown, generates HTML)
python generate_userguide.py

# Or use the batch file (Windows)
generate_userguide.bat

# Skip screenshot capture (use existing screenshots)
python generate_userguide.py --skip-screenshots

# Step by step
python tests/capture_all_screenshots.py  # 1. Capture screenshots (automated)
python scripts/update_screenshots.py     # 2. Update markdown references
python src/html_userguide_generator.py   # 3. Generate HTML guide
```

**Screenshot Automation:**
- HTML reports: Playwright (browser automation)
- CLI output: PIL/Pillow (text-to-image)
- GUI: PyAutoGUI (desktop automation)
- Excel: win32com (Windows) or placeholders (cross-platform)

See [docs/SCREENSHOT_STATUS.md](docs/SCREENSHOT_STATUS.md) for details.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=src
```

## Building Executables

### Windows

To create a standalone Windows executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller EndOfSupportTool.spec --clean

# Or use the build script
build.bat
```

The executable will be created at `dist/EndOfSupportTool.exe` (~30 MB). It includes all dependencies and can be distributed without requiring Python installation.

### macOS

To create a macOS application bundle:

```bash
# Make the build script executable
chmod +x build_mac.sh

# Run the build script
./build_mac.sh
```

Or manually:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the app bundle
python -m PyInstaller EndOfSupportTool_mac.spec --clean
```

The application will be created at `dist/EndOfSupportTool.app`. You can:
- Run it directly: `open dist/EndOfSupportTool.app`
- Distribute as a zip: `zip -r EndOfSupportTool_mac.zip dist/EndOfSupportTool.app`
- Create a DMG: `hdiutil create -volname EndOfSupportTool -srcfolder dist/EndOfSupportTool.app -ov EndOfSupportTool.dmg`

Note: macOS builds must be created on a Mac. The Windows executable cannot be built on Mac and vice versa.

## Requirements

- Python 3.9+
- openpyxl (for Excel output)
- pywin32 (optional, for native Windows pivot - auto-detected)

## Project Structure

```
EndOfSupportTool/
├── src/
│   ├── __init__.py
│   ├── main.py          # CLI entry point
│   ├── gui.py           # GUI application
│   ├── parser.py        # CSV parser
│   ├── classifier.py    # Support status classifier
│   ├── generator.py     # Report generator
│   ├── models.py        # Data models
│   ├── formatters.py    # Output formatters (Text, CSV, JSON, Excel)
│   └── templates/
│       └── pivot_template.xlsx  # Pivot table template
├── tests/
│   ├── test_csv_parser.py
│   └── test_classifier.py
├── pyproject.toml
└── README.md
```

## License

MIT
