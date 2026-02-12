# EndOfSupportTool - Design Document

## Overview

EndOfSupportTool is a Python application that analyzes AWS resource inventory data to identify resources approaching or past their end-of-support dates. It supports multiple input methods (CSV file, AWS API fetch) and generates reports in various formats (Text, CSV, JSON, Excel, HTML).

**Version:** 2.4.0

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EndOfSupportTool                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐   │
│  │   Data Input    │     │   Processing    │     │      Output             │   │
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────────────┤   │
│  │                 │     │                 │     │                         │   │
│  │  ┌───────────┐  │     │  ┌───────────┐  │     │  ┌───────────────────┐  │   │
│  │  │ CSV File  │──┼────▶│  │  Parser   │  │     │  │  Text Formatter   │  │   │
│  │  └───────────┘  │     │  └─────┬─────┘  │     │  └───────────────────┘  │   │
│  │                 │     │        │        │     │                         │   │
│  │  ┌───────────┐  │     │        ▼        │     │  ┌───────────────────┐  │   │
│  │  │ AWS API   │──┼────▶│  ┌───────────┐  │     │  │  CSV Formatter    │  │   │
│  │  │ (Fetch)   │  │     │  │Classifier │  │     │  └───────────────────┘  │   │
│  │  └───────────┘  │     │  │  + Lookup │  │     │                         │   │
│  │                 │     │  └─────┬─────┘  │     │  ┌───────────────────┐  │   │
│  └─────────────────┘     │        │        │     │  │  JSON Formatter   │  │   │
│                          │        ▼        │     │  └───────────────────┘  │   │
│                          │  ┌───────────┐  │     │                         │   │
│                          │  │ Generator │──┼────▶│  ┌───────────────────┐  │   │
│                          │  └───────────┘  │     │  │  Excel Formatter  │  │   │
│                          │                 │     │  │  + Timeline       │  │   │
│                          └─────────────────┘     │  └───────────────────┘  │   │
│                                                  │                         │   │
│                                                  │  ┌───────────────────┐  │   │
│                                                  │  │  HTML Formatter   │  │   │
│                                                  │  │  + Interactive    │  │   │
│                                                  │  └───────────────────┘  │   │
│                                                  │                         │   │
│                                                  └─────────────────────────┘   │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                              User Interfaces                                     │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────────────┐ │
│  │     CLI (main.py)           │    │           GUI (gui.py)                  │ │
│  │  - Command line arguments   │    │  - Step-by-step wizard                  │ │
│  │  - Batch processing         │    │  - AWS fetch integration                │ │
│  │  - Scripting support        │    │  - Filter configuration                 │ │
│  └─────────────────────────────┘    └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  CSV File    │    │   Parser     │    │  Classifier  │    │  Generator   │
│  (Input)     │───▶│  (parser.py) │───▶│(classifier.py)───▶│(generator.py)│
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
                    │  Resource    │    │ SupportStatus│    │   Report     │
                    │  Objects     │    │ + Enrichment │    │   Object     │
                    └──────────────┘    └──────────────┘    └──────────────┘
                                               │                    │
                                               ▼                    ▼
                                        ┌──────────────┐    ┌──────────────┐
                                        │  Extended    │    │  Formatters  │
                                        │  Support     │    │  (Multiple)  │
                                        │  Lookup      │    └──────────────┘
                                        └──────────────┘           │
                                                                   ▼
                                                            ┌──────────────┐
                                                            │   Output     │
                                                            │   Files      │
                                                            └──────────────┘
```

---

## Module Structure

```
src/
├── __init__.py              # Package initialization, version, exports
├── models.py                # Data models (Resource, Report, SupportStatus)
├── parser.py                # CSV parsing and date handling
├── classifier.py            # Support status classification logic
├── extended_support_lookup.py # Static lookup table for extended support dates
├── generator.py             # Report generation with hierarchical grouping
├── formatters.py            # Text, CSV, JSON, Excel formatters + Timeline
├── html_formatter.py        # Interactive HTML report formatter
├── html_userguide_generator.py # HTML user guide generation
├── main.py                  # CLI entry point
└── gui.py                   # Tkinter GUI application

