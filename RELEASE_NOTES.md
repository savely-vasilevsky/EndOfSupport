# Release Notes - v2.1.0

## 🎉 What's New in v2.1.0

### Version Details Feature (Excel)
- **New "Include Version Details" option** - Creates separate tabs for each Service+Engine combination (e.g., Lambda_python, RDS_mysql)
- **Clickable hyperlinks** - "Version Details" column in Support Status Report links to the relevant service tab
- **Blue tab colors** - Version detail tabs are highlighted with blue color for easy identification
- **Meaningful drill-down text** - When using pivot drill-down, the Version Details column shows "See Lambda_python tab" etc., guiding users to the correct tab
- **Available in GUI and CLI** - New checkbox in GUI, `--include-version-details` flag in CLI

### Improved Logging
- **Detailed logging** - Added comprehensive logging throughout the Excel generation process
- **Better error messages** - Improved error handling and reporting for pivot table creation

### Bug Fixes
- **Fixed pivot table creation** - Resolved issues with win32com Excel automation
- **Fixed launcher imports** - Added missing html_formatter module to launcher.py

---

## Previous Release Notes

## 🎉 What's New in v2.0.0

### Interactive HTML Reports
- **New HTML output format** - Generate professional, interactive web-based reports
- **Filter Bar** - Multi-select filters for Service, Account, and Status with instant filtering
- **Summary Dashboard** - Visual cards showing total resources and status counts
- **Interactive Charts** - Stacked bar charts by Service/Account, doughnut and pie charts
- **Timeline View** - Resources grouped by End-of-Support month with visual chart
- **DataTables** - Searchable, sortable tables with pagination and export (Copy, CSV, Excel)
- **Service Groups** - Collapsible accordion sections with per-service DataTables
- **Navigation** - Sticky menu bar, smooth scroll, go-to-top button
- **Fast Loading** - Non-blocking spinner with progressive/lazy loading for better performance

### GUI Improvements
- **HTML as default format** - HTML is now the first and default output option
- **Updated Help** - Comprehensive quick help with all new features documented
- **Smart Filter Defaults** - "Approaching EOS", "Extended Support", and "Out of Support" selected by default
- **Renamed "Supported" to "Regular Support"** - Clearer terminology
- **Faster File Dialogs** - Optimized initial directory selection

### Excel Enhancements
- **Timeline View** - Visual Gantt-style timeline with row/column grouping
- **Pivot Tables** - Cross-platform support with template-based approach
- **Per-Account Pivots** - Optional separate pivot tables for each AWS account

## 📋 Output Formats
- **HTML** - Interactive web report (default)
- **Excel** - Professional spreadsheet with pivot tables, timeline, and version details
- **Text** - Human-readable console output
- **CSV** - Flat table for data analysis
- **JSON** - Structured data for programmatic use

## 🔧 Technical Improvements
- Comprehensive test suite with 240+ tests
- Browser interaction tests using Playwright
- Property-based testing with Hypothesis
- Deferred rendering for large datasets

## 📖 Documentation
- Updated User Guide with HTML format documentation
- Component architecture documentation

---

## 💻 Installation

### Windows
Download `EndOfSupportTool.exe` and run it directly. No installation required.

### macOS
The app is not signed with an Apple Developer certificate. To open:

**Option 1 (Recommended):**
1. Right-click (or Control+click) on `EndOfSupportTool.app` (extract from zip first)
2. Select **"Open"** from the context menu
3. Click **"Open"** in the security dialog

**Option 2:**
1. Try to open the app (it will be blocked)
2. Go to **System Settings** → **Privacy & Security**
3. Scroll down and click **"Open Anyway"** next to the blocked app message
4. Enter your password when prompted
