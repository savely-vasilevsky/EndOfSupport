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
        return f"""<div class="header">
    <h1>🔧 AWS End-of-Support Report</h1>
    <span class="subtitle">Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
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
        
        # Generate account filter options (all selected by default)
        account_options = []
        for account in accounts:
            account_options.append(
                f'<label class="filter-option selected" data-filter="account" data-value="{self._escape_html(account)}">'
                f'<input type="checkbox" checked><span class="checkmark">✓</span>{self._escape_html(account)}</label>'
            )
        account_options_html = '\n'.join(account_options)
        
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
        <div class="filter-group">
            <label>Service</label>
            <div class="filter-options" id="service-filters">
                {service_options_html}
            </div>
        </div>
        <div class="filter-group">
            <label>Account</label>
            <div class="filter-options" id="account-filters">
                {account_options_html}
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
    <div class="summary-cards">
        <div class="summary-card total">
            <div class="count">{report.total_resources}</div>
            <div class="label">Total Resources</div>
        </div>
        <div class="summary-card supported">
            <div class="count">{status_counts.get(SupportStatus.SUPPORTED, 0)}</div>
            <div class="label">Supported</div>
        </div>
        <div class="summary-card approaching">
            <div class="count">{status_counts.get(SupportStatus.APPROACHING_EOS, 0)}</div>
            <div class="label">Approaching EOS</div>
        </div>
        <div class="summary-card extended">
            <div class="count">{status_counts.get(SupportStatus.EXTENDED_SUPPORT, 0)}</div>
            <div class="label">Extended Support</div>
        </div>
        <div class="summary-card out-of-support">
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
        <div class="chart-row">
            <div>
                <h3>By Service</h3>
                <div class="chart-container">
                    <canvas id="serviceChart"></canvas>
                </div>
            </div>
            <div>
                <h3>By Account</h3>
                <div class="chart-container">
                    <canvas id="accountChart"></canvas>
                </div>
            </div>
        </div>
        <div class="chart-row">
            <div>
                <h3>Overall Status Distribution</h3>
                <div class="chart-container">
                    <canvas id="statusPieChart"></canvas>
                </div>
            </div>
            <div>
                <h3>Resources by Service</h3>
                <div class="chart-container">
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
        
        return f"""<div id="timeline-section" class="section">
    <h2>Support Timeline
        <button class="collapse-btn" onclick="toggleSection('timeline-content')">−</button>
    </h2>
    <div id="timeline-content" class="collapsible-content">
        <p>End-of-Support events aggregated by month:</p>
        <div class="chart-container" style="height: 350px;">
            <canvas id="timelineChart"></canvas>
        </div>
        <script>
            function initTimelineChart() {{
                var timelineCtx = document.getElementById('timelineChart');
                if (timelineCtx && !timelineCtx.chart) {{
                    timelineCtx.chart = new Chart(timelineCtx, {{
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
                            plugins: {{ title: {{ display: true, text: 'Resources by End-of-Support Month' }}, legend: {{ position: 'top' }} }},
                            scales: {{ x: {{ stacked: true, title: {{ display: true, text: 'End-of-Support Month' }} }}, y: {{ stacked: true, beginAtZero: true, title: {{ display: true, text: 'Number of Resources' }} }} }}
                        }}
                    }});
                }}
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
        service_groups = []
        service_table_ids = []
        
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                # Count resources by status for this service
                status_counts = {
                    'supported': 0,
                    'approaching': 0,
                    'extended': 0,
                    'out_of_support': 0
                }
                resources_list = []
                
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        for resource in version_group.resources:
                            status_key = self._status_to_key(resource.status)
                            status_counts[status_key] += 1
                            resources_list.append({
                                'account': account_name,
                                'engine': engine_name or 'N/A',
                                'version': version_name,
                                'name': resource.resource_name or resource.resource_arn or 'N/A',
                                'eos': resource.end_of_support.strftime('%Y-%m-%d') if resource.end_of_support else 'N/A',
                                'status': resource.status
                            })
                
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
        
        return f"""<script>
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
    document.querySelectorAll('#account-filters .filter-option.selected').forEach(function(el) {{
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
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true }} }} }}
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
            options: {{ responsive: true, maintainAspectRatio: false, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, beginAtZero: true }} }} }}
        }});
        
        new Chart(document.getElementById('statusPieChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Supported', 'Approaching EOS', 'Extended Support', 'Out of Support'],
                datasets: [{{ data: {status_values}, backgroundColor: ['#66bb6a', '#ffa726', '#42a5f5', '#ef5350'] }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});
        
        new Chart(document.getElementById('servicePieChart'), {{
            type: 'pie',
            data: {{
                labels: {service_labels},
                datasets: [{{ data: {service_totals}, backgroundColor: ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7', '#fa709a', '#fee140', '#30cfd0', '#330867', '#a8edea', '#fed6e3', '#5ee7df'] }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});
        
        stepComplete();
    }});
}}

// Initialize with progressive loading
$(document).ready(function() {{
    initFilters();
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