scripts/
├── fetch_aws_resources.py   # AWS API resource fetching
├── extended_support_lookup.py # Extended lookup with cost estimation
├── compare_extended_support_sources.py # Comparison utilities
└── test_extended_support_dates.py # Test suite for lookup

tests/
├── test_classifier.py       # Classifier unit & property tests
├── test_csv_parser.py       # Parser tests
├── test_html_formatter.py   # HTML formatter tests
├── test_html_interaction.py # Playwright browser tests
├── test_timeline_*.py       # Timeline generation tests
└── conftest.py              # Test fixtures and strategies
```

---

## Core Components

### 1. Data Models (`models.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                        SupportStatus (Enum)                      │
├─────────────────────────────────────────────────────────────────┤
│  SUPPORTED              │ Resource is fully supported            │
│  APPROACHING_EOS        │ Within threshold days of EOS           │
│  EXTENDED_SUPPORT_YEAR_1│ In extended support Year 1             │
│  EXTENDED_SUPPORT_YEAR_2│ In extended support Year 2             │
│  EXTENDED_SUPPORT_YEAR_3│ In extended support Year 3             │
│  OUT_OF_SUPPORT         │ Past end-of-support date               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         Resource (Dataclass)                     │
├─────────────────────────────────────────────────────────────────┤
│  account, payer_id, service, resource_type, resource_arn        │
│  resource_name, region, engine, version                         │
│  end_of_support, end_of_support_raw                             │
│  extended_support_start, extended_support_year1/2/3_start       │
│  extended_support_end                                           │
│  status (SupportStatus), days_to_eos                            │
│  instance_type, est_monthly/annual_ext_support_cost             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Report Hierarchy                              │
├─────────────────────────────────────────────────────────────────┤
│  Report                                                          │
│    └── AccountGroup (by AWS account)                            │
│          └── ServiceGroup (by service: Lambda, RDS, EKS...)     │
│                └── EngineGroup (by engine: python, mysql...)    │
│                      └── VersionGroup (by version: 3.9, 8.0...) │
│                            └── Resource[]                        │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Classification Logic (`classifier.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                   Classification Precedence                      │
├─────────────────────────────────────────────────────────────────┤
│  1. Enrich with extended support dates from static lookup       │
│  2. Check if "Deprecated" → OUT_OF_SUPPORT                      │
│  3. Check if Extended Support End < today → OUT_OF_SUPPORT      │
│  4. Check if in Extended Support Year 3 → EXTENDED_SUPPORT_Y3   │
│  5. Check if in Extended Support Year 2 → EXTENDED_SUPPORT_Y2   │
│  6. Check if in Extended Support Year 1 → EXTENDED_SUPPORT_Y1   │
│  7. Check if Insights = "Out of support" → OUT_OF_SUPPORT       │
│  8. Check if EOS date in past → OUT_OF_SUPPORT                  │
│  9. Check if EOS within threshold → APPROACHING_EOS             │
│  10. Default → SUPPORTED                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Extended Support Lookup (`extended_support_lookup.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│              Static Lookup Table Coverage                        │
├─────────────────────────────────────────────────────────────────┤
│  Engine              │ Versions                                  │
│  ────────────────────┼──────────────────────────────────────────│
│  MySQL (RDS)         │ 5.7, 8.0, 8.4                            │
│  PostgreSQL (RDS)    │ 11, 12, 13, 14, 15, 16, 17               │
│  Aurora MySQL        │ 5.7, 8.0                                  │
│  Aurora PostgreSQL   │ 11, 12, 13, 14, 15, 16, 17               │
│  DocumentDB          │ 4.0, 5.0                                  │
│  EKS (Kubernetes)    │ 1.29, 1.30, 1.31, 1.32, 1.33, 1.34, 1.35 │
└─────────────────────────────────────────────────────────────────┘

Each entry contains:
  - standard_support_end
  - extended_support_start
  - extended_support_year1_start
  - extended_support_year3_start (Year 2 is calculated)
  - extended_support_end
```

### 4. Output Formatters

```
┌─────────────────────────────────────────────────────────────────┐
│                      Formatter Classes                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TextFormatter                                                   │
│    └── Plain text hierarchical report                           │
│                                                                  │
│  CSVFormatter                                                    │
│    └── Flat CSV with all resource details                       │
│                                                                  │
│  JSONFormatter                                                   │
│    └── Structured JSON with full hierarchy                      │
│                                                                  │
│  ExcelFormatter                                                  │
│    ├── Table of Contents sheet                                  │
│    ├── Main Report sheet with pivot tables                      │
│    ├── Timeline visualization sheet                             │
│    └── Version Detail sheets (optional)                         │
│                                                                  │
│  HTMLFormatter                                                   │
│    ├── Interactive dashboard with charts                        │
│    ├── Filter bar (status, service, account)                    │
│    ├── DataTables with search/sort/pagination                   │
│    ├── Timeline chart                                           │
│    └── Collapsible sections                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## User Interfaces

### CLI (`main.py`)

```
Usage: eos-tool <input.csv> [options]

Options:
  --output-format    text|csv|json|excel|html (default: text)
  --output-file      Output file path
  --status           Filter by status (can repeat)
  --account          Filter by account (can repeat)
  --service          Filter by service (can repeat)
  --days-threshold   Days for "approaching" (default: 90)
  --pivot-per-account  Separate pivot per account (Excel)
  --include-timeline   Include timeline sheet (Excel, default: true)
  --no-timeline        Exclude timeline sheet
```

### GUI (`gui.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│                    GUI Wizard Steps                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Step 1: Data Source Selection                                  │
│    ○ Load from CSV File                                         │
│      └── Browse for CSV file                                    │
│    ○ Fetch from AWS                                             │
│      ├── AWS Profile (optional)                                 │
│      ├── Regions (comma-separated or all)                       │
│      ├── Parallel Workers                                       │
│      └── Include Extended Support Costs                         │
│                                                                  │
│  Step 2: Output Configuration                                   │
│    ├── Output Format (Text/CSV/JSON/Excel/HTML)                 │
│    ├── Output File Path                                         │
│    ├── Days Threshold                                           │
│    ├── Status Filters (checkboxes)                              │
│    └── Excel Options (pivot, timeline, version details)         │
│                                                                  │
│  [Back] [Generate Report]                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## HTML Report Features

```
┌─────────────────────────────────────────────────────────────────┐
│                   HTML Report Structure                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Navigation Menu (sticky)                                │   │
│  │  [Summary] [Status] [Timeline] [Resources] [Details]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Filter Bar                                              │   │
│  │  [Services ▼] [Accounts ▼] [Status ▼] [Apply] [Reset]   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Summary Dashboard                                       │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       │   │
│  │  │Total│ │ OK  │ │Near │ │ Y1  │ │ Y2  │ │ OOS │       │   │
│  │  │ 20  │ │ 15  │ │  2  │ │  1  │ │  1  │ │  1  │       │   │
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Charts Section                                          │   │
│  │  ┌───────────────┐  ┌───────────────┐                   │   │
│  │  │ Service Chart │  │ Account Chart │                   │   │
│  │  │   (Bar)       │  │   (Bar)       │                   │   │
│  │  └───────────────┘  └───────────────┘                   │   │
│  │  ┌───────────────┐  ┌───────────────┐                   │   │
│  │  │ Status Pie    │  │ Service Pie   │                   │   │
│  │  └───────────────┘  └───────────────┘                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Timeline Chart (Stacked Bar by Month)                   │   │
│  │  [Date Range Filter]                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Resources Table (DataTables)                            │   │
│  │  [Search] [Export] [Pagination]                          │   │
│  │  Account | Service | Engine | Version | Status | ...     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Service Group Details (Collapsible)                     │   │
│  │  ▶ Lambda (17 resources)                                 │   │
│  │  ▶ EKS (2 resources)                                     │   │
│  │  ▶ Aurora (1 resource)                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Excel Report Features

```
┌─────────────────────────────────────────────────────────────────┐
│                   Excel Workbook Structure                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Sheet 1: Table of Contents                                     │
│    └── Hyperlinks to all sheets                                 │
│                                                                  │
│  Sheet 2: Report                                                │
│    ├── Summary section with status counts                       │
│    ├── Pivot table (by Service/Engine/Version)                  │
│    └── Detailed resource list                                   │
│                                                                  │
│  Sheet 3: Timeline                                              │
│    ├── Date headers (Year/Month/Day)                            │
│    ├── Engine-Version rows                                      │
│    ├── Color-coded cells:                                       │
│    │   - Red: End of Support event                              │
│    │   - Blue: Extended Support Start                           │
│    │   - Dark Red: Extended Support End                         │
│    │   - Yellow: Approaching EOS period                         │
│    │   - Light Blue: Extended Support period                    │
│    │   - Light Red: Out of Support period                       │
│    │   - Gray: Weekends                                         │
│    └── Legend                                                   │
│                                                                  │
│  Sheet 4+: Version Details (optional)                           │
│    └── Per Service+Engine breakdown                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Supported AWS Services

| Service | Engine Types | Extended Support |
|---------|--------------|------------------|
| Lambda | python, nodejs, java, dotnet, ruby, go | No |
| RDS | MySQL, PostgreSQL, MariaDB, Oracle, SQL Server | Yes (MySQL, PostgreSQL) |
| Aurora | MySQL, PostgreSQL | Yes |
| EKS | Kubernetes | Yes |
| DocumentDB | MongoDB-compatible | Yes |
| ElastiCache | Redis, Memcached | No |
| OpenSearch | OpenSearch, Elasticsearch | No |
| Neptune | Graph DB | No |
| MSK | Kafka | No |
| Amazon MQ | ActiveMQ, RabbitMQ | No |

---

## Testing Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                      Test Categories                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Unit Tests                                                      │
│    ├── test_classifier.py - Classification logic                │
│    ├── test_csv_parser.py - CSV parsing                         │
│    ├── test_html_formatter.py - HTML generation                 │
│    └── test_engine_version_data.py - Data models                │
│                                                                  │
│  Property-Based Tests (Hypothesis)                              │
│    ├── Classification determinism                               │
│    ├── Out-of-support completeness                              │
│    ├── Approaching EOS threshold correctness                    │
│    └── CSV parsing round-trip                                   │
│                                                                  │
│  Integration Tests                                               │
│    ├── test_timeline_integration.py - Excel timeline            │
│    ├── test_cli_timeline.py - CLI arguments                     │
│    └── test_timeline_generator.py - Timeline generation         │
│                                                                  │
│  Browser Tests (Playwright)                                      │
│    └── test_html_interaction.py                                 │
│        ├── Filter interactions                                  │
│        ├── Chart rendering                                      │
│        ├── DataTable functionality                              │
│        ├── Section collapse/expand                              │
│        └── Navigation                                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration & Build

### Dependencies

```
# Core
python >= 3.9

# Required
openpyxl      # Excel file generation

# Optional (for GUI)
tkinter       # GUI framework (usually bundled with Python)

# Optional (for AWS fetch)
boto3         # AWS SDK

# Development
pytest        # Testing
hypothesis    # Property-based testing
playwright    # Browser testing
```

### Build Commands

```bash
# Install dependencies
pip install -e .

# Run tests
pytest tests/ -v

# Build executable (Windows)
pyinstaller EndOfSupportTool.spec

# Build executable (macOS)
pyinstaller EndOfSupportTool_mac.spec
```

---

## Version History

| Version | Key Features |
|---------|--------------|
| 2.4.0 | Extended support date enrichment from static lookup, EKS support |
| 2.3.x | Extended support cost estimation, star notation for approaching EOS |
| 2.2.x | 6-status classification (Y1/Y2/Y3), HTML interactive report |
| 2.1.x | Timeline visualization, Excel pivot tables |
| 2.0.x | GUI application, AWS fetch integration |
| 1.x | Initial CLI tool with basic classification |

---

## Future Enhancements

1. **Real-time API Integration** - Fetch extended support dates from AWS APIs
2. **Notification System** - Email alerts for approaching EOS
3. **Multi-region Dashboard** - Aggregate view across regions
4. **Cost Optimization** - Recommendations for version upgrades
5. **Compliance Reporting** - Export for audit purposes
