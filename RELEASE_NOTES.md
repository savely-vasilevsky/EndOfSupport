# Release Notes - v2.4.1

## 🎉 What's New in v2.4.1

### Account Filter for Version Details Section
- **Account filter now applies to Version Details** - When filtering by account, the Version Details by Service section now correctly filters rows to show only versions with resources in the selected accounts
- **Dynamic count updates** - Summary counts in card headers and content update when filters are applied
- **Row-level filtering** - Individual version rows are hidden/shown based on account filter

### Resizable Chart Popup Windows
- **Charts open in separate windows** - Clicking the fullscreen button (⛶) now opens charts in a resizable browser popup window
- **Aspect ratio maintained** - Charts maintain their aspect ratio (2:1 for bar charts, 1:1 for pie charts) when the window is resized
- **Theme toggle** - Popup windows include a Dark/Light theme toggle button
- **Data labels toggle** - Show/hide data labels checkbox available in popup

### Chart Click Handler Fix
- **Fixed "No resource found" error** - Chart clicks in By Service and By Account sections now correctly identify the clicked element even when filters are applied

### Bug Fixes
- **Fixed chart label lookup** - Chart onClick handlers now use the chart's current labels instead of static arrays, fixing issues when filters change the displayed data

---

# Release Notes - v2.4.0

## 🎉 What's New in v2.4.0

### Extended Support Date Columns in HTML Report
- **New columns** - Added "Ext. Support Start" and "Ext. Support End" columns to the All Resources table
- **Cost columns** - Added "Est. Monthly Cost" and "Est. Annual Cost" columns with star (*) notation for Approaching EOS status

### Cost Estimation with Star Notation
- **Star (*) indicator** - Costs marked with * indicate future charges that will apply if the component is not upgraded before EOS
- **All formats updated** - Star notation added to CSV, Excel, JSON, Text, and HTML formatters
- **Help documentation** - Added explanation about star notation in GUI Help and HTML report Help guide

### Extended Support Lookup Improvements
- **DocumentDB support** - Fixed version normalization for DocumentDB (4.0, 5.0) in extended support lookup
- **Comprehensive test suite** - Added `test_extended_support_dates.py` script to validate all extended support date fetching

### Bug Fixes
- **Fixed DocumentDB lookup** - DocumentDB versions now correctly resolve in the extended support lookup table

---

# Release Notes - v2.3.1

## 🎉 What's New in v2.3.1

### Extended Support Year Classification (Y1/Y2/Y3)
- **6-status classification system** - Resources are now classified into 6 statuses: Supported, Approaching EOS, Extended Support Y1, Extended Support Y2, Extended Support Y3, and Out of Support
- **Automatic Year 2 calculation** - Year 2 is automatically calculated as the period between Year 1 end and Year 3 start (since CSV doesn't include Year 2 column)
- **Extended support takes precedence** - Resources with extended support dates are correctly classified even if insights say "Out of support"
- **Shortened labels** - Display labels use "Y1", "Y2", "Y3" instead of "Year 1", "Year 2", "Year 3" for cleaner UI

### HTML Report Improvements
- **Horizontal scrolling** - Tables now support horizontal scrolling when content is wider than the viewport
- **Column resizing fixed** - Column resizing no longer triggers table re-sorting
- **Updated filter checkboxes** - GUI filter checkboxes updated for the 3 extended support year statuses

### Excel Report Improvements
- **Pivot table fallback** - If Windows COM pivot creation fails, automatically falls back to cross-platform summary pivot
- **Better error handling** - Pivot creation errors no longer cause the entire report generation to fail

### Bug Fixes
- **Fixed column resize sorting issue** - Resizing columns no longer triggers DataTables sorting
- **Fixed extended support classification** - Resources are now correctly classified into Y1/Y2/Y3 based on dates

---

# Release Notes - v2.3.0

## 🎉 What's New in v2.3.0

### Chart Click-Through Filtering
- **Chart clicks now respect page filters** - When you click on any chart (Service, Account, Status Pie, Service Pie), the popup window now shows only resources that match the current page filters
- **Timeline chart clicks filtered** - Clicking on timeline chart bars now shows only resources matching current filters
- **Summary card clicks filtered** - Clicking on summary dashboard cards (Total, Supported, etc.) now respects active filters
- **Consistent filtering experience** - All interactive elements now work together with the filter bar

### ARN Column in HTML Report
- **New ARN column** - The All Resources table now includes an ARN column between Resource and End of Support
- **Truncated display** - Long ARNs are truncated with ellipsis for cleaner display
- **Full ARN on hover** - Hover over any ARN to see the complete value in a tooltip

### Timeline Chart Filtering Fix
- **Fixed timeline chart not updating** - Resolved issue where the Support Timeline chart wasn't updating when filters were applied
- **Global variable scope fix** - Timeline variables are now properly accessible across script blocks

### Summary Dashboard Tooltip Filtering
- **Filtered tooltip counts** - When hovering on summary cards, the service breakdown tooltip now shows counts based on current filters
- **"(filtered)" indicator** - Tooltip title indicates when showing filtered counts

---

# Release Notes - v2.2.0

## 🎉 What's New in v2.2.0

### Version Details Feature (HTML)
- **New "Version Details by Service" section** - Accordion-style cards for each Service+Engine combination showing version breakdown
- **Clickable links in resources table** - "Version Details" column with links that scroll to the relevant service card
- **Summary statistics per card** - Total resources, version count, and status breakdown for each Service+Engine
- **Expand/Collapse All buttons** - Quickly expand or collapse all version detail cards
- **Version detail tables** - Each card contains a table with Version, Resource Count, EOS dates, and Status Summary

### Enhanced Filter Functionality
- **Filters now update ALL widgets** - When applying filters, all charts (Service, Account, Status Pie, Service Pie) are updated to reflect filtered data
- **Timeline chart filtered** - The Support Timeline chart now updates based on Service and Status filters
- **Timeline list filtered** - The "Upcoming End-of-Support Events" list now shows/hides items based on Service and Status filters
- **Version Details cards filtered** - Service filter now hides/shows version detail cards accordingly
- **Summary cards updated** - Counts in summary cards reflect filtered data
- **Reset restores all** - Reset button now properly restores all charts, timeline, and lists to original state

### Navigation Improvements
- **New "Version Details" menu link** - Quick navigation to the Version Details section from the menu bar

---

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
