"""HTML formatter for EndOfSupportTool.

Generates an interactive HTML report with collapsible sections,
data tables, and charts similar to AWS TAM reports.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Optional

# Handle imports for both package and frozen executable modes
try:
    from .models import Report, Resource, SupportStatus
except ImportError:
    from models import Report, Resource, SupportStatus


class HTMLFormatter:
    """Formats report as an interactive HTML page.
    
    Creates a professional HTML report with:
    - Summary dashboard with status counts
    - Interactive data tables with search/filter
    - Collapsible sections by service
    - Color-coded status indicators
    - Timeline visualization
    """
    
    # Status colors matching the BigID report style
    STATUS_COLORS = {
        SupportStatus.SUPPORTED: ("#c8e6c9", "#1b5e20"),  # (bg, text)
        SupportStatus.APPROACHING_EOS: ("#fff9c4", "#f57f17"),
        SupportStatus.EXTENDED_SUPPORT: ("#bbdefb", "#0d47a1"),
        SupportStatus.OUT_OF_SUPPORT: ("#ffcdd2", "#b71c1c"),
    }
    
    STATUS_LABELS = {
        SupportStatus.SUPPORTED: "Supported",
        SupportStatus.APPROACHING_EOS: "Approaching EOS",
        SupportStatus.EXTENDED_SUPPORT: "Extended Support",
        SupportStatus.OUT_OF_SUPPORT: "Out of Support",
    }

    def format(self, report: Report) -> str:
        """Format the report as an HTML string.
        
        Args:
            report: Report object to format.
            
        Returns:
            Complete HTML document as a string.
        """
        return self._generate_html(report)

    def format_to_file(self, report: Report, filepath: str) -> None:
        """Write the HTML report to a file.
        
        Args:
            report: Report object to format.
            filepath: Path to write the HTML file.
        """
        html_content = self.format(report)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _generate_html(self, report: Report) -> str:
        """Generate the complete HTML document."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS End-of-Support Report - {report.generated_at.strftime('%Y-%m-%d')}</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.11.4/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.2.2/css/buttons.dataTables.min.css">
    {self._get_styles()}
</head>
<body>
    {self._generate_header(report)}
    {self._generate_menu()}
    {self._generate_filter_bar(report)}
    <div class="container">
        {self._generate_summary_section(report)}
        {self._generate_status_breakdown_section(report)}
        {self._generate_resources_table(report)}
        {self._generate_timeline_section(report)}
        {self._generate_by_service_section(report)}
    </div>
    {self._generate_footer()}
    <!-- Load scripts at end for faster initial render -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.11.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.2.2/js/dataTables.buttons.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.2.2/js/buttons.html5.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    {self._generate_scripts(report)}
</body>
</html>"""

    def _get_styles(self) -> str:
        """Return the CSS styles for the report."""
        return """<style>
* {
    box-sizing: border-box;
}

/* Loading spinner - inline in header */
.header-spinner {
    width: 20px;
    height: 20px;
    border: 3px solid rgba(255,255,255,0.3);
    border-top: 3px solid #ff9900;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-left: 15px;
    display: inline-block;
    vertical-align: middle;
}

.header-spinner.hidden {
    display: none;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

body {
    margin: 0;
    padding: 0;
    font-family: "Amazon Ember", "Helvetica Neue", Roboto, Arial, sans-serif;
    font-size: 14px;
    color: #545b64;
    background-color: #f9f9f9;
}

.header {
    background-color: #232f3e;
    color: white;
    padding: 15px 30px;
    display: flex;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.header h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 400;
}

.header .subtitle {
    margin-left: 20px;
    color: #aab7b8;
    font-size: 14px;
}

.header .generation-params {
    margin-left: 20px;
    padding: 4px 12px;
    background: rgba(255, 153, 0, 0.15);
    border-radius: 4px;
    color: #d4a259;
    font-size: 12px;
    max-width: 600px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.header .loading-status {
    margin-left: auto;
    display: flex;
    align-items: center;
    color: #aab7b8;
    font-size: 13px;
}

#menuBar {
    display: flex;
    list-style: none;
    background-color: #f2f2f2;
    padding: 0;
    margin: 0;
    border-bottom: 1px solid #dcdcdc;
    position: sticky;
    top: 0;
    z-index: 100;
}

#menuBar li {
    position: relative;
}

#menuBar li a {
    display: block;
    padding: 12px 20px;
    color: #16191f;
    text-decoration: none;
    font-weight: 500;
}

#menuBar li:hover {
    background-color: #2074d5;
}

#menuBar li:hover a {
    color: white;
}

.container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.section {
    background: white;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 20px;
    padding: 20px;
}

.section h2 {
    color: #ff9900;
    margin-top: 0;
    padding-bottom: 10px;
    border-bottom: 2px solid #ff9900;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.section h2 .collapse-btn {
    cursor: pointer;
    font-size: 18px;
    color: #545b64;
    background: none;
    border: none;
    padding: 5px 10px;
}

.section h2 .collapse-btn:hover {
    color: #ff9900;
}

.summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
}

.summary-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 20px;
    border-radius: 8px;
    text-align: center;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

.summary-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.2);
}

.summary-card.total {
    background: linear-gradient(135deg, #232f3e 0%, #37475a 100%);
}

.summary-card.supported {
    background: linear-gradient(135deg, #43a047 0%, #66bb6a 100%);
}

.summary-card.approaching {
    background: linear-gradient(135deg, #fb8c00 0%, #ffa726 100%);
}

.summary-card.extended {
    background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%);
}

.summary-card.out-of-support {
    background: linear-gradient(135deg, #e53935 0%, #ef5350 100%);
}

.summary-card .count {
    font-size: 36px;
    font-weight: bold;
    margin-bottom: 5px;
}

.summary-card .label {
    font-size: 14px;
    opacity: 0.9;
}

/* Summary card tooltip */
.summary-card-tooltip {
    position: absolute;
    background: rgba(35, 47, 62, 0.95);
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 13px;
    z-index: 1000;
    pointer-events: none;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    max-width: 280px;
    white-space: nowrap;
}

.summary-card-tooltip .tooltip-title {
    font-weight: 600;
    margin-bottom: 8px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255,255,255,0.2);
}

.summary-card-tooltip .tooltip-row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
}

.summary-card-tooltip .tooltip-service {
    margin-right: 20px;
}

.summary-card-tooltip .tooltip-count {
    font-weight: 600;
    color: #ff9900;
}

.summary-card-tooltip .tooltip-more {
    color: #aab7b8;
    font-style: italic;
    margin-top: 6px;
    padding-top: 6px;
    border-top: 1px solid rgba(255,255,255,0.2);
}

.status-supported { background-color: #c8e6c9; color: #1b5e20; }
.status-approaching { background-color: #fff9c4; color: #f57f17; }
.status-extended { background-color: #bbdefb; color: #0d47a1; }
.status-out-of-support { background-color: #ffcdd2; color: #b71c1c; }

.chart-container {
    height: 300px;
    margin: 20px 0;
}

.chart-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

@media (max-width: 900px) {
    .chart-row {
        grid-template-columns: 1fr;
    }
}

table.dataTable {
    width: 100% !important;
    border-collapse: collapse;
}

table.dataTable thead th {
    background-color: #f5f5f5;
    border-bottom: 2px solid #ddd;
    padding: 12px 8px;
    text-align: left;
    font-weight: 600;
}

table.dataTable tbody td {
    padding: 10px 8px;
    border-bottom: 1px solid #eee;
}

table.dataTable tbody tr:hover {
    background-color: #f5f5f5;
}

.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}

.collapsible-content {
    overflow: hidden;
    transition: max-height 0.3s ease-out;
}

.collapsible-content.collapsed {
    max-height: 0 !important;
    padding: 0 !important;
}

.footer {
    text-align: center;
    padding: 20px;
    color: #aab7b8;
    font-size: 12px;
}

.service-group {
    margin-bottom: 15px;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
}

.service-group-header {
    background-color: #f5f5f5;
    padding: 12px 15px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.service-group-header:hover {
    background-color: #eeeeee;
}

.service-group-content {
    padding: 15px;
    display: none;
}

.service-group.expanded .service-group-content {
    display: block;
}

.timeline-bar {
    height: 20px;
    border-radius: 3px;
    margin: 2px 0;
}

.go-to-top {
    position: fixed;
    bottom: 30px;
    right: 30px;
    background-color: #ff9900;
    color: white;
    border: none;
    border-radius: 50%;
    width: 50px;
    height: 50px;
    cursor: pointer;
    font-size: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    display: none;
}

.go-to-top:hover {
    background-color: #ec7211;
}

.search-box {
    margin-bottom: 15px;
}

.search-box input {
    padding: 8px 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    width: 300px;
}

.dt-buttons {
    margin-bottom: 10px;
}

.dt-button {
    background-color: #f5f5f5 !important;
    border: 1px solid #ccc !important;
    border-radius: 4px !important;
    padding: 6px 12px !important;
    margin-right: 5px !important;
}

.dt-button:hover {
    background-color: #e0e0e0 !important;
}

/* Filter bar styles */
.filter-bar {
    background-color: #fff;
    padding: 15px 20px;
    border-bottom: 1px solid #dcdcdc;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.filter-bar .filter-container {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    align-items: flex-start;
}

.filter-bar .filter-group {
    flex: 1;
    min-width: 200px;
}

.filter-bar .filter-group label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: #16191f;
}

.filter-bar .filter-options {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.filter-bar .filter-option {
    display: inline-flex;
    align-items: center;
    padding: 6px 12px;
    background-color: #e8f4fd;
    border: 2px solid #2074d5;
    border-radius: 16px;
    cursor: pointer;
    font-size: 13px;
    transition: all 0.2s;
    user-select: none;
    -webkit-user-select: none;
}

.filter-bar .filter-option:hover {
    background-color: #d0e8fc;
    transform: scale(1.02);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.filter-bar .filter-option.selected {
    background-color: #2074d5;
    color: white;
}

.filter-bar .filter-option input {
    display: none;
}

.filter-bar .filter-option .checkmark {
    margin-right: 6px;
    font-size: 12px;
}

.filter-bar .filter-actions {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    padding-bottom: 2px;
}

.filter-bar .filter-btn {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
}

.filter-bar .apply-btn {
    background-color: #ff9900;
    color: white;
}

.filter-bar .apply-btn:hover {
    background-color: #ec7211;
}

.filter-bar .reset-btn {
    background-color: #f5f5f5;
    color: #545b64;
    border: 1px solid #ccc;
}

.filter-bar .reset-btn:hover {
    background-color: #e0e0e0;
}

.filter-bar .filter-option.status-supported.selected {
    background-color: #43a047;
    border-color: #43a047;
}

.filter-bar .filter-option.status-approaching.selected {
    background-color: #fb8c00;
    border-color: #fb8c00;
}

.filter-bar .filter-option.status-extended.selected {
    background-color: #1976d2;
    border-color: #1976d2;
}

.filter-bar .filter-option.status-out-of-support.selected {
    background-color: #e53935;
    border-color: #e53935;
}

/* Multi-select dropdown styles */
.filter-group-dropdown {
    max-width: 300px;
}

.multi-select-dropdown {
    position: relative;
}

.dropdown-trigger {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    background: white;
    border: 2px solid #2074d5;
    border-radius: 6px;
    cursor: pointer;
    min-width: 200px;
    transition: all 0.2s;
}

.dropdown-trigger:hover {
    background: #f5f9ff;
    border-color: #1565c0;
}

.dropdown-text {
    font-size: 13px;
    color: #16191f;
}

.dropdown-arrow {
    font-size: 10px;
    color: #2074d5;
    transition: transform 0.2s;
}

.multi-select-dropdown.open .dropdown-arrow {
    transform: rotate(180deg);
}

.dropdown-menu {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: white;
    border: 1px solid #ddd;
    border-radius: 6px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 1000;
    margin-top: 4px;
    max-height: 350px;
    overflow: hidden;
}

.multi-select-dropdown.open .dropdown-menu {
    display: block;
}

.dropdown-search {
    padding: 8px;
    border-bottom: 1px solid #eee;
}

.dropdown-search input {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 13px;
}

.dropdown-search input:focus {
    outline: none;
    border-color: #2074d5;
}

.dropdown-actions {
    display: flex;
    gap: 8px;
    padding: 8px;
    border-bottom: 1px solid #eee;
    background: #f9f9f9;
}

.dropdown-actions button {
    flex: 1;
    padding: 6px 10px;
    font-size: 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: white;
    cursor: pointer;
    transition: all 0.2s;
}

.dropdown-actions button:hover {
    background: #2074d5;
    color: white;
    border-color: #2074d5;
}

.dropdown-items {
    max-height: 220px;
    overflow-y: auto;
}

.dropdown-item {
    display: flex;
    align-items: center;
    padding: 10px 12px;
    cursor: pointer;
    transition: background 0.15s;
    border-bottom: 1px solid #f5f5f5;
}

.dropdown-item:hover {
    background: #f5f9ff;
}

.dropdown-item.selected {
    background: #e8f4fd;
}

.dropdown-item .checkbox {
    width: 18px;
    height: 18px;
    border: 2px solid #ccc;
    border-radius: 3px;
    margin-right: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: transparent;
    transition: all 0.15s;
}

.dropdown-item.selected .checkbox {
    background: #2074d5;
    border-color: #2074d5;
    color: white;
}

.dropdown-item .item-text {
    font-size: 13px;
    color: #16191f;
}

.dropdown-item.hidden {
    display: none;
}

/* Lazy loading placeholder */
.chart-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #aab7b8;
    font-size: 14px;
}

@media (max-width: 768px) {
    .filter-bar .filter-container {
        flex-direction: column;
    }
    .filter-bar .filter-group {
        width: 100%;
    }
}
</style>"""

    def _generate_header(self, report: Report) -> str:
        """Generate the page header."""
        # Build parameters display string
        params_html = ""
        if report.generation_params:
            params_str = report.generation_params.to_display_string()
            params_html = f'<div class="generation-params">{params_str}</div>'
        
        return f"""<div class="header">
    <h1>🔧 AWS End-of-Support Report</h1>
    <span class="subtitle">Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
    {params_html}
    <div class="loading-status">
        <span id="loading-text">Loading...</span>
        <div id="header-spinner" class="header-spinner"></div>
    </div>
</div>"""

    def _generate_menu(self) -> str:
        """Generate the navigation menu."""
        return """<ul id="menuBar">
    <li><a href="#summary-section" onclick="scrollToSection(event)">Summary</a></li>
    <li><a href="#status-breakdown" onclick="scrollToSection(event)">Status Breakdown</a></li>
    <li><a href="#resources-table" onclick="scrollToSection(event)">All Resources</a></li>
    <li><a href="#timeline-section" onclick="scrollToSection(event)">Timeline</a></li>
    <li><a href="#by-service-section" onclick="scrollToSection(event)">By Service</a></li>
    <li><a href="#" onclick="showReportHelp(event)" style="color: #ff9900;">Help</a></li>
</ul>
<button class="go-to-top" onclick="window.scrollTo({top: 0, behavior: 'smooth'})">↑</button>"""

    def _generate_filter_bar(self, report: Report) -> str:
        """Generate the filter bar with Service, Account, and Status filters."""
        # Collect unique services and accounts
        services = set()
        accounts = set()
        
        for account_name, account_group in report.accounts.items():
            accounts.add(account_name)
            for service_name in account_group.services.keys():
                services.add(service_name)
        
        # Sort for consistent display
        services = sorted(services)
        accounts = sorted(accounts)
        
        # Generate service filter options (all selected by default)
        service_options = []
        for service in services:
            service_id = self._escape_html(service).replace(' ', '-').replace('.', '-').lower()
            service_options.append(
                f'<label class="filter-option selected" data-filter="service" data-value="{self._escape_html(service)}">'
                f'<input type="checkbox" checked><span class="checkmark">✓</span>{self._escape_html(service)}</label>'
            )
        service_options_html = '\n'.join(service_options)
        
        # Generate account filter options for dropdown (all selected by default)
        account_options = []
        for account in accounts:
            account_options.append(
                f'<div class="dropdown-item selected" data-filter="account" data-value="{self._escape_html(account)}">'
                f'<span class="checkbox">✓</span><span class="item-text">{self._escape_html(account)}</span></div>'
            )
        account_options_html = '\n'.join(account_options)
        account_count = len(accounts)
        
        # Status filter options (all selected by default)
        status_options = f'''
            <label class="filter-option status-supported selected" data-filter="status" data-value="Supported">
                <input type="checkbox" checked><span class="checkmark">✓</span>Supported</label>
            <label class="filter-option status-approaching selected" data-filter="status" data-value="Approaching EOS">
                <input type="checkbox" checked><span class="checkmark">✓</span>Approaching EOS</label>
            <label class="filter-option status-extended selected" data-filter="status" data-value="Extended Support">
                <input type="checkbox" checked><span class="checkmark">✓</span>Extended Support</label>
            <label class="filter-option status-out-of-support selected" data-filter="status" data-value="Out of Support">
                <input type="checkbox" checked><span class="checkmark">✓</span>Out of Support</label>
        '''
        
        return f"""<div class="filter-bar">
    <div class="filter-container">
        <div class="filter-group filter-group-dropdown">
            <label>Account</label>
            <div class="multi-select-dropdown" id="account-dropdown">
                <div class="dropdown-trigger" onclick="toggleAccountDropdown()">
                    <span class="dropdown-text"><span id="account-count">{account_count}</span> of {account_count} selected</span>
                    <span class="dropdown-arrow">▼</span>
                </div>
                <div class="dropdown-menu" id="account-menu">
                    <div class="dropdown-search">
                        <input type="text" placeholder="Search accounts..." id="account-search" oninput="filterAccountOptions()">
                    </div>
                    <div class="dropdown-actions">
                        <button type="button" onclick="selectAllAccounts()">Select All</button>
                        <button type="button" onclick="deselectAllAccounts()">Deselect All</button>
                    </div>
                    <div class="dropdown-items" id="account-items">
                        {account_options_html}
                    </div>
                </div>
            </div>
        </div>
        <div class="filter-group">
            <label>Service</label>
            <div class="filter-options" id="service-filters">
                {service_options_html}
            </div>
        </div>
        <div class="filter-group">
            <label>Status</label>
            <div class="filter-options" id="status-filters">
                {status_options}
            </div>
        </div>
        <div class="filter-actions">
            <button class="filter-btn apply-btn" onclick="applyFilters()">Apply Filters</button>
            <button class="filter-btn reset-btn" onclick="resetFilters()">Reset All</button>
        </div>
    </div>
</div>"""

    def _generate_summary_section(self, report: Report) -> str:
        """Generate the summary dashboard section."""
        status_counts = report.total_counts
        
        return f"""<div id="summary-section" class="section">
    <h2>Summary Dashboard</h2>
    <p style="color: #666; margin-bottom: 15px;"><strong>Click on any card to view affected resources in a new tab. Hover to see breakdown by service.</strong></p>
    <div class="summary-cards">
        <div class="summary-card total" onclick="showAllResources()" onmouseenter="showSummaryTooltip(event, 'total')" onmousemove="positionSummaryTooltip(event)" onmouseleave="hideSummaryTooltip()">
            <div class="count">{report.total_resources}</div>
            <div class="label">Total Resources</div>
        </div>
        <div class="summary-card supported" onclick="showStatusResources('supported')" onmouseenter="showSummaryTooltip(event, 'supported')" onmousemove="positionSummaryTooltip(event)" onmouseleave="hideSummaryTooltip()">
            <div class="count">{status_counts.get(SupportStatus.SUPPORTED, 0)}</div>
            <div class="label">Supported</div>
        </div>
        <div class="summary-card approaching" onclick="showStatusResources('approaching')" onmouseenter="showSummaryTooltip(event, 'approaching')" onmousemove="positionSummaryTooltip(event)" onmouseleave="hideSummaryTooltip()">
            <div class="count">{status_counts.get(SupportStatus.APPROACHING_EOS, 0)}</div>
            <div class="label">Approaching EOS</div>
        </div>
        <div class="summary-card extended" onclick="showStatusResources('extended')" onmouseenter="showSummaryTooltip(event, 'extended')" onmousemove="positionSummaryTooltip(event)" onmouseleave="hideSummaryTooltip()">
            <div class="count">{status_counts.get(SupportStatus.EXTENDED_SUPPORT, 0)}</div>
            <div class="label">Extended Support</div>
        </div>
        <div class="summary-card out-of-support" onclick="showStatusResources('out_of_support')" onmouseenter="showSummaryTooltip(event, 'out_of_support')" onmousemove="positionSummaryTooltip(event)" onmouseleave="hideSummaryTooltip()">
            <div class="count">{status_counts.get(SupportStatus.OUT_OF_SUPPORT, 0)}</div>
            <div class="label">Out of Support</div>
        </div>
    </div>
</div>"""

    def _generate_status_breakdown_section(self, report: Report) -> str:
        """Generate the status breakdown section with charts."""
        # Collect data for charts
        service_data = {}
        account_data = {}
        
        for account_name, account_group in report.accounts.items():
            account_data[account_name] = {
                'supported': 0,
                'approaching': 0,
                'extended': 0,
                'out_of_support': 0
            }
            for service_name, service_group in account_group.services.items():
                if service_name not in service_data:
                    service_data[service_name] = {
                        'supported': 0,
                        'approaching': 0,
                        'extended': 0,
                        'out_of_support': 0
                    }
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        for resource in version_group.resources:
                            status_key = self._status_to_key(resource.status)
                            service_data[service_name][status_key] += 1
                            account_data[account_name][status_key] += 1
        
        return f"""<div id="status-breakdown" class="section">
    <h2>Status Breakdown
        <button class="collapse-btn" onclick="toggleSection('status-breakdown-content')">−</button>
    </h2>
    <div id="status-breakdown-content" class="collapsible-content">
        <p style="color: #666; margin-bottom: 15px;"><strong>Click on any chart element to view affected resources in a new tab.</strong></p>
        <div class="chart-row">
            <div>
                <h3>By Service</h3>
                <div class="chart-container" style="cursor: pointer;">
                    <canvas id="serviceChart"></canvas>
                </div>
            </div>
            <div>
                <h3>By Account</h3>
                <div class="chart-container" style="cursor: pointer;">
                    <canvas id="accountChart"></canvas>
                </div>
            </div>
        </div>
        <div class="chart-row">
            <div>
                <h3>Overall Status Distribution</h3>
                <div class="chart-container" style="cursor: pointer;">
                    <canvas id="statusPieChart"></canvas>
                </div>
            </div>
            <div>
                <h3>Resources by Service</h3>
                <div class="chart-container" style="cursor: pointer;">
                    <canvas id="servicePieChart"></canvas>
                </div>
            </div>
        </div>
    </div>
</div>"""

    def _status_to_key(self, status: SupportStatus) -> str:
        """Convert status enum to dictionary key."""
        mapping = {
            SupportStatus.SUPPORTED: 'supported',
            SupportStatus.APPROACHING_EOS: 'approaching',
            SupportStatus.EXTENDED_SUPPORT: 'extended',
            SupportStatus.OUT_OF_SUPPORT: 'out_of_support'
        }
        return mapping.get(status, 'supported')

    def _generate_resources_table(self, report: Report) -> str:
        """Generate the main resources data table."""
        rows = []
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        for resource in version_group.resources:
                            status_class = self._get_status_class(resource.status)
                            status_label = self.STATUS_LABELS.get(resource.status, "Unknown")
                            eos_date = resource.end_of_support.strftime('%Y-%m-%d') if resource.end_of_support else 'N/A'
                            days_to_eos = resource.days_to_eos if resource.days_to_eos is not None else 'N/A'
                            
                            rows.append(f"""<tr>
                                <td>{self._escape_html(account_name)}</td>
                                <td>{self._escape_html(service_name)}</td>
                                <td>{self._escape_html(engine_name or 'N/A')}</td>
                                <td>{self._escape_html(version_name)}</td>
                                <td>{self._escape_html(resource.resource_name or resource.resource_arn or 'N/A')}</td>
                                <td>{eos_date}</td>
                                <td>{days_to_eos}</td>
                                <td><span class="status-badge {status_class}">{status_label}</span></td>
                            </tr>""")
        
        rows_html = '\n'.join(rows)
        
        return f"""<div id="resources-table" class="section">
    <h2>All Resources
        <button class="collapse-btn" onclick="toggleSection('resources-table-content')">−</button>
    </h2>
    <div id="resources-table-content" class="collapsible-content">
        <table id="resourcesDataTable" class="display">
            <thead>
                <tr>
                    <th>Account</th>
                    <th>Service</th>
                    <th>Engine</th>
                    <th>Version</th>
                    <th>Resource</th>
                    <th>End of Support</th>
                    <th>Days to EOS</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
</div>"""

    def _get_status_class(self, status: SupportStatus) -> str:
        """Get CSS class for status."""
        mapping = {
            SupportStatus.SUPPORTED: 'status-supported',
            SupportStatus.APPROACHING_EOS: 'status-approaching',
            SupportStatus.EXTENDED_SUPPORT: 'status-extended',
            SupportStatus.OUT_OF_SUPPORT: 'status-out-of-support'
        }
        return mapping.get(status, '')

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ''
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#39;'))

    def _generate_timeline_section(self, report: Report) -> str:
        """Generate the timeline visualization section with Chart.js timeline."""
        import json
        from collections import defaultdict
        
        # Collect timeline data grouped by month and status
        monthly_data = defaultdict(lambda: {'supported': 0, 'approaching': 0, 'extended': 0, 'out_of_support': 0})
        # Also collect detailed resources by month for click-through
        monthly_resources = defaultdict(list)
        timeline_items = []
        seen = set()
        
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        for resource in version_group.resources:
                            if resource.end_of_support:
                                # Group by month for chart
                                month_key = resource.end_of_support.strftime('%Y-%m')
                                status_key = self._status_to_key(resource.status)
                                monthly_data[month_key][status_key] += 1
                                
                                # Store detailed resource info for click-through
                                monthly_resources[month_key].append({
                                    'account': account_name,
                                    'service': service_name,
                                    'engine': engine_name or 'N/A',
                                    'version': version_name,
                                    'resource': resource.resource_name or resource.resource_arn or 'N/A',
                                    'eos_date': resource.end_of_support.strftime('%Y-%m-%d'),
                                    'status': status_key
                                })
                                
                                # Collect unique items for list
                                key = (service_name, engine_name or 'N/A', version_name)
                                if key not in seen:
                                    seen.add(key)
                                    timeline_items.append({
                                        'service': service_name,
                                        'engine': engine_name or 'N/A',
                                        'version': version_name,
                                        'eos_date': resource.end_of_support.isoformat(),
                                        'status': status_key
                                    })
        
        # Sort timeline items by EOS date
        timeline_items.sort(key=lambda x: x['eos_date'])
        
        # Sort months and prepare chart data
        sorted_months = sorted(monthly_data.keys())
        
        # Prepare data for Chart.js
        chart_labels = json.dumps(sorted_months)
        chart_supported = json.dumps([monthly_data[m]['supported'] for m in sorted_months])
        chart_approaching = json.dumps([monthly_data[m]['approaching'] for m in sorted_months])
        chart_extended = json.dumps([monthly_data[m]['extended'] for m in sorted_months])
        chart_out_of_support = json.dumps([monthly_data[m]['out_of_support'] for m in sorted_months])
        
        # Prepare detailed resources data for click-through (JSON for JavaScript)
        monthly_resources_json = json.dumps({m: monthly_resources[m] for m in sorted_months})
        
        # Prepare service summary per month for tooltip
        monthly_service_summary = {}
        for month in sorted_months:
            service_counts = defaultdict(int)
            for res in monthly_resources[month]:
                service_counts[res['service']] += 1
            monthly_service_summary[month] = dict(service_counts)
        monthly_service_summary_json = json.dumps(monthly_service_summary)
        
        # Generate timeline list HTML
        timeline_list_html = []
        for item in timeline_items[:100]:  # Limit to 100 items
            status_class = f"status-{item['status'].replace('_', '-')}"
            timeline_list_html.append(f"""
                <div class="timeline-item" style="display: flex; align-items: center; padding: 8px 12px; margin: 4px 0; border-radius: 4px; background-color: #f9f9f9;">
                    <span class="status-badge {status_class}" style="min-width: 120px; text-align: center;">{item['eos_date']}</span>
                    <span style="margin-left: 15px; flex: 1;">
                        <strong>{self._escape_html(item['service'])}</strong> - 
                        {self._escape_html(item['engine'])} {self._escape_html(item['version'])}
                    </span>
                </div>
            """)
        
        timeline_list = '\n'.join(timeline_list_html) if timeline_list_html else '<p>No timeline data available.</p>'
        more_text = f'<p style="color: #666; font-style: italic;">Showing {len(timeline_list_html)} of {len(timeline_items)} unique engine-version combinations</p>' if len(timeline_items) > 100 else ''
        
        # Get min and max dates for the date range inputs
        # Default: earliest date in report to 6 months in the future
        from datetime import datetime
        
        today = datetime.now()
        
        # Calculate 6 months ahead
        year_end = today.year
        month_end = today.month + 6
        while month_end > 12:
            month_end -= 12
            year_end += 1
        default_end = f"{year_end:04d}-{month_end:02d}"
        
        if sorted_months:
            data_min_month = sorted_months[0]
            data_max_month = sorted_months[-1]
            # Start from earliest date in report
            default_start = data_min_month
            # Clamp end to available data range
            if default_end > data_max_month:
                default_end = data_max_month
        else:
            data_min_month = ""
            data_max_month = ""
            default_start = ""
            default_end = ""
        
        return f"""<div id="timeline-section" class="section">
    <h2>Support Timeline
        <button class="collapse-btn" onclick="toggleSection('timeline-content')">−</button>
    </h2>
    <div id="timeline-content" class="collapsible-content">
        <p>End-of-Support events aggregated by month. <strong>Click on a bar to view affected resources in a new tab.</strong></p>
        <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 15px; padding: 12px; background: #f9f9f9; border-radius: 6px; flex-wrap: wrap;">
            <label style="font-weight: 500;">Date Range:</label>
            <input type="month" id="timelineStartDate" value="{default_start}" min="{data_min_month}" max="{data_max_month}" style="padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;">
            <span>to</span>
            <input type="month" id="timelineEndDate" value="{default_end}" min="{data_min_month}" max="{data_max_month}" style="padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;">
            <button onclick="applyTimelineDateFilter()" style="padding: 6px 16px; background: #2074d5; color: white; border: none; border-radius: 4px; cursor: pointer;">Apply</button>
            <button onclick="resetTimelineDateFilter()" style="padding: 6px 16px; background: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; cursor: pointer;">Reset</button>
        </div>
        <div class="chart-container" style="height: 350px; cursor: pointer;">
            <canvas id="timelineChart"></canvas>
        </div>
        <script>
            var timelineResourcesData = {monthly_resources_json};
            var timelineServiceSummary = {monthly_service_summary_json};
            var timelineMonths = {chart_labels};
            var allTimelineMonths = {chart_labels};
            var allTimelineData = {{
                out_of_support: {chart_out_of_support},
                extended: {chart_extended},
                approaching: {chart_approaching},
                supported: {chart_supported}
            }};
            var timelineChartInstance = null;
            
            function initTimelineChart() {{
                var timelineCtx = document.getElementById('timelineChart');
                if (timelineCtx && !timelineChartInstance) {{
                    timelineChartInstance = new Chart(timelineCtx, {{
                        type: 'bar',
                        data: {{
                            labels: {chart_labels},
                            datasets: [
                                {{ label: 'Out of Support', data: {chart_out_of_support}, backgroundColor: '#ef5350', borderColor: '#c62828', borderWidth: 1 }},
                                {{ label: 'Extended Support', data: {chart_extended}, backgroundColor: '#42a5f5', borderColor: '#1565c0', borderWidth: 1 }},
                                {{ label: 'Approaching EOS', data: {chart_approaching}, backgroundColor: '#ffa726', borderColor: '#ef6c00', borderWidth: 1 }},
                                {{ label: 'Supported', data: {chart_supported}, backgroundColor: '#66bb6a', borderColor: '#2e7d32', borderWidth: 1 }}
                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            onClick: function(event, elements) {{
                                if (elements.length > 0) {{
                                    var index = elements[0].index;
                                    var month = timelineChartInstance.data.labels[index];
                                    showMonthResources(month);
                                }}
                            }},
                            plugins: {{ 
                                title: {{ display: true, text: 'Resources by End-of-Support Month (Click to view details)' }}, 
                                legend: {{ position: 'top' }},
                                tooltip: {{
                                    callbacks: {{
                                        afterBody: function(context) {{
                                            var month = context[0].label;
                                            var services = timelineServiceSummary[month] || {{}};
                                            var lines = ['', 'By Service:'];
                                            var sortedServices = Object.keys(services).sort(function(a, b) {{
                                                return services[b] - services[a];
                                            }});
                                            for (var i = 0; i < sortedServices.length && i < 5; i++) {{
                                                var svc = sortedServices[i];
                                                lines.push('  ' + svc + ': ' + services[svc]);
                                            }}
                                            if (sortedServices.length > 5) {{
                                                lines.push('  ... and ' + (sortedServices.length - 5) + ' more');
                                            }}
                                            lines.push('', 'Click to view all resources');
                                            return lines;
                                        }}
                                    }}
                                }}
                            }},
                            scales: {{ x: {{ stacked: true, title: {{ display: true, text: 'End-of-Support Month' }} }}, y: {{ stacked: true, beginAtZero: true, title: {{ display: true, text: 'Number of Resources' }} }} }}
                        }}
                    }});
                    timelineCtx.chart = timelineChartInstance;
                    // Apply default date filter on load
                    applyTimelineDateFilter();
                }}
            }}
            
            function applyTimelineDateFilter() {{
                var startDate = document.getElementById('timelineStartDate').value;
                var endDate = document.getElementById('timelineEndDate').value;
                
                if (!startDate || !endDate) {{
                    alert('Please select both start and end dates');
                    return;
                }}
                
                var filteredIndices = [];
                for (var i = 0; i < allTimelineMonths.length; i++) {{
                    var month = allTimelineMonths[i];
                    if (month >= startDate && month <= endDate) {{
                        filteredIndices.push(i);
                    }}
                }}
                
                var filteredMonths = filteredIndices.map(function(i) {{ return allTimelineMonths[i]; }});
                var filteredOutOfSupport = filteredIndices.map(function(i) {{ return allTimelineData.out_of_support[i]; }});
                var filteredExtended = filteredIndices.map(function(i) {{ return allTimelineData.extended[i]; }});
                var filteredApproaching = filteredIndices.map(function(i) {{ return allTimelineData.approaching[i]; }});
                var filteredSupported = filteredIndices.map(function(i) {{ return allTimelineData.supported[i]; }});
                
                timelineChartInstance.data.labels = filteredMonths;
                timelineChartInstance.data.datasets[0].data = filteredOutOfSupport;
                timelineChartInstance.data.datasets[1].data = filteredExtended;
                timelineChartInstance.data.datasets[2].data = filteredApproaching;
                timelineChartInstance.data.datasets[3].data = filteredSupported;
                timelineChartInstance.update();
            }}
            
            function resetTimelineDateFilter() {{
                document.getElementById('timelineStartDate').value = allTimelineMonths[0] || '';
                document.getElementById('timelineEndDate').value = allTimelineMonths[allTimelineMonths.length - 1] || '';
                
                timelineChartInstance.data.labels = allTimelineMonths;
                timelineChartInstance.data.datasets[0].data = allTimelineData.out_of_support;
                timelineChartInstance.data.datasets[1].data = allTimelineData.extended;
                timelineChartInstance.data.datasets[2].data = allTimelineData.approaching;
                timelineChartInstance.data.datasets[3].data = allTimelineData.supported;
                timelineChartInstance.update();
            }}
            
            function showMonthResources(month) {{
                var resources = timelineResourcesData[month] || [];
                if (resources.length === 0) {{
                    alert('No resources found for ' + month);
                    return;
                }}
                showChartResources('Resources with End-of-Support in ' + month, resources, {{}});
            }}
        </script>
        <h3 style="margin-top: 30px; color: #ff9900;">Upcoming End-of-Support Events</h3>
        <div style="max-height: 400px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 4px; padding: 10px;">
            {timeline_list}
        </div>
        {more_text}
    </div>
</div>"""

    def _generate_by_service_section(self, report: Report) -> str:
        """Generate the by-service breakdown section with paginated DataTables."""
        # First, aggregate all resources by service (across all accounts)
        service_data = {}  # service_name -> {status_counts, resources_list}
        
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                if service_name not in service_data:
                    service_data[service_name] = {
                        'status_counts': {
                            'supported': 0,
                            'approaching': 0,
                            'extended': 0,
                            'out_of_support': 0
                        },
                        'resources_list': []
                    }
                
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        for resource in version_group.resources:
                            status_key = self._status_to_key(resource.status)
                            service_data[service_name]['status_counts'][status_key] += 1
                            service_data[service_name]['resources_list'].append({
                                'account': account_name,
                                'engine': engine_name or 'N/A',
                                'version': version_name,
                                'name': resource.resource_name or resource.resource_arn or 'N/A',
                                'eos': resource.end_of_support.strftime('%Y-%m-%d') if resource.end_of_support else 'N/A',
                                'status': resource.status
                            })
        
        # Now generate HTML for each service
        service_groups = []
        service_table_ids = []
        
        for service_name in sorted(service_data.keys()):
            data = service_data[service_name]
            status_counts = data['status_counts']
            resources_list = data['resources_list']
            
            total = sum(status_counts.values())
            # Create safe ID for service
            safe_service_id = self._escape_html(service_name).replace(' ', '-').replace('.', '-').replace('/', '-').lower()
            service_id = f"service-{safe_service_id}"
            table_id = f"serviceTable-{safe_service_id}"
            service_table_ids.append(table_id)
            
            # Build ALL resources rows for this service (DataTable will paginate)
            resource_rows = []
            for r in resources_list:
                status_class = self._get_status_class(r['status'])
                status_label = self.STATUS_LABELS.get(r['status'], 'Unknown')
                resource_rows.append(f"""<tr data-account="{self._escape_html(r['account'])}" data-status="{status_label}">
                        <td>{self._escape_html(r['account'])}</td>
                        <td>{self._escape_html(r['engine'])}</td>
                        <td>{self._escape_html(r['version'])}</td>
                        <td title="{self._escape_html(r['name'])}">{self._escape_html(r['name'][:60])}{'...' if len(r['name']) > 60 else ''}</td>
                        <td>{r['eos']}</td>
                        <td><span class="status-badge {status_class}">{status_label}</span></td>
                    </tr>""")
            
            resource_rows_html = '\n'.join(resource_rows)
            
            service_groups.append(f"""
                <div class="service-group" id="{service_id}" data-service="{self._escape_html(service_name)}">
                    <div class="service-group-header" onclick="toggleServiceGroup('{service_id}')">
                        <span>
                            <strong>{self._escape_html(service_name)}</strong> 
                            (<span class="service-count">{total}</span> resources)
                        </span>
                        <span>
                            <span class="status-badge status-supported" data-count="{status_counts['supported']}">{status_counts['supported']}</span>
                            <span class="status-badge status-approaching" data-count="{status_counts['approaching']}">{status_counts['approaching']}</span>
                            <span class="status-badge status-extended" data-count="{status_counts['extended']}">{status_counts['extended']}</span>
                            <span class="status-badge status-out-of-support" data-count="{status_counts['out_of_support']}">{status_counts['out_of_support']}</span>
                        </span>
                    </div>
                    <div class="service-group-content">
                        <table id="{table_id}" class="service-datatable display" style="width: 100%;">
                            <thead>
                                <tr>
                                    <th>Account</th>
                                    <th>Engine</th>
                                    <th>Version</th>
                                    <th>Resource</th>
                                    <th>End of Support</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {resource_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
                """)
        
        service_groups_html = '\n'.join(service_groups)
        
        return f"""<div id="by-service-section" class="section">
    <h2>Resources by Service
        <button class="collapse-btn" onclick="toggleSection('by-service-content')">−</button>
    </h2>
    <div id="by-service-content" class="collapsible-content">
        <p>Click on a service to expand and see its resources:</p>
        {service_groups_html if service_groups else '<p>No service data available.</p>'}
    </div>
</div>"""

    def _generate_footer(self) -> str:
        """Generate the page footer."""
        return """<div class="footer">
    <p>Generated by AWS End-of-Support Tool | 
       <a href="https://github.com/savelyvas/EndOfSupport" target="_blank">GitHub</a>
    </p>
</div>"""

    def _generate_scripts(self, report: Report) -> str:
        """Generate JavaScript for interactivity and charts."""
        # Collect chart data
        service_data = {}
        account_data = {}
        status_totals = {
            'supported': 0,
            'approaching': 0,
            'extended': 0,
            'out_of_support': 0
        }
        
        # Also collect detailed resources for click-through
        from collections import defaultdict
        service_resources = defaultdict(list)
        account_resources = defaultdict(list)
        status_resources = defaultdict(list)
        
        for account_name, account_group in report.accounts.items():
            if account_name not in account_data:
                account_data[account_name] = {'supported': 0, 'approaching': 0, 'extended': 0, 'out_of_support': 0}
            for service_name, service_group in account_group.services.items():
                if service_name not in service_data:
                    service_data[service_name] = {'supported': 0, 'approaching': 0, 'extended': 0, 'out_of_support': 0}
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        for resource in version_group.resources:
                            status_key = self._status_to_key(resource.status)
                            service_data[service_name][status_key] += 1
                            account_data[account_name][status_key] += 1
                            status_totals[status_key] += 1
                            
                            # Store detailed resource info
                            resource_info = {
                                'account': account_name,
                                'service': service_name,
                                'engine': engine_name or 'N/A',
                                'version': version_name,
                                'resource': resource.resource_name or resource.resource_arn or 'N/A',
                                'eos_date': resource.end_of_support.strftime('%Y-%m-%d') if resource.end_of_support else 'N/A',
                                'status': status_key
                            }
                            service_resources[service_name].append(resource_info)
                            account_resources[account_name].append(resource_info)
                            status_resources[status_key].append(resource_info)
        
        # Convert to JSON-safe format
        import json
        service_labels = json.dumps(list(service_data.keys()))
        service_supported = json.dumps([v['supported'] for v in service_data.values()])
        service_approaching = json.dumps([v['approaching'] for v in service_data.values()])
        service_extended = json.dumps([v['extended'] for v in service_data.values()])
        service_out = json.dumps([v['out_of_support'] for v in service_data.values()])
        
        account_labels = json.dumps(list(account_data.keys()))
        account_supported = json.dumps([v['supported'] for v in account_data.values()])
        account_approaching = json.dumps([v['approaching'] for v in account_data.values()])
        account_extended = json.dumps([v['extended'] for v in account_data.values()])
        account_out = json.dumps([v['out_of_support'] for v in account_data.values()])
        
        status_values = json.dumps([
            status_totals['supported'],
            status_totals['approaching'],
            status_totals['extended'],
            status_totals['out_of_support']
        ])
        
        service_totals = json.dumps([sum(v.values()) for v in service_data.values()])
        
        # JSON for click-through data
        service_resources_json = json.dumps(dict(service_resources))
        account_resources_json = json.dumps(dict(account_resources))
        status_resources_json = json.dumps(dict(status_resources))
        
        # Build service summary per status for tooltips
        status_service_summary = {
            'total': {},
            'supported': {},
            'approaching': {},
            'extended': {},
            'out_of_support': {}
        }
        for svc_name, svc_counts in service_data.items():
            total_for_service = sum(svc_counts.values())
            if total_for_service > 0:
                status_service_summary['total'][svc_name] = total_for_service
            for status_key in ['supported', 'approaching', 'extended', 'out_of_support']:
                if svc_counts[status_key] > 0:
                    status_service_summary[status_key][svc_name] = svc_counts[status_key]
        
        status_service_summary_json = json.dumps(status_service_summary)
        
        return f"""<script>
// Chart click-through data
var serviceResourcesData = {service_resources_json};
var accountResourcesData = {account_resources_json};
var statusResourcesData = {status_resources_json};
var statusServiceSummary = {status_service_summary_json};
var statusLabelsMap = ['supported', 'approaching', 'extended', 'out_of_support'];
var statusDisplayNames = {{
    'supported': 'Supported',
    'approaching': 'Approaching EOS',
    'extended': 'Extended Support',
    'out_of_support': 'Out of Support'
}};

// Show resources for a specific status (from summary card click)
function showStatusResources(statusKey) {{
    var resources = statusResourcesData[statusKey] || [];
    var title = statusDisplayNames[statusKey] + ' Resources';
    showChartResources(title, resources, {{ statuses: [statusKey] }});
}}

// Show all resources (from Total card click)
function showAllResources() {{
    var allResources = [];
    for (var status in statusResourcesData) {{
        allResources = allResources.concat(statusResourcesData[status]);
    }}
    showChartResources('All Resources', allResources, {{}});
}}

// Summary card tooltip functions
var summaryTooltip = null;

function showSummaryTooltip(event, statusKey) {{
    var services = statusServiceSummary[statusKey] || {{}};
    var serviceList = Object.keys(services);
    
    if (serviceList.length === 0) return;
    
    // Sort by count descending
    serviceList.sort(function(a, b) {{ return services[b] - services[a]; }});
    
    // Create tooltip element if not exists
    if (!summaryTooltip) {{
        summaryTooltip = document.createElement('div');
        summaryTooltip.className = 'summary-card-tooltip';
        document.body.appendChild(summaryTooltip);
    }}
    
    // Build tooltip content
    var title = statusKey === 'total' ? 'All Resources' : statusDisplayNames[statusKey];
    var html = '<div class="tooltip-title">Resources by Service</div>';
    
    var maxShow = 5;
    var shown = Math.min(serviceList.length, maxShow);
    
    for (var i = 0; i < shown; i++) {{
        var svc = serviceList[i];
        html += '<div class="tooltip-row">';
        html += '<span class="tooltip-service">' + svc + '</span>';
        html += '<span class="tooltip-count">' + services[svc] + '</span>';
        html += '</div>';
    }}
    
    if (serviceList.length > maxShow) {{
        var remaining = serviceList.length - maxShow;
        html += '<div class="tooltip-more">... and ' + remaining + ' more service' + (remaining > 1 ? 's' : '') + '</div>';
    }}
    
    summaryTooltip.innerHTML = html;
    summaryTooltip.style.display = 'block';
    
    // Position tooltip
    positionSummaryTooltip(event);
}}

function positionSummaryTooltip(event) {{
    if (!summaryTooltip) return;
    
    var x = event.pageX + 15;
    var y = event.pageY + 15;
    
    // Adjust if tooltip goes off screen
    var tooltipRect = summaryTooltip.getBoundingClientRect();
    if (x + tooltipRect.width > window.innerWidth) {{
        x = event.pageX - tooltipRect.width - 15;
    }}
    if (y + tooltipRect.height > window.innerHeight + window.scrollY) {{
        y = event.pageY - tooltipRect.height - 15;
    }}
    
    summaryTooltip.style.left = x + 'px';
    summaryTooltip.style.top = y + 'px';
}}

function hideSummaryTooltip() {{
    if (summaryTooltip) {{
        summaryTooltip.style.display = 'none';
    }}
}}

// Show Report Help Guide
function showReportHelp(event) {{
    event.preventDefault();
    
    var html = '<!DOCTYPE html><html><head>';
    html += '<meta charset="UTF-8">';
    html += '<title>AWS End-of-Support Report - User Guide</title>';
    html += '<style>';
    html += 'body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }}';
    html += '.header {{ background: linear-gradient(135deg, #232f3e 0%, #37475a 100%); color: white; padding: 30px; text-align: center; }}';
    html += '.header h1 {{ margin: 0; font-size: 28px; }}';
    html += '.header p {{ margin: 10px 0 0 0; opacity: 0.9; }}';
    html += '.container {{ max-width: 900px; margin: 0 auto; padding: 30px; }}';
    html += '.toc {{ background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 30px; }}';
    html += '.toc h2 {{ color: #232f3e; margin-top: 0; border-bottom: 2px solid #ff9900; padding-bottom: 10px; }}';
    html += '.toc ul {{ list-style: none; padding: 0; margin: 0; }}';
    html += '.toc li {{ padding: 8px 0; }}';
    html += '.toc a {{ color: #2074d5; text-decoration: none; }}';
    html += '.toc a:hover {{ text-decoration: underline; }}';
    html += '.section {{ background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }}';
    html += '.section h2 {{ color: #232f3e; margin-top: 0; border-bottom: 2px solid #ff9900; padding-bottom: 10px; }}';
    html += '.section h3 {{ color: #37475a; margin-top: 20px; }}';
    html += '.feature {{ background: #f9f9f9; padding: 15px; border-radius: 6px; margin: 15px 0; border-left: 4px solid #ff9900; }}';
    html += '.feature h4 {{ margin: 0 0 10px 0; color: #232f3e; }}';
    html += '.tip {{ background: #e8f4fd; padding: 15px; border-radius: 6px; margin: 15px 0; border-left: 4px solid #2074d5; }}';
    html += '.tip strong {{ color: #0d47a1; }}';
    html += '.status-example {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; margin: 2px; }}';
    html += '.status-supported {{ background: #c8e6c9; color: #1b5e20; }}';
    html += '.status-approaching {{ background: #fff9c4; color: #f57f17; }}';
    html += '.status-extended {{ background: #bbdefb; color: #0d47a1; }}';
    html += '.status-out {{ background: #ffcdd2; color: #b71c1c; }}';
    html += 'code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}';
    html += 'ul {{ padding-left: 20px; }}';
    html += 'li {{ margin: 8px 0; }}';
    html += '</style>';
    html += '</head><body>';
    
    // Header
    html += '<div class="header">';
    html += '<h1>AWS End-of-Support Report</h1>';
    html += '<p>User Guide - How to Use This Report</p>';
    html += '</div>';
    
    html += '<div class="container">';
    
    // Table of Contents
    html += '<div class="toc">';
    html += '<h2>Table of Contents</h2>';
    html += '<ul>';
    html += '<li><a href="#overview">1. Report Overview</a></li>';
    html += '<li><a href="#status-types">2. Understanding Status Types</a></li>';
    html += '<li><a href="#navigation">3. Navigation Menu</a></li>';
    html += '<li><a href="#filters">4. Using Filters</a></li>';
    html += '<li><a href="#summary">5. Summary Section</a></li>';
    html += '<li><a href="#charts">6. Status Breakdown Charts</a></li>';
    html += '<li><a href="#resources-table">7. All Resources Table</a></li>';
    html += '<li><a href="#timeline">8. Support Timeline</a></li>';
    html += '<li><a href="#by-service">9. By Service Section</a></li>';
    html += '<li><a href="#export">10. Exporting Data</a></li>';
    html += '</ul>';
    html += '</div>';
    
    // Section 1: Overview
    html += '<div class="section" id="overview">';
    html += '<h2>1. Report Overview</h2>';
    html += '<p>This report provides a comprehensive view of your AWS resources and their End-of-Support (EOS) status. It helps you identify resources that need attention before they reach their end-of-support dates.</p>';
    html += '<div class="feature"><h4>Key Features</h4>';
    html += '<ul>';
    html += '<li>Visual status breakdown by service, account, and overall distribution</li>';
    html += '<li>Interactive timeline showing upcoming EOS events</li>';
    html += '<li>Detailed resource tables with search and export capabilities</li>';
    html += '<li>Click-through functionality on all charts to view affected resources</li>';
    html += '</ul></div>';
    html += '</div>';
    
    // Section 2: Status Types
    html += '<div class="section" id="status-types">';
    html += '<h2>2. Understanding Status Types</h2>';
    html += '<p>Resources are classified into four status categories:</p>';
    html += '<div class="feature">';
    html += '<p><span class="status-example status-supported">Supported</span> - Resource version is fully supported with no immediate action required.</p>';
    html += '<p><span class="status-example status-approaching">Approaching EOS</span> - End-of-support date is within the configured threshold (default: 90 days). Plan your upgrade soon.</p>';
    html += '<p><span class="status-example status-extended">Extended Support</span> - Resource is in extended support period. May incur additional costs.</p>';
    html += '<p><span class="status-example status-out">Out of Support</span> - Resource has passed its end-of-support date. Immediate action recommended.</p>';
    html += '</div>';
    html += '</div>';
    
    // Section 3: Navigation
    html += '<div class="section" id="navigation">';
    html += '<h2>3. Navigation Menu</h2>';
    html += '<p>The top navigation bar provides quick access to all report sections:</p>';
    html += '<ul>';
    html += '<li><strong>Summary</strong> - Jump to the executive summary with key metrics</li>';
    html += '<li><strong>Status Breakdown</strong> - View charts showing resource distribution</li>';
    html += '<li><strong>All Resources</strong> - Access the complete resource table</li>';
    html += '<li><strong>Timeline</strong> - See upcoming EOS events on a timeline</li>';
    html += '<li><strong>By Service</strong> - View resources grouped by AWS service</li>';
    html += '<li><strong>Help</strong> - Open this user guide</li>';
    html += '</ul>';
    html += '<div class="tip"><strong>Tip:</strong> Use the arrow button (↑) in the bottom-right corner to quickly return to the top of the report.</div>';
    html += '</div>';
    
    // Section 4: Filters
    html += '<div class="section" id="filters">';
    html += '<h2>4. Using Filters</h2>';
    html += '<p>The filter bar below the navigation allows you to focus on specific subsets of your resources:</p>';
    html += '<h3>Service Filter</h3>';
    html += '<p>Click on service badges to toggle them on/off. Selected services appear highlighted. Only resources from selected services will be shown in the tables.</p>';
    html += '<h3>Account Filter</h3>';
    html += '<p>Click the account dropdown to select/deselect specific AWS accounts:</p>';
    html += '<ul>';
    html += '<li>Use the search box to find specific accounts</li>';
    html += '<li>Click "Select All" or "Deselect All" for bulk selection</li>';
    html += '<li>Click individual accounts to toggle them</li>';
    html += '</ul>';
    html += '<h3>Status Filter</h3>';
    html += '<p>Click on status badges to show/hide resources with specific statuses. This helps you focus on resources that need immediate attention.</p>';
    html += '<div class="tip"><strong>Tip:</strong> Click "Apply Filters" after making your selections to update the view.</div>';
    html += '</div>';
    
    // Section 5: Summary
    html += '<div class="section" id="summary">';
    html += '<h2>5. Summary Section</h2>';
    html += '<p>The summary section provides an at-a-glance view of your resource status:</p>';
    html += '<ul>';
    html += '<li><strong>Total Resources</strong> - The total number of resources analyzed</li>';
    html += '<li><strong>Status Cards</strong> - Color-coded cards showing counts for each status type</li>';
    html += '</ul>';
    html += '<p>Use this section to quickly assess the overall health of your AWS resources.</p>';
    html += '</div>';
    
    // Section 6: Charts
    html += '<div class="section" id="charts">';
    html += '<h2>6. Status Breakdown Charts</h2>';
    html += '<p>Four interactive charts provide visual insights into your resource distribution:</p>';
    html += '<h3>By Service (Bar Chart)</h3>';
    html += '<p>Shows resource counts per AWS service, stacked by status. Click on any bar to view all resources for that service in a new tab.</p>';
    html += '<h3>By Account (Bar Chart)</h3>';
    html += '<p>Shows resource counts per AWS account, stacked by status. Click on any bar to view all resources for that account in a new tab.</p>';
    html += '<h3>Overall Status Distribution (Doughnut Chart)</h3>';
    html += '<p>Shows the proportion of resources in each status category. Click on any segment to view all resources with that status in a new tab.</p>';
    html += '<h3>Resources by Service (Pie Chart)</h3>';
    html += '<p>Shows the total resource count per service regardless of status. Click on any slice to view all resources for that service in a new tab.</p>';
    html += '<div class="tip"><strong>Tip:</strong> Hover over chart elements to see detailed counts. All charts are clickable - click to open a detailed view in a new tab.</div>';
    html += '</div>';
    
    // Section 7: Resources Table
    html += '<div class="section" id="resources-table">';
    html += '<h2>7. All Resources Table</h2>';
    html += '<p>The main resources table shows all analyzed resources with the following columns:</p>';
    html += '<ul>';
    html += '<li><strong>Account</strong> - AWS account name or ID</li>';
    html += '<li><strong>Service</strong> - AWS service (RDS, ElastiCache, etc.)</li>';
    html += '<li><strong>Engine</strong> - Database or service engine type</li>';
    html += '<li><strong>Version</strong> - Current version of the resource</li>';
    html += '<li><strong>Resource</strong> - Resource name or ARN</li>';
    html += '<li><strong>EOS Date</strong> - End-of-support date</li>';
    html += '<li><strong>Days to EOS</strong> - Number of days until end-of-support</li>';
    html += '<li><strong>Status</strong> - Current support status</li>';
    html += '</ul>';
    html += '<h3>Table Features</h3>';
    html += '<ul>';
    html += '<li><strong>Search</strong> - Use the search box to filter by any column</li>';
    html += '<li><strong>Sort</strong> - Click column headers to sort ascending/descending</li>';
    html += '<li><strong>Pagination</strong> - Navigate through pages using the controls at the bottom</li>';
    html += '<li><strong>Copy</strong> - Copy table data to clipboard</li>';
    html += '<li><strong>CSV</strong> - Export visible data to CSV file</li>';
    html += '</ul>';
    html += '</div>';
    
    // Section 8: Timeline
    html += '<div class="section" id="timeline">';
    html += '<h2>8. Support Timeline</h2>';
    html += '<p>The timeline section visualizes upcoming end-of-support events:</p>';
    html += '<h3>Timeline Chart</h3>';
    html += '<p>A stacked bar chart showing resource counts by month, colored by status. This helps you plan upgrades by seeing when resources will reach their EOS dates.</p>';
    html += '<h3>Date Range Filter</h3>';
    html += '<p>Use the date range inputs to focus on a specific time period:</p>';
    html += '<ul>';
    html += '<li>Select start and end months using the date pickers</li>';
    html += '<li>Click "Apply" to filter the chart</li>';
    html += '<li>Click "Reset" to show all available data</li>';
    html += '</ul>';
    html += '<h3>Click-Through Details</h3>';
    html += '<p>Click on any bar in the timeline to open a new tab showing all resources with EOS dates in that month.</p>';
    html += '<h3>Tooltip Information</h3>';
    html += '<p>Hover over bars to see:</p>';
    html += '<ul>';
    html += '<li>Status breakdown for that month</li>';
    html += '<li>Top 5 services with resource counts</li>';
    html += '</ul>';
    html += '<div class="tip"><strong>Tip:</strong> The timeline defaults to showing from the earliest EOS date to 6 months in the future.</div>';
    html += '</div>';
    
    // Section 9: By Service
    html += '<div class="section" id="by-service">';
    html += '<h2>9. By Service Section</h2>';
    html += '<p>This section groups resources by AWS service for detailed analysis:</p>';
    html += '<ul>';
    html += '<li>Each service has its own expandable panel</li>';
    html += '<li>Click on a service header to expand/collapse its details</li>';
    html += '<li>Each panel shows status counts and a detailed resource table</li>';
    html += '<li>Tables support search, sort, and pagination</li>';
    html += '</ul>';
    html += '<p>Use this section when you need to focus on a specific AWS service.</p>';
    html += '</div>';
    
    // Section 10: Export
    html += '<div class="section" id="export">';
    html += '<h2>10. Exporting Data</h2>';
    html += '<p>Multiple export options are available throughout the report:</p>';
    html += '<h3>Main Table Export</h3>';
    html += '<p>The "All Resources" table provides three export buttons:</p>';
    html += '<ul>';
    html += '<li><strong>Copy</strong> - Copies visible data to clipboard (tab-separated)</li>';
    html += '<li><strong>CSV</strong> - Downloads visible data as a CSV file</li>';
    html += '</ul>';
    html += '<h3>Chart Detail Export</h3>';
    html += '<p>When you click on a chart element and open the detail view in a new tab, you can:</p>';
    html += '<ul>';
    html += '<li>Use the "Copy" button to copy data to clipboard</li>';
    html += '<li>Use the "CSV" button to download as CSV</li>';
    html += '<li>Use the search box to filter before exporting</li>';
    html += '</ul>';
    html += '<div class="tip"><strong>Tip:</strong> Filters applied to the main table affect what gets exported. Apply filters first, then export to get a focused dataset.</div>';
    html += '</div>';
    
    html += '</div>'; // container
    html += '</body></html>';
    
    var newTab = window.open('', '_blank');
    newTab.document.write(html);
    newTab.document.close();
}}

// Generic function to show resources in a new tab with filters
function showChartResources(title, resources, filterContext) {{
    if (!resources || resources.length === 0) {{
        alert('No resources found');
        return;
    }}
    
    // Default filter context if not provided
    filterContext = filterContext || {{}};
    var selectedServices = filterContext.services || null;
    var selectedAccounts = filterContext.accounts || null;
    var selectedStatuses = filterContext.statuses || null;
    
    // Get unique values from resources for filter options
    var allServices = [...new Set(resources.map(function(r) {{ return r.service; }}))].sort();
    var allAccounts = [...new Set(resources.map(function(r) {{ return r.account; }}))].sort();
    var allStatuses = ['supported', 'approaching', 'extended', 'out_of_support'];
    
    var statusColors = {{
        'supported': {{ bg: '#c8e6c9', text: '#1b5e20' }},
        'approaching': {{ bg: '#fff9c4', text: '#f57f17' }},
        'extended': {{ bg: '#bbdefb', text: '#0d47a1' }},
        'out_of_support': {{ bg: '#ffcdd2', text: '#b71c1c' }}
    }};
    
    var statusLabels = {{
        'supported': 'Supported',
        'approaching': 'Approaching EOS',
        'extended': 'Extended Support',
        'out_of_support': 'Out of Support'
    }};
    
    // Newline character for proper formatting
    var nl = String.fromCharCode(10);
    
    var html = '<!DOCTYPE html><html><head>' + nl;
    html += '<meta charset="UTF-8">' + nl;
    html += '<title>' + title + '</title>' + nl;
    html += '<style>' + nl;
    html += 'body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}' + nl;
    html += '.container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}' + nl;
    html += 'h1 {{ color: #232f3e; border-bottom: 3px solid #ff9900; padding-bottom: 10px; margin-bottom: 20px; }}' + nl;
    html += '.summary {{ display: flex; gap: 15px; margin: 20px 0; flex-wrap: wrap; }}' + nl;
    html += '.summary-item {{ padding: 10px 20px; border-radius: 6px; font-weight: 500; }}' + nl;
    html += '.dt-buttons {{ margin-bottom: 10px; }}' + nl;
    html += '.dt-button {{ background-color: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; padding: 6px 12px; margin-right: 5px; cursor: pointer; font-size: 14px; }}' + nl;
    html += '.dt-button:hover {{ background-color: #e0e0e0; }}' + nl;
    html += '.copy-popup {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #333; color: white; padding: 20px 40px; border-radius: 8px; font-size: 18px; z-index: 9999; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }}' + nl;
    html += '.copy-popup h2 {{ margin: 0 0 10px 0; font-size: 20px; }}' + nl;
    html += '.copy-popup p {{ margin: 0; font-size: 14px; opacity: 0.9; }}' + nl;
    html += 'table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}' + nl;
    html += 'th {{ background: #232f3e; color: white; padding: 12px; text-align: left; }}' + nl;
    html += 'td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}' + nl;
    html += 'tr:hover {{ background: #f9f9f9; }}' + nl;
    html += 'tr.hidden {{ display: none; }}' + nl;
    html += '.status-badge {{ padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 500; }}' + nl;
    html += '.toolbar {{ margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 6px; display: flex; gap: 15px; align-items: center; flex-wrap: wrap; }}' + nl;
    html += '.toolbar input {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; width: 300px; }}' + nl;
    html += '.filter-bar {{ background: #fff; padding: 15px; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 20px; }}' + nl;
    html += '.filter-row {{ display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }}' + nl;
    html += '.filter-group {{ flex: 1; min-width: 200px; }}' + nl;
    html += '.filter-group label {{ display: block; font-weight: 600; margin-bottom: 8px; color: #16191f; }}' + nl;
    html += '.filter-options {{ display: flex; flex-wrap: wrap; gap: 6px; }}' + nl;
    html += '.filter-chip {{ display: inline-flex; align-items: center; padding: 5px 10px; background: #e8f4fd; border: 2px solid #2074d5; border-radius: 16px; cursor: pointer; font-size: 12px; transition: all 0.2s; user-select: none; }}' + nl;
    html += '.filter-chip:hover {{ background: #d0e8fc; }}' + nl;
    html += '.filter-chip.selected {{ background: #2074d5; color: white; }}' + nl;
    html += '.filter-chip.status-supported.selected {{ background: #43a047; border-color: #43a047; }}' + nl;
    html += '.filter-chip.status-approaching.selected {{ background: #fb8c00; border-color: #fb8c00; }}' + nl;
    html += '.filter-chip.status-extended.selected {{ background: #1976d2; border-color: #1976d2; }}' + nl;
    html += '.filter-chip.status-out_of_support.selected {{ background: #e53935; border-color: #e53935; }}' + nl;
    html += '.filter-actions {{ display: flex; gap: 10px; align-items: flex-end; padding-top: 24px; }}' + nl;
    html += '.filter-btn {{ padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; font-weight: 500; }}' + nl;
    html += '.apply-btn {{ background: #ff9900; color: white; }}' + nl;
    html += '.apply-btn:hover {{ background: #ec7211; }}' + nl;
    html += '.reset-btn {{ background: #f5f5f5; color: #545b64; border: 1px solid #ccc; }}' + nl;
    html += '.reset-btn:hover {{ background: #e0e0e0; }}' + nl;
    html += '</style>' + nl;
    html += '</head><body>' + nl;
    html += '<div class="container">' + nl;
    html += '<h1>' + title + '</h1>' + nl;
    
    // Helper variable for single quotes in HTML attributes
    var q = String.fromCharCode(39);
    
    // Build filter bar
    html += '<div class="filter-bar">' + nl;
    html += '<div class="filter-row">' + nl;
    
    // Service filter
    html += '<div class="filter-group">';
    html += '<label>Service</label>';
    html += '<div class="filter-options" id="serviceFilters">';
    allServices.forEach(function(svc) {{
        var isSelected = selectedServices === null || selectedServices.indexOf(svc) > -1;
        html += "<span class=" + q + "filter-chip" + (isSelected ? " selected" : "") + q + " data-filter=" + q + "service" + q + " data-value=" + q + svc + q + " onclick=" + q + "toggleFilterChip(this)" + q + ">" + svc + "</span>";
    }});
    html += '</div></div>';
    
    // Account filter
    html += '<div class="filter-group">';
    html += '<label>Account</label>';
    html += '<div class="filter-options" id="accountFilters">';
    allAccounts.forEach(function(acc) {{
        var isSelected = selectedAccounts === null || selectedAccounts.indexOf(acc) > -1;
        html += "<span class=" + q + "filter-chip" + (isSelected ? " selected" : "") + q + " data-filter=" + q + "account" + q + " data-value=" + q + acc + q + " onclick=" + q + "toggleFilterChip(this)" + q + ">" + acc + "</span>";
    }});
    html += '</div></div>';
    
    // Status filter
    html += '<div class="filter-group">';
    html += '<label>Status</label>';
    html += '<div class="filter-options" id="statusFilters">';
    allStatuses.forEach(function(st) {{
        var isSelected = selectedStatuses === null || selectedStatuses.indexOf(st) > -1;
        html += "<span class=" + q + "filter-chip status-" + st + (isSelected ? " selected" : "") + q + " data-filter=" + q + "status" + q + " data-value=" + q + st + q + " onclick=" + q + "toggleFilterChip(this)" + q + ">" + statusLabels[st] + "</span>";
    }});
    html += '</div></div>';
    
    // Filter actions
    html += '<div class="filter-actions">';
    html += "<button class=" + q + "filter-btn apply-btn" + q + " onclick=" + q + "applyFilters()" + q + ">Apply</button>";
    html += "<button class=" + q + "filter-btn reset-btn" + q + " onclick=" + q + "resetFilters()" + q + ">Reset</button>";
    html += '</div></div></div>';
    
    // Summary counts
    html += '<div class="summary" id="summaryBar"></div>';
    
    // Toolbar
    html += '<div class="toolbar">';
    html += '<div class="dt-buttons">';
    html += "<button class=" + q + "dt-button" + q + " onclick=" + q + "copyToClipboard()" + q + ">Copy</button>";
    html += "<button class=" + q + "dt-button" + q + " onclick=" + q + "exportToCSV()" + q + ">CSV</button>";
    html += '</div>';
    html += '<input type="text" id="searchInput" placeholder="Search resources..." onkeyup="applyFilters()">';
    html += '</div>';
    
    // Table
    html += '<table id="resourceTable">';
    html += '<thead><tr><th>Account</th><th>Service</th><th>Engine</th><th>Version</th><th>Resource</th><th>EOS Date</th><th>Status</th></tr></thead>';
    html += '<tbody>';
    
    resources.forEach(function(r) {{
        var colors = statusColors[r.status];
        html += '<tr data-account="' + r.account + '" data-service="' + r.service + '" data-status="' + r.status + '">';
        html += '<td>' + r.account + '</td>';
        html += '<td>' + r.service + '</td>';
        html += '<td>' + r.engine + '</td>';
        html += '<td>' + r.version + '</td>';
        html += '<td>' + r.resource + '</td>';
        html += '<td>' + r.eos_date + '</td>';
        html += '<td><span class="status-badge" style="background: ' + colors.bg + '; color: ' + colors.text + ';">' + statusLabels[r.status] + '</span></td>';
        html += '</tr>';
    }});
    
    html += '</tbody></table></div>' + nl;
    
    // JavaScript
    html += '<scr' + 'ipt>' + nl;
    html += 'var statusColors = ' + JSON.stringify(statusColors) + ';' + nl;
    html += 'var statusLabels = ' + JSON.stringify(statusLabels) + ';' + nl;
    html += 'function chr(c) {{ return String.fromCharCode(c); }}' + nl;
    html += 'function toggleFilterChip(el) {{ el.classList.toggle("selected"); }}' + nl;
    html += 'function getSelectedFilters() {{' + nl;
    html += '  var s = [], a = [], st = [];' + nl;
    html += '  document.querySelectorAll("#serviceFilters .filter-chip.selected").forEach(function(c) {{ s.push(c.dataset.value); }});' + nl;
    html += '  document.querySelectorAll("#accountFilters .filter-chip.selected").forEach(function(c) {{ a.push(c.dataset.value); }});' + nl;
    html += '  document.querySelectorAll("#statusFilters .filter-chip.selected").forEach(function(c) {{ st.push(c.dataset.value); }});' + nl;
    html += '  return {{ services: s, accounts: a, statuses: st }};' + nl;
    html += '}}' + nl;
    html += 'function applyFilters() {{' + nl;
    html += '  var f = getSelectedFilters();' + nl;
    html += '  var search = document.getElementById("searchInput").value.toLowerCase();' + nl;
    html += '  var rows = document.querySelectorAll("#resourceTable tbody tr");' + nl;
    html += '  var counts = {{ total: 0, supported: 0, approaching: 0, extended: 0, out_of_support: 0 }};' + nl;
    html += '  rows.forEach(function(row) {{' + nl;
    html += '    var svc = row.dataset.service, acc = row.dataset.account, st = row.dataset.status;' + nl;
    html += '    var text = row.textContent.toLowerCase();' + nl;
    html += '    var ok = (f.services.length === 0 || f.services.indexOf(svc) > -1) && (f.accounts.length === 0 || f.accounts.indexOf(acc) > -1) && (f.statuses.length === 0 || f.statuses.indexOf(st) > -1) && (search === "" || text.indexOf(search) > -1);' + nl;
    html += '    if (ok) {{ row.classList.remove("hidden"); counts.total++; counts[st]++; }}' + nl;
    html += '    else {{ row.classList.add("hidden"); }}' + nl;
    html += '  }});' + nl;
    html += '  updateSummary(counts);' + nl;
    html += '}}' + nl;
    html += 'function resetFilters() {{' + nl;
    html += '  document.querySelectorAll(".filter-chip").forEach(function(c) {{ c.classList.add("selected"); }});' + nl;
    html += '  document.getElementById("searchInput").value = "";' + nl;
    html += '  applyFilters();' + nl;
    html += '}}' + nl;
    html += 'function updateSummary(counts) {{' + nl;
    html += '  var dq = String.fromCharCode(34);' + nl;
    html += '  var h = "<div class=" + dq + "summary-item" + dq + " style=" + dq + "background: #232f3e; color: white;" + dq + ">Showing: " + counts.total + "</div>";' + nl;
    html += '  for (var st in statusLabels) {{' + nl;
    html += '    if (counts[st] > 0) {{' + nl;
    html += '      var c = statusColors[st];' + nl;
    html += '      h += "<div class=" + dq + "summary-item" + dq + " style=" + dq + "background: " + c.bg + "; color: " + c.text + ";" + dq + ">" + statusLabels[st] + ": " + counts[st] + "</div>";' + nl;
    html += '    }}' + nl;
    html += '  }}' + nl;
    html += '  document.getElementById("summaryBar").innerHTML = h;' + nl;
    html += '}}' + nl;
    html += 'function exportToCSV() {{' + nl;
    html += '  var rows = document.querySelectorAll("#resourceTable tr");' + nl;
    html += '  var csv = [];' + nl;
    html += '  for (var i = 0; i < rows.length; i++) {{' + nl;
    html += '    if (rows[i].classList.contains("hidden")) continue;' + nl;
    html += '    var cols = rows[i].querySelectorAll("td, th");' + nl;
    html += '    var rd = [];' + nl;
    html += '    for (var j = 0; j < cols.length; j++) {{ rd.push(chr(34) + cols[j].textContent.replace(/"/g, chr(34)+chr(34)) + chr(34)); }}' + nl;
    html += '    csv.push(rd.join(","));' + nl;
    html += '  }}' + nl;
    html += '  var blob = new Blob([csv.join(String.fromCharCode(10))], {{type: "text/csv;charset=utf-8;"}});' + nl;
    html += '  var link = document.createElement("a");' + nl;
    html += '  link.href = URL.createObjectURL(blob);' + nl;
    html += '  link.download = "resources.csv";' + nl;
    html += '  document.body.appendChild(link);' + nl;
    html += '  link.click();' + nl;
    html += '  document.body.removeChild(link);' + nl;
    html += '}}' + nl;
    html += 'function copyToClipboard() {{' + nl;
    html += '  var rows = document.querySelectorAll("#resourceTable tr");' + nl;
    html += '  var text = [], cnt = 0;' + nl;
    html += '  for (var i = 0; i < rows.length; i++) {{' + nl;
    html += '    if (rows[i].classList.contains("hidden")) continue;' + nl;
    html += '    var cols = rows[i].querySelectorAll("td, th");' + nl;
    html += '    var rd = [];' + nl;
    html += '    for (var j = 0; j < cols.length; j++) {{ rd.push(cols[j].textContent); }}' + nl;
    html += '    text.push(rd.join(String.fromCharCode(9)));' + nl;
    html += '    cnt++;' + nl;
    html += '  }}' + nl;
    html += '  var tc = text.join(String.fromCharCode(10));' + nl;
    html += '  if (navigator.clipboard && navigator.clipboard.writeText) {{' + nl;
    html += '    navigator.clipboard.writeText(tc).then(function() {{ showCopyPopup(cnt - 1); }}).catch(function() {{ fallbackCopy(tc, cnt - 1); }});' + nl;
    html += '  }} else {{ fallbackCopy(tc, cnt - 1); }}' + nl;
    html += '}}' + nl;
    html += 'function showCopyPopup(count) {{' + nl;
    html += '  var popup = document.createElement("div");' + nl;
    html += '  popup.className = "copy-popup";' + nl;
    html += '  popup.innerHTML = "<h2>Copy to clipboard</h2><p>Copied " + count + " rows to clipboard</p>";' + nl;
    html += '  document.body.appendChild(popup);' + nl;
    html += '  setTimeout(function() {{ document.body.removeChild(popup); }}, 1500);' + nl;
    html += '}}' + nl;
    html += 'function fallbackCopy(text, count) {{' + nl;
    html += '  var ta = document.createElement("textarea");' + nl;
    html += '  ta.value = text;' + nl;
    html += '  ta.style.position = "fixed";' + nl;
    html += '  ta.style.left = "-9999px";' + nl;
    html += '  document.body.appendChild(ta);' + nl;
    html += '  ta.select();' + nl;
    html += '  try {{ document.execCommand("copy"); showCopyPopup(count); }}' + nl;
    html += '  catch(e) {{ alert("Copy failed"); }}' + nl;
    html += '  document.body.removeChild(ta);' + nl;
    html += '}}' + nl;
    html += 'document.addEventListener("DOMContentLoaded", function() {{ applyFilters(); }});' + nl;
    html += '</scr' + 'ipt>';
    
    html += '</body></html>';
    
    var newTab = window.open('', '_blank');
    newTab.document.write(html);
    newTab.document.close();
}}

// Scroll to section
function scrollToSection(event) {{
    event.preventDefault();
    const targetId = event.target.getAttribute('href').substring(1);
    const target = document.getElementById(targetId);
    if (target) {{
        target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}
}}

// Toggle section collapse
function toggleSection(sectionId) {{
    const section = document.getElementById(sectionId);
    const btn = section.previousElementSibling.querySelector('.collapse-btn');
    if (section.classList.contains('collapsed')) {{
        section.classList.remove('collapsed');
        btn.textContent = '−';
    }} else {{
        section.classList.add('collapsed');
        btn.textContent = '+';
    }}
}}

// Toggle service group and initialize DataTable if needed
function toggleServiceGroup(groupId) {{
    const group = document.getElementById(groupId);
    group.classList.toggle('expanded');
    
    // Initialize DataTable for this service if not already done
    if (group.classList.contains('expanded')) {{
        const table = group.querySelector('.service-datatable');
        if (table && !$.fn.DataTable.isDataTable(table)) {{
            $(table).DataTable({{
                pageLength: 10,
                lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
                order: [[4, 'asc']],
                dom: 'lfrtip',
                language: {{
                    search: "Search:",
                    lengthMenu: "Show _MENU_ entries"
                }}
            }});
        }}
    }}
}}

// Show/hide go-to-top button
window.addEventListener('scroll', function() {{
    const btn = document.querySelector('.go-to-top');
    if (window.scrollY > 300) {{
        btn.style.display = 'block';
    }} else {{
        btn.style.display = 'none';
    }}
}});

// Filter functionality - initialize on DOM ready
function initFilters() {{
    document.querySelectorAll('.filter-option').forEach(function(option) {{
        option.addEventListener('click', function(e) {{
            e.preventDefault();
            e.stopPropagation();
            this.classList.toggle('selected');
            const checkbox = this.querySelector('input');
            if (checkbox) {{
                checkbox.checked = this.classList.contains('selected');
            }}
            const checkmark = this.querySelector('.checkmark');
            if (checkmark) {{
                checkmark.textContent = this.classList.contains('selected') ? '✓' : '';
            }}
        }});
    }});
}}

function getSelectedFilters() {{
    const services = [];
    const accounts = [];
    const statuses = [];
    
    document.querySelectorAll('#service-filters .filter-option.selected').forEach(function(el) {{
        services.push(el.dataset.value);
    }});
    document.querySelectorAll('#account-items .dropdown-item.selected').forEach(function(el) {{
        accounts.push(el.dataset.value);
    }});
    document.querySelectorAll('#status-filters .filter-option.selected').forEach(function(el) {{
        statuses.push(el.dataset.value);
    }});
    
    return {{ services, accounts, statuses }};
}}

function applyFilters() {{
    const filters = getSelectedFilters();
    const table = $('#resourcesDataTable').DataTable();
    
    // Custom filter function for main table
    $.fn.dataTable.ext.search.pop(); // Remove previous filter
    $.fn.dataTable.ext.search.push(function(settings, data, dataIndex) {{
        // Only apply to main resources table
        if (settings.sTableId !== 'resourcesDataTable') {{
            return true;
        }}
        
        const account = data[0];
        const service = data[1];
        const statusCell = data[7];
        
        // Extract status text from the cell
        const statusMatch = statusCell.match(/>([^<]+)</);
        const status = statusMatch ? statusMatch[1] : statusCell;
        
        const accountMatch = filters.accounts.length === 0 || filters.accounts.includes(account);
        const serviceMatch = filters.services.length === 0 || filters.services.includes(service);
        const statusMatch2 = filters.statuses.length === 0 || filters.statuses.includes(status);
        
        return accountMatch && serviceMatch && statusMatch2;
    }});
    
    table.draw();
    
    // Filter service groups in By Service section
    document.querySelectorAll('.service-group').forEach(function(group) {{
        const serviceName = group.dataset.service || group.querySelector('.service-group-header strong').textContent;
        
        // Check if service matches filter
        if (filters.services.length > 0 && !filters.services.includes(serviceName)) {{
            group.style.display = 'none';
            return;
        }}
        
        group.style.display = '';
        
        // Filter rows within the service table
        const serviceTable = group.querySelector('.service-datatable');
        if (serviceTable) {{
            const rows = serviceTable.querySelectorAll('tbody tr');
            let visibleCount = 0;
            let statusCounts = {{ supported: 0, approaching: 0, extended: 0, out_of_support: 0 }};
            
            rows.forEach(function(row) {{
                const account = row.dataset.account || row.cells[0].textContent;
                const status = row.dataset.status || '';
                
                const accountMatch = filters.accounts.length === 0 || filters.accounts.includes(account);
                const statusMatch = filters.statuses.length === 0 || filters.statuses.includes(status);
                
                if (accountMatch && statusMatch) {{
                    row.style.display = '';
                    visibleCount++;
                    // Count by status
                    if (status === 'Supported') statusCounts.supported++;
                    else if (status === 'Approaching EOS') statusCounts.approaching++;
                    else if (status === 'Extended Support') statusCounts.extended++;
                    else if (status === 'Out of Support') statusCounts.out_of_support++;
                }} else {{
                    row.style.display = 'none';
                }}
            }});
            
            // Update the service group header counts
            const countSpan = group.querySelector('.service-count');
            if (countSpan) {{
                countSpan.textContent = visibleCount;
            }}
            
            // Update status badge counts in header
            const badges = group.querySelectorAll('.service-group-header .status-badge');
            if (badges.length >= 4) {{
                badges[0].textContent = statusCounts.supported;
                badges[1].textContent = statusCounts.approaching;
                badges[2].textContent = statusCounts.extended;
                badges[3].textContent = statusCounts.out_of_support;
            }}
            
            // Hide service group if no visible rows
            if (visibleCount === 0) {{
                group.style.display = 'none';
            }}
            
            // If DataTable is initialized, redraw it
            if ($.fn.DataTable.isDataTable(serviceTable)) {{
                $(serviceTable).DataTable().draw();
            }}
        }}
    }});
    
    // Update summary counts based on visible rows
    updateSummaryCounts(table);
}}

function updateSummaryCounts(table) {{
    let total = 0;
    let supported = 0;
    let approaching = 0;
    let extended = 0;
    let outOfSupport = 0;
    
    table.rows({{ search: 'applied' }}).every(function() {{
        total++;
        const data = this.data();
        const statusCell = data[7];
        
        if (statusCell.includes('status-supported')) supported++;
        else if (statusCell.includes('status-approaching')) approaching++;
        else if (statusCell.includes('status-extended')) extended++;
        else if (statusCell.includes('status-out-of-support')) outOfSupport++;
    }});
    
    // Update the summary cards
    const cards = document.querySelectorAll('.summary-card .count');
    if (cards.length >= 5) {{
        cards[0].textContent = total;
        cards[1].textContent = supported;
        cards[2].textContent = approaching;
        cards[3].textContent = extended;
        cards[4].textContent = outOfSupport;
    }}
}}

function resetFilters() {{
    // Select all filter options
    document.querySelectorAll('.filter-option').forEach(function(option) {{
        option.classList.add('selected');
        option.querySelector('input').checked = true;
        option.querySelector('.checkmark').textContent = '✓';
    }});
    
    // Reset account dropdown
    selectAllAccounts();
    
    // Clear DataTable filter and redraw
    const table = $('#resourcesDataTable').DataTable();
    $.fn.dataTable.ext.search.pop();
    table.draw();
    
    // Show all service groups and reset their rows
    document.querySelectorAll('.service-group').forEach(function(group) {{
        group.style.display = '';
        
        // Show all rows in service tables
        const serviceTable = group.querySelector('.service-datatable');
        if (serviceTable) {{
            serviceTable.querySelectorAll('tbody tr').forEach(function(row) {{
                row.style.display = '';
            }});
            
            // Reset counts from data attributes
            const badges = group.querySelectorAll('.service-group-header .status-badge');
            if (badges.length >= 4) {{
                badges[0].textContent = badges[0].dataset.count || badges[0].textContent;
                badges[1].textContent = badges[1].dataset.count || badges[1].textContent;
                badges[2].textContent = badges[2].dataset.count || badges[2].textContent;
                badges[3].textContent = badges[3].dataset.count || badges[3].textContent;
            }}
            
            // Recalculate total count
            const totalRows = serviceTable.querySelectorAll('tbody tr').length;
            const countSpan = group.querySelector('.service-count');
            if (countSpan) {{
                countSpan.textContent = totalRows;
            }}
            
            // Redraw DataTable if initialized
            if ($.fn.DataTable.isDataTable(serviceTable)) {{
                $(serviceTable).DataTable().draw();
            }}
        }}
    }});
    
    // Reset summary counts to original values
    const cards = document.querySelectorAll('.summary-card .count');
    if (cards.length >= 5) {{
        cards[0].textContent = '{report.total_resources}';
        cards[1].textContent = '{report.total_counts.get(SupportStatus.SUPPORTED, 0)}';
        cards[2].textContent = '{report.total_counts.get(SupportStatus.APPROACHING_EOS, 0)}';
        cards[3].textContent = '{report.total_counts.get(SupportStatus.EXTENDED_SUPPORT, 0)}';
        cards[4].textContent = '{report.total_counts.get(SupportStatus.OUT_OF_SUPPORT, 0)}';
    }}
}}

// Account dropdown functions
function toggleAccountDropdown() {{
    const dropdown = document.getElementById('account-dropdown');
    dropdown.classList.toggle('open');
}}

function filterAccountOptions() {{
    const searchText = document.getElementById('account-search').value.toLowerCase();
    const items = document.querySelectorAll('#account-items .dropdown-item');
    
    items.forEach(function(item) {{
        const text = item.querySelector('.item-text').textContent.toLowerCase();
        if (text.includes(searchText)) {{
            item.classList.remove('hidden');
        }} else {{
            item.classList.add('hidden');
        }}
    }});
}}

function selectAllAccounts() {{
    const items = document.querySelectorAll('#account-items .dropdown-item');
    items.forEach(function(item) {{
        item.classList.add('selected');
    }});
    updateAccountCount();
}}

function deselectAllAccounts() {{
    const items = document.querySelectorAll('#account-items .dropdown-item');
    items.forEach(function(item) {{
        item.classList.remove('selected');
    }});
    updateAccountCount();
}}

function updateAccountCount() {{
    const total = document.querySelectorAll('#account-items .dropdown-item').length;
    const selected = document.querySelectorAll('#account-items .dropdown-item.selected').length;
    document.getElementById('account-count').textContent = selected;
}}

function initAccountDropdown() {{
    // Toggle item selection on click
    document.querySelectorAll('#account-items .dropdown-item').forEach(function(item) {{
        item.addEventListener('click', function(e) {{
            e.stopPropagation();
            this.classList.toggle('selected');
            updateAccountCount();
        }});
    }});
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {{
        const dropdown = document.getElementById('account-dropdown');
        if (dropdown && !dropdown.contains(e.target)) {{
            dropdown.classList.remove('open');
        }}
    }});
}}

// Loading state management
var loadingSteps = 0;
var totalSteps = 3;

function updateLoadingStatus(message) {{
    var loadingText = document.getElementById('loading-text');
    if (loadingText) loadingText.textContent = message;
}}

function stepComplete() {{
    loadingSteps++;
    if (loadingSteps >= totalSteps) {{
        var spinner = document.getElementById('header-spinner');
        var loadingText = document.getElementById('loading-text');
        if (spinner) spinner.classList.add('hidden');
        if (loadingText) loadingText.textContent = 'Ready';
        setTimeout(function() {{
            var loadingStatus = document.querySelector('.loading-status');
            if (loadingStatus) loadingStatus.style.opacity = '0';
        }}, 1000);
    }}
}}

// Lazy load charts
var chartsInitialized = false;
var serviceLabelsArray = {service_labels};
var accountLabelsArray = {account_labels};

function initChartsLazy() {{
    if (chartsInitialized) return;
    chartsInitialized = true;
    
    requestAnimationFrame(function() {{
        new Chart(document.getElementById('serviceChart'), {{
            type: 'bar',
            data: {{
                labels: {service_labels},
                datasets: [
                    {{ label: 'Supported', data: {service_supported}, backgroundColor: '#66bb6a' }},
                    {{ label: 'Approaching EOS', data: {service_approaching}, backgroundColor: '#ffa726' }},
                    {{ label: 'Extended Support', data: {service_extended}, backgroundColor: '#42a5f5' }},
                    {{ label: 'Out of Support', data: {service_out}, backgroundColor: '#ef5350' }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true }} }},
                onClick: function(event, elements) {{
                    if (elements.length > 0) {{
                        var index = elements[0].index;
                        var datasetIndex = elements[0].datasetIndex;
                        var service = serviceLabelsArray[index];
                        var allResources = serviceResourcesData[service] || [];
                        var statusKey = statusLabelsMap[datasetIndex];
                        // Filter resources by the clicked status
                        var resources = allResources.filter(function(r) {{ return r.status === statusKey; }});
                        var statusName = statusDisplayNames[statusKey];
                        showChartResources(statusName + ' Resources for ' + service, resources, {{ services: [service], statuses: [statusKey] }});
                    }}
                }},
                plugins: {{
                    tooltip: {{
                        callbacks: {{
                            afterBody: function() {{ return 'Click to view resources'; }}
                        }}
                    }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('accountChart'), {{
            type: 'bar',
            data: {{
                labels: {account_labels},
                datasets: [
                    {{ label: 'Supported', data: {account_supported}, backgroundColor: '#66bb6a' }},
                    {{ label: 'Approaching EOS', data: {account_approaching}, backgroundColor: '#ffa726' }},
                    {{ label: 'Extended Support', data: {account_extended}, backgroundColor: '#42a5f5' }},
                    {{ label: 'Out of Support', data: {account_out}, backgroundColor: '#ef5350' }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true }} }},
                onClick: function(event, elements) {{
                    if (elements.length > 0) {{
                        var index = elements[0].index;
                        var datasetIndex = elements[0].datasetIndex;
                        var account = accountLabelsArray[index];
                        var allResources = accountResourcesData[account] || [];
                        var statusKey = statusLabelsMap[datasetIndex];
                        // Filter resources by the clicked status
                        var resources = allResources.filter(function(r) {{ return r.status === statusKey; }});
                        var statusName = statusDisplayNames[statusKey];
                        showChartResources(statusName + ' Resources for Account ' + account, resources, {{ accounts: [account], statuses: [statusKey] }});
                    }}
                }},
                plugins: {{
                    tooltip: {{
                        callbacks: {{
                            afterBody: function() {{ return 'Click to view resources'; }}
                        }}
                    }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('statusPieChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Supported', 'Approaching EOS', 'Extended Support', 'Out of Support'],
                datasets: [{{ data: {status_values}, backgroundColor: ['#66bb6a', '#ffa726', '#42a5f5', '#ef5350'] }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                onClick: function(event, elements) {{
                    if (elements.length > 0) {{
                        var index = elements[0].index;
                        var statusKey = statusLabelsMap[index];
                        var resources = statusResourcesData[statusKey] || [];
                        showChartResources(statusDisplayNames[statusKey] + ' Resources', resources, {{ statuses: [statusKey] }});
                    }}
                }},
                plugins: {{
                    tooltip: {{
                        callbacks: {{
                            afterBody: function() {{ return 'Click to view resources'; }}
                        }}
                    }}
                }}
            }}
        }});
        
        new Chart(document.getElementById('servicePieChart'), {{
            type: 'pie',
            data: {{
                labels: {service_labels},
                datasets: [{{ data: {service_totals}, backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7', '#fa709a', '#fee140', '#30cfd0', '#330867', '#a8edea', '#fed6e3', '#5ee7df'] }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                onClick: function(event, elements) {{
                    if (elements.length > 0) {{
                        var index = elements[0].index;
                        var service = serviceLabelsArray[index];
                        var resources = serviceResourcesData[service] || [];
                        showChartResources('Resources for ' + service, resources, {{ services: [service] }});
                    }}
                }},
                plugins: {{
                    tooltip: {{
                        callbacks: {{
                            afterBody: function() {{ return 'Click to view resources'; }}
                        }}
                    }}
                }}
            }}
        }});
        
        stepComplete();
    }});
}}

// Initialize with progressive loading
$(document).ready(function() {{
    initFilters();
    initAccountDropdown();
    updateLoadingStatus('Initializing table...');
    
    // Initialize DataTable with deferred rendering
    setTimeout(function() {{
        $('#resourcesDataTable').DataTable({{
            pageLength: 25,
            order: [[5, 'asc']],
            dom: 'Bfrtip',
            buttons: ['copy', 'csv', 'excel'],
            deferRender: true,
            language: {{ search: "Search:", lengthMenu: "Show _MENU_ entries" }}
        }});
        stepComplete();
        
        // Load charts after table
        updateLoadingStatus('Loading charts...');
        setTimeout(function() {{
            initChartsLazy();
            
            // Timeline chart init
            updateLoadingStatus('Loading timeline...');
            setTimeout(function() {{
                if (typeof initTimelineChart === 'function') initTimelineChart();
                stepComplete();
            }}, 50);
        }}, 50);
    }}, 10);
}});
</script>"""
