"""HTML formatter for EndOfSupportTool.

Generates an interactive HTML report with collapsible sections,
data tables, and charts similar to AWS TAM reports.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Optional

# Handle imports for both package and frozen executable modes
try:
    from .models import Report, Resource, SupportStatus
    from . import __version__
except ImportError:
    from models import Report, Resource, SupportStatus
    __version__ = "2.4.0"


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
        SupportStatus.SUPPORTED: ("#c8e6c9", "#1b5e20"),  # (bg, text) - Green
        SupportStatus.APPROACHING_EOS: ("#fff9c4", "#f57f17"),  # Yellow/Orange
        SupportStatus.EXTENDED_SUPPORT_YEAR_1: ("#bbdefb", "#0d47a1"),  # Light Blue
        SupportStatus.EXTENDED_SUPPORT_YEAR_2: ("#90caf9", "#1565c0"),  # Medium Blue
        SupportStatus.EXTENDED_SUPPORT_YEAR_3: ("#64b5f6", "#0d47a1"),  # Darker Blue
        SupportStatus.OUT_OF_SUPPORT: ("#ffcdd2", "#b71c1c"),  # Red
    }
    
    STATUS_LABELS = {
        SupportStatus.SUPPORTED: "Supported",
        SupportStatus.APPROACHING_EOS: "Approaching EOS",
        SupportStatus.EXTENDED_SUPPORT_YEAR_1: "Extended Support Y1",
        SupportStatus.EXTENDED_SUPPORT_YEAR_2: "Extended Support Y2",
        SupportStatus.EXTENDED_SUPPORT_YEAR_3: "Extended Support Y3",
        SupportStatus.OUT_OF_SUPPORT: "Out of Support",
    }
    
    # AWS Documentation links for each service
    # Maps service name (as it appears in the report) to documentation URL and description
    AWS_DOCS_LINKS = {
        # Compute Services
        "Lambda": {
            "url": "https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html",
            "title": "Runtime Deprecation Policy",
            "description": "All runtimes with deprecation dates and block function create/update dates"
        },
        "EKS": {
            "url": "https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html",
            "title": "Kubernetes Versions",
            "description": "Standard support (14 months) and extended support (12 months) dates"
        },
        # Database Services
        "RDS": {
            "url": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-versions.html",
            "title": "Extended Support Versions",
            "description": "RDS Extended Support dates by engine"
        },
        "Aurora": {
            "url": "https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.VersionPolicy.html",
            "title": "Aurora Version Policy",
            "description": "Long-term support (LTS) versions and Extended Support information"
        },
        "DocumentDB": {
            "url": "https://docs.aws.amazon.com/documentdb/latest/developerguide/document-db-support-dates.html",
            "title": "Engine Version Support Dates",
            "description": "Standard and extended support dates with pricing information"
        },
        "Neptune": {
            "url": "https://docs.aws.amazon.com/neptune/latest/userguide/engine-releases.html",
            "title": "Engine Releases",
            "description": "Complete list of releases with end-of-life dates"
        },
        "ElastiCache": {
            "url": "https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/engine-versions.html",
            "title": "Engine Versions and Upgrading",
            "description": "Version information for Valkey, Redis OSS, and Memcached"
        },
        # Analytics & Search Services
        "OpenSearch": {
            "url": "https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-migration.html",
            "title": "Upgrading Domains",
            "description": "Version upgrade paths and supported versions"
        },
        "OpenSearch Service": {
            "url": "https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-migration.html",
            "title": "Upgrading Domains",
            "description": "Version upgrade paths and supported versions"
        },
        # Messaging Services
        "MSK": {
            "url": "https://docs.aws.amazon.com/msk/latest/developerguide/supported-kafka-versions.html",
            "title": "Supported Kafka Versions",
            "description": "List of supported Apache Kafka versions"
        },
        "Managed Streaming for Apache Kafka": {
            "url": "https://docs.aws.amazon.com/msk/latest/developerguide/supported-kafka-versions.html",
            "title": "Supported Kafka Versions",
            "description": "List of supported Apache Kafka versions"
        },
        "MQ": {
            "url": "https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/activemq-version-management.html",
            "title": "ActiveMQ Version Management",
            "description": "Engine versions with end-of-support dates and automatic upgrade policy"
        },
        "Amazon MQ": {
            "url": "https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/activemq-version-management.html",
            "title": "ActiveMQ Version Management",
            "description": "Engine versions with end-of-support dates and automatic upgrade policy"
        },
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

    def _generate_html(self, report: Report, include_version_details: bool = True) -> str:
        """Generate the complete HTML document."""
        version_details_section = self._generate_version_details_section(report) if include_version_details else ""
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
    {self._generate_menu(include_version_details)}
    {self._generate_filter_bar(report)}
    <div class="container">
        {self._generate_summary_section(report)}
        {self._generate_status_breakdown_section(report)}
        {self._generate_resources_table(report, include_version_details)}
        {self._generate_timeline_section(report)}
        {self._generate_by_service_section(report)}
        {version_details_section}
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

.header .header-info {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-left: 20px;
}

.header .subtitle {
    color: #aab7b8;
    font-size: 14px;
}

.header .generation-params {
    padding: 4px 12px;
    background: rgba(255, 153, 0, 0.2);
    border-radius: 4px;
    color: #ffb84d;
    font-size: 12px;
    font-weight: 500;
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

.summary-card.extended-year-1 {
    background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%);
}

.summary-card.extended-year-2 {
    background: linear-gradient(135deg, #1565c0 0%, #1976d2 100%);
}

.summary-card.extended-year-3 {
    background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%);
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
.status-extended-year-1 { background-color: #bbdefb; color: #0d47a1; }
.status-extended-year-2 { background-color: #90caf9; color: #1565c0; }
.status-extended-year-3 { background-color: #64b5f6; color: #0d47a1; }
.status-out-of-support { background-color: #ffcdd2; color: #b71c1c; }

/* Support Lifecycle Timeline Bar */
.lifecycle-bar {
    position: relative;
    display: flex;
    height: 24px;
    border-radius: 4px;
    overflow: visible;
    background: #f0f0f0;
    font-size: 10px;
    min-width: 250px;
}

.lifecycle-segment {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    border-right: 1px solid rgba(255,255,255,0.5);
}

.lifecycle-segment:last-of-type {
    border-right: none;
}

.lifecycle-segment.supported {
    background: linear-gradient(135deg, #66bb6a, #43a047);
    color: white;
}

.lifecycle-segment.ext-y1 {
    background: linear-gradient(135deg, #42a5f5, #1e88e5);
    color: white;
}

.lifecycle-segment.ext-y2 {
    background: linear-gradient(135deg, #ffa726, #fb8c00);
    color: white;
}

.lifecycle-segment.ext-y3 {
    background: linear-gradient(135deg, #ef5350, #e53935);
    color: white;
}

.lifecycle-segment.out-of-support {
    background: linear-gradient(135deg, #78909c, #546e7a);
    color: white;
}

.lifecycle-marker {
    position: absolute;
    top: -8px;
    transform: translateX(-50%);
    font-size: 14px;
    color: #d32f2f;
    font-weight: bold;
    text-shadow: 0 0 2px white, 0 0 2px white;
    z-index: 10;
    cursor: help;
}

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
    min-width: 1200px;
    border-collapse: collapse;
}

table.dataTable thead th {
    background-color: #f5f5f5;
    border-bottom: 2px solid #ddd;
    padding: 12px 8px;
    text-align: left;
    font-weight: 600;
    position: relative;
    white-space: nowrap;
}

/* Column resizer handle */
table.dataTable thead th .col-resizer {
    position: absolute;
    right: -4px;
    top: 0;
    width: 10px;
    height: 100%;
    cursor: col-resize;
    background: transparent;
    z-index: 100;
}

table.dataTable thead th .col-resizer:hover,
table.dataTable thead th .col-resizer.resizing {
    background: #ff9900;
}

table.dataTable tbody td {
    padding: 10px 8px;
    border-bottom: 1px solid #eee;
    white-space: nowrap;
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
    overflow-x: auto;
}

.service-group.expanded .service-group-content {
    display: block;
}

/* Table wrapper for horizontal scrolling */
.table-wrapper {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-bottom: 10px;
}

.table-wrapper::-webkit-scrollbar {
    height: 8px;
}

.table-wrapper::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
}

.table-wrapper::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
}

.table-wrapper::-webkit-scrollbar-thumb:hover {
    background: #a1a1a1;
}

/* DataTables horizontal scroll styling */
.dataTables_wrapper {
    overflow-x: auto;
    width: 100%;
}

.dataTables_scrollHead,
.dataTables_scrollBody {
    overflow-x: auto !important;
}

.dataTables_scrollBody::-webkit-scrollbar {
    height: 10px;
}

.dataTables_scrollBody::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
}

.dataTables_scrollBody::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
}

.dataTables_scrollBody::-webkit-scrollbar-thumb:hover {
    background: #a1a1a1;
}

/* Ensure table columns don't collapse */
table.dataTable th,
table.dataTable td {
    min-width: 80px;
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

.filter-bar .filter-option.status-extended-year-1.selected {
    background-color: #1976d2;
    border-color: #1976d2;
}

.filter-bar .filter-option.status-extended-year-2.selected {
    background-color: #1565c0;
    border-color: #1565c0;
}

.filter-bar .filter-option.status-extended-year-3.selected {
    background-color: #0d47a1;
    border-color: #0d47a1;
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

/* Version Details Section Styles */
.version-details-link {
    color: #0563C1;
    text-decoration: none;
    font-weight: 500;
}

.version-details-link:hover {
    text-decoration: underline;
}

.version-details-controls {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
}

.version-details-controls button {
    padding: 8px 16px;
    border: 1px solid #ccc;
    border-radius: 4px;
    background: #f5f5f5;
    cursor: pointer;
    font-size: 13px;
}

.version-details-controls button:hover {
    background: #e0e0e0;
}

.version-detail-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-bottom: 15px;
    overflow: hidden;
    transition: box-shadow 0.2s;
}

.version-detail-card:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.version-detail-header {
    background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
    padding: 15px 20px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #e0e0e0;
}

.version-detail-header:hover {
    background: linear-gradient(135deg, #e8e8e8 0%, #ddd 100%);
}

.version-detail-header h3 {
    margin: 0;
    color: #232f3e;
    font-size: 16px;
}

.aws-docs-link {
    font-size: 12px;
    font-weight: normal;
    color: #0073bb;
    text-decoration: none;
    margin-left: 10px;
    padding: 3px 8px;
    background: #e8f4fc;
    border-radius: 4px;
    transition: background 0.2s;
}

.aws-docs-link:hover {
    background: #d1e8f7;
    text-decoration: underline;
}

.version-detail-header .stats {
    display: flex;
    gap: 10px;
    align-items: center;
}

.version-detail-header .stat-badge {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}

.version-detail-header .expand-icon {
    font-size: 18px;
    color: #666;
    transition: transform 0.2s;
}

.version-detail-card.expanded .expand-icon {
    transform: rotate(180deg);
}

.version-detail-content {
    padding: 0;
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease-out, padding 0.3s ease-out;
}

.version-detail-card.expanded .version-detail-content {
    padding: 20px;
    max-height: 2000px;
}

.version-detail-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    margin-bottom: 20px;
}

.version-detail-summary .summary-item {
    background: #f9f9f9;
    padding: 12px;
    border-radius: 6px;
    text-align: center;
}

.version-detail-summary .summary-item .count {
    font-size: 24px;
    font-weight: bold;
    color: #232f3e;
}

.version-detail-summary .summary-item .label {
    font-size: 12px;
    color: #666;
}

.version-detail-table {
    width: 100%;
    border-collapse: collapse;
    min-width: 600px;
}

.version-detail-table th {
    background: #f5f5f5;
    padding: 10px;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid #ddd;
    white-space: nowrap;
}

.version-detail-table td {
    padding: 10px;
    border-bottom: 1px solid #eee;
    white-space: nowrap;
}

.version-detail-table tr:hover {
    background: #f9f9f9;
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
    <h1>🔧 AWS End-of-Support Report <span style="font-size: 14px; font-weight: normal; opacity: 0.8;">v{__version__}</span></h1>
    <div class="header-info">
        <span class="subtitle">Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
        {params_html}
    </div>
    <div class="loading-status">
        <span id="loading-text">Loading...</span>
        <div id="header-spinner" class="header-spinner"></div>
    </div>
</div>"""

    def _generate_menu(self, include_version_details: bool = True) -> str:
        """Generate the navigation menu."""
        version_details_link = '<li><a href="#version-details-section" onclick="scrollToSection(event)">Version Details</a></li>' if include_version_details else ""
        return f"""<ul id="menuBar">
    <li><a href="#summary-section" onclick="scrollToSection(event)">Summary</a></li>
    <li><a href="#status-breakdown" onclick="scrollToSection(event)">Status Breakdown</a></li>
    <li><a href="#resources-table" onclick="scrollToSection(event)">All Resources</a></li>
    <li><a href="#timeline-section" onclick="scrollToSection(event)">Timeline</a></li>
    <li><a href="#by-service-section" onclick="scrollToSection(event)">By Service</a></li>
    {version_details_link}
    <li><a href="#" onclick="showReportHelp(event)" style="color: #ff9900;">Help</a></li>
</ul>
<button class="go-to-top" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})">↑</button>"""

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
            <label class="filter-option status-extended-year-1 selected" data-filter="status" data-value="Extended Support Y1">
                <input type="checkbox" checked><span class="checkmark">✓</span>Extended Support Y1</label>
            <label class="filter-option status-extended-year-2 selected" data-filter="status" data-value="Extended Support Y2">
                <input type="checkbox" checked><span class="checkmark">✓</span>Extended Support Y2</label>
            <label class="filter-option status-extended-year-3 selected" data-filter="status" data-value="Extended Support Y3">
                <input type="checkbox" checked><span class="checkmark">✓</span>Extended Support Y3</label>
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
        
        # Calculate total extended support count (sum of all 3 years)
        extended_total = (
            status_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_1, 0) +
            status_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_2, 0) +
            status_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_3, 0)
        )
        
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
        <div class="summary-card extended-year-1" onclick="showStatusResources('extended_year_1')" onmouseenter="showSummaryTooltip(event, 'extended_year_1')" onmousemove="positionSummaryTooltip(event)" onmouseleave="hideSummaryTooltip()">
            <div class="count">{status_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_1, 0)}</div>
            <div class="label">Extended Support Y1</div>
        </div>
        <div class="summary-card extended-year-2" onclick="showStatusResources('extended_year_2')" onmouseenter="showSummaryTooltip(event, 'extended_year_2')" onmousemove="positionSummaryTooltip(event)" onmouseleave="hideSummaryTooltip()">
            <div class="count">{status_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_2, 0)}</div>
            <div class="label">Extended Support Y2</div>
        </div>
        <div class="summary-card extended-year-3" onclick="showStatusResources('extended_year_3')" onmouseenter="showSummaryTooltip(event, 'extended_year_3')" onmousemove="positionSummaryTooltip(event)" onmouseleave="hideSummaryTooltip()">
            <div class="count">{status_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_3, 0)}</div>
            <div class="label">Extended Support Y3</div>
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
                'extended_year_1': 0,
                'extended_year_2': 0,
                'extended_year_3': 0,
                'out_of_support': 0
            }
            for service_name, service_group in account_group.services.items():
                if service_name not in service_data:
                    service_data[service_name] = {
                        'supported': 0,
                        'approaching': 0,
                        'extended_year_1': 0,
                        'extended_year_2': 0,
                        'extended_year_3': 0,
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
            SupportStatus.EXTENDED_SUPPORT_YEAR_1: 'extended_year_1',
            SupportStatus.EXTENDED_SUPPORT_YEAR_2: 'extended_year_2',
            SupportStatus.EXTENDED_SUPPORT_YEAR_3: 'extended_year_3',
            SupportStatus.OUT_OF_SUPPORT: 'out_of_support'
        }
        return mapping.get(status, 'supported')

    def _generate_resources_table(self, report: Report, include_version_details: bool = True) -> str:
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
                            resource_arn = resource.resource_arn or 'N/A'
                            
                            # Extended support dates
                            ext_start = resource.extended_support_start.strftime('%Y-%m-%d') if resource.extended_support_start else 'N/A'
                            ext_end = resource.extended_support_end.strftime('%Y-%m-%d') if resource.extended_support_end else 'N/A'
                            
                            # Cost with star (*) for Approaching EOS (future cost if not upgraded)
                            # Don't show cost for Supported status (no extended support cost applies)
                            monthly_cost = ''
                            annual_cost = ''
                            if resource.status != SupportStatus.SUPPORTED:
                                monthly_cost = resource.est_monthly_ext_support_cost or ''
                                annual_cost = resource.est_annual_ext_support_cost or ''
                                if resource.status == SupportStatus.APPROACHING_EOS and monthly_cost:
                                    monthly_cost = f"{monthly_cost}*"
                                    annual_cost = f"{annual_cost}*" if annual_cost else ""
                            
                            # Generate version details link
                            version_details_cell = ""
                            if include_version_details:
                                anchor_id = self._get_version_details_anchor_id(service_name, engine_name)
                                display_name = f"{service_name}_{engine_name}" if engine_name and engine_name != "N/A" else service_name
                                # Sanitize display name for HTML
                                display_name = display_name.replace(" ", "_").replace("/", "_")[:30]
                                version_details_cell = f'<td><a href="#version-detail-{anchor_id}" class="version-details-link" onclick="scrollToVersionDetail(event, \'{anchor_id}\')">See {display_name}</a></td>'
                            
                            rows.append(f"""<tr>
                                <td>{self._escape_html(account_name)}</td>
                                <td>{self._escape_html(service_name)}</td>
                                <td>{self._escape_html(engine_name or 'N/A')}</td>
                                <td>{self._escape_html(version_name)}</td>
                                <td>{self._escape_html(resource.resource_name or 'N/A')}</td>
                                <td title="{self._escape_html(resource_arn)}" style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{self._escape_html(resource_arn)}</td>
                                <td>{eos_date}</td>
                                <td>{days_to_eos}</td>
                                <td><span class="status-badge {status_class}">{status_label}</span></td>
                                <td>{ext_start}</td>
                                <td>{ext_end}</td>
                                <td>{self._escape_html(monthly_cost)}</td>
                                <td>{self._escape_html(annual_cost)}</td>
                                {version_details_cell}
                            </tr>""")
        
        rows_html = '\n'.join(rows)
        
        # Add Version Details column header if enabled
        version_details_header = "<th>Version Details</th>" if include_version_details else ""
        
        return f"""<div id="resources-table" class="section">
    <h2>All Resources
        <button class="collapse-btn" onclick="toggleSection('resources-table-content')">−</button>
    </h2>
    <div id="resources-table-content" class="collapsible-content">
        <div class="table-wrapper">
            <table id="resourcesDataTable" class="display">
                <thead>
                    <tr>
                        <th>Account</th>
                        <th>Service</th>
                        <th>Engine</th>
                        <th>Version</th>
                        <th>Resource</th>
                        <th>ARN</th>
                        <th>End of Support</th>
                        <th>Days to EOS</th>
                        <th>Status</th>
                        <th>Ext. Support Start</th>
                        <th>Ext. Support End</th>
                        <th>Est. Monthly Cost</th>
                        <th>Est. Annual Cost</th>
                        {version_details_header}
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>
</div>"""
    
    def _get_version_details_anchor_id(self, service_name: str, engine_name: str) -> str:
        """Generate a safe anchor ID for version details section."""
        engine = engine_name if engine_name and engine_name != "N/A" else ""
        combined = f"{service_name}_{engine}" if engine else service_name
        # Sanitize for HTML ID: lowercase, replace spaces and special chars
        safe_id = combined.lower().replace(" ", "-").replace("/", "-").replace(".", "-").replace(":", "-")
        return safe_id[:50]  # Limit length

    def _get_status_class(self, status: SupportStatus) -> str:
        """Get CSS class for status."""
        mapping = {
            SupportStatus.SUPPORTED: 'status-supported',
            SupportStatus.APPROACHING_EOS: 'status-approaching',
            SupportStatus.EXTENDED_SUPPORT_YEAR_1: 'status-extended-year-1',
            SupportStatus.EXTENDED_SUPPORT_YEAR_2: 'status-extended-year-2',
            SupportStatus.EXTENDED_SUPPORT_YEAR_3: 'status-extended-year-3',
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

    def _generate_lifecycle_timeline_bar(self, eos_date: Optional[date], ext_start: Optional[date], 
                                          ext_y1_start: Optional[date], ext_y3_start: Optional[date],
                                          ext_end: Optional[date]) -> str:
        """Generate a visual support lifecycle timeline bar showing current position.
        
        The bar shows: Supported | Ext Y1 | Ext Y2 | Ext Y3 | Out of Support
        with a marker showing where TODAY falls on the timeline.
        
        Args:
            eos_date: End of standard support date
            ext_start: Extended support start date
            ext_y1_start: Extended support Year 1 start date
            ext_y3_start: Extended support Year 3 start date
            ext_end: Extended support end date
            
        Returns:
            HTML string for the timeline bar
        """
        from datetime import date as date_type, timedelta
        today = date_type.today()
        
        def safe_add_years(d: date_type, years: int) -> date_type:
            """Safely add/subtract years, handling leap year edge cases."""
            try:
                return date_type(d.year + years, d.month, d.day)
            except ValueError:
                # Handle Feb 29 -> Feb 28 for non-leap years
                return date_type(d.year + years, d.month, d.day - 1)
        
        def safe_add_months(d: date_type, months: int) -> date_type:
            """Safely add/subtract months, handling edge cases."""
            new_month = d.month + months
            new_year = d.year
            while new_month > 12:
                new_month -= 12
                new_year += 1
            while new_month < 1:
                new_month += 12
                new_year -= 1
            # Handle day overflow (e.g., Jan 31 + 1 month = Feb 28)
            import calendar
            max_day = calendar.monthrange(new_year, new_month)[1]
            return date_type(new_year, new_month, min(d.day, max_day))
        
        # If no dates available, show a simple "No data" bar
        if not eos_date and not ext_start and not ext_end:
            return '<div class="lifecycle-bar"><div class="lifecycle-segment supported" style="width: 100%;" title="No lifecycle data available">No data</div></div>'
        
        # Calculate Year 2 start (1 year after Y1 start)
        ext_y2_start = None
        if ext_y1_start and not ext_y3_start:
            # If no Y3, calculate Y2 as Y1 + 1 year
            ext_y2_start = safe_add_years(ext_y1_start, 1)
        elif ext_y1_start and ext_y3_start:
            # Y2 is between Y1 and Y3
            ext_y2_start = safe_add_years(ext_y1_start, 1)
        
        # Determine the timeline range
        # Start from 1 year before EOS (or today if no EOS)
        # End at ext_end + 6 months (or 2 years after EOS if no ext_end)
        if eos_date:
            timeline_start = safe_add_years(eos_date, -1)
        else:
            timeline_start = safe_add_years(today, -1)
        
        if ext_end:
            timeline_end = safe_add_months(ext_end, 6)
        elif eos_date:
            timeline_end = safe_add_years(eos_date, 2)
        else:
            timeline_end = safe_add_years(today, 2)
        
        total_days = (timeline_end - timeline_start).days
        if total_days <= 0:
            total_days = 365  # Fallback
        
        # Calculate segment widths as percentages
        segments = []
        
        # Supported segment (from timeline_start to eos_date or ext_start)
        supported_end = eos_date or ext_start or timeline_end
        supported_width = max(0, (supported_end - timeline_start).days) / total_days * 100
        if supported_width > 0:
            segments.append({
                'class': 'supported',
                'width': supported_width,
                'label': 'Supported',
                'tooltip': f'Standard Support (until {supported_end.strftime("%Y-%m-%d")})'
            })
        
        # Extended Support Year 1
        if ext_y1_start or ext_start:
            y1_start = ext_y1_start or ext_start
            y1_end = ext_y2_start or ext_y3_start or ext_end or safe_add_years(y1_start, 1)
            y1_width = max(0, (y1_end - y1_start).days) / total_days * 100
            if y1_width > 0:
                segments.append({
                    'class': 'ext-y1',
                    'width': y1_width,
                    'label': 'Y1',
                    'tooltip': f'Extended Support Year 1 ({y1_start.strftime("%Y-%m-%d")} to {y1_end.strftime("%Y-%m-%d")})'
                })
        
        # Extended Support Year 2
        if ext_y2_start:
            y2_end = ext_y3_start or ext_end or safe_add_years(ext_y2_start, 1)
            y2_width = max(0, (y2_end - ext_y2_start).days) / total_days * 100
            if y2_width > 0:
                segments.append({
                    'class': 'ext-y2',
                    'width': y2_width,
                    'label': 'Y2',
                    'tooltip': f'Extended Support Year 2 ({ext_y2_start.strftime("%Y-%m-%d")} to {y2_end.strftime("%Y-%m-%d")})'
                })
        
        # Extended Support Year 3
        if ext_y3_start:
            y3_end = ext_end or safe_add_years(ext_y3_start, 1)
            y3_width = max(0, (y3_end - ext_y3_start).days) / total_days * 100
            if y3_width > 0:
                segments.append({
                    'class': 'ext-y3',
                    'width': y3_width,
                    'label': 'Y3',
                    'tooltip': f'Extended Support Year 3 ({ext_y3_start.strftime("%Y-%m-%d")} to {y3_end.strftime("%Y-%m-%d")})'
                })
        
        # Out of Support segment
        oos_start = ext_end or eos_date
        if oos_start and oos_start < timeline_end:
            oos_width = max(0, (timeline_end - oos_start).days) / total_days * 100
            if oos_width > 0:
                segments.append({
                    'class': 'out-of-support',
                    'width': oos_width,
                    'label': 'OOS',
                    'tooltip': f'Out of Support (from {oos_start.strftime("%Y-%m-%d")})'
                })
        
        # Calculate TODAY marker position
        today_position = max(0, min(100, (today - timeline_start).days / total_days * 100))
        
        # Build HTML
        segments_html = ''
        for seg in segments:
            segments_html += f'<div class="lifecycle-segment {seg["class"]}" style="width: {seg["width"]:.1f}%;" title="{seg["tooltip"]}">{seg["label"]}</div>'
        
        # Add TODAY marker
        marker_html = f'<div class="lifecycle-marker" style="left: {today_position:.1f}%;" title="Today ({today.strftime("%Y-%m-%d")})">▼</div>'
        
        return f'<div class="lifecycle-bar">{segments_html}{marker_html}</div>'

    def _get_aws_docs_link_html(self, service: str) -> str:
        """Generate HTML for AWS documentation link if available for the service.
        
        Args:
            service: Service name to look up documentation for.
            
        Returns:
            HTML string with documentation link, or empty string if not available.
        """
        docs_info = self.AWS_DOCS_LINKS.get(service)
        if docs_info:
            return f''' <a href="{docs_info["url"]}" target="_blank" class="aws-docs-link" onclick="event.stopPropagation();" title="{docs_info["description"]}">📖 {docs_info["title"]}</a>'''
        return ''

    def _generate_timeline_section(self, report: Report) -> str:
        """Generate the timeline visualization section with Chart.js timeline."""
        import json
        from collections import defaultdict
        
        # Collect timeline data grouped by month and status
        monthly_data = defaultdict(lambda: {'supported': 0, 'approaching': 0, 'extended_year_1': 0, 'extended_year_2': 0, 'extended_year_3': 0, 'out_of_support': 0})
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
        chart_extended_year_1 = json.dumps([monthly_data[m]['extended_year_1'] for m in sorted_months])
        chart_extended_year_2 = json.dumps([monthly_data[m]['extended_year_2'] for m in sorted_months])
        chart_extended_year_3 = json.dumps([monthly_data[m]['extended_year_3'] for m in sorted_months])
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
        
        # Prepare timeline items JSON for JavaScript filtering
        timeline_items_json = json.dumps(timeline_items)
        
        # Generate timeline list HTML with data attributes for filtering
        timeline_list_html = []
        for item in timeline_items[:100]:  # Limit to 100 items
            status_class = f"status-{item['status'].replace('_', '-')}"
            status_label = {'supported': 'Supported', 'approaching': 'Approaching EOS', 'extended_year_1': 'Extended Support Y1', 'extended_year_2': 'Extended Support Y2', 'extended_year_3': 'Extended Support Y3', 'out_of_support': 'Out of Support'}.get(item['status'], item['status'])
            timeline_list_html.append(f"""
                <div class="timeline-item" data-service="{self._escape_html(item['service'])}" data-status="{status_label}" style="display: flex; align-items: center; padding: 8px 12px; margin: 4px 0; border-radius: 4px; background-color: #f9f9f9;">
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
        # Default: 6 months before current date to 6 months after
        from datetime import datetime
        
        today = datetime.now()
        
        # Calculate 6 months before
        year_start = today.year
        month_start = today.month - 6
        while month_start < 1:
            month_start += 12
            year_start -= 1
        default_start = f"{year_start:04d}-{month_start:02d}"
        
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
            # Clamp defaults to available data range
            if default_start < data_min_month:
                default_start = data_min_month
            if default_end > data_max_month:
                default_end = data_max_month
        else:
            # No data - use calculated defaults anyway
            data_min_month = default_start
            data_max_month = default_end
        
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
            // Make timeline variables global for access from other scripts
            window.timelineResourcesData = {monthly_resources_json};
            window.timelineServiceSummary = {monthly_service_summary_json};
            window.timelineMonths = {chart_labels};
            window.allTimelineMonths = {chart_labels};
            window.allTimelineResourcesData = {monthly_resources_json};
            window.allTimelineData = {{
                out_of_support: {chart_out_of_support},
                extended_year_3: {chart_extended_year_3},
                extended_year_2: {chart_extended_year_2},
                extended_year_1: {chart_extended_year_1},
                approaching: {chart_approaching},
                supported: {chart_supported}
            }};
            window.timelineChartInstance = null;
            
            function initTimelineChart() {{
                var timelineCtx = document.getElementById('timelineChart');
                if (timelineCtx && !window.timelineChartInstance) {{
                    window.timelineChartInstance = new Chart(timelineCtx, {{
                        type: 'bar',
                        data: {{
                            labels: {chart_labels},
                            datasets: [
                                {{ label: 'Out of Support', data: {chart_out_of_support}, backgroundColor: '#ef5350', borderColor: '#c62828', borderWidth: 1 }},
                                {{ label: 'Extended Support Y3', data: {chart_extended_year_3}, backgroundColor: '#64b5f6', borderColor: '#0d47a1', borderWidth: 1 }},
                                {{ label: 'Extended Support Y2', data: {chart_extended_year_2}, backgroundColor: '#90caf9', borderColor: '#1565c0', borderWidth: 1 }},
                                {{ label: 'Extended Support Y1', data: {chart_extended_year_1}, backgroundColor: '#bbdefb', borderColor: '#1976d2', borderWidth: 1 }},
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
                
                // If dates are empty, use first and last available months as defaults
                if (!startDate && window.allTimelineMonths.length > 0) {{
                    startDate = window.allTimelineMonths[0];
                    document.getElementById('timelineStartDate').value = startDate;
                }}
                if (!endDate && window.allTimelineMonths.length > 0) {{
                    endDate = window.allTimelineMonths[window.allTimelineMonths.length - 1];
                    document.getElementById('timelineEndDate').value = endDate;
                }}
                
                if (!startDate || !endDate) {{
                    // No data available at all
                    return;
                }}
                
                var filteredIndices = [];
                for (var i = 0; i < window.allTimelineMonths.length; i++) {{
                    var month = window.allTimelineMonths[i];
                    if (month >= startDate && month <= endDate) {{
                        filteredIndices.push(i);
                    }}
                }}
                
                var filteredMonths = filteredIndices.map(function(i) {{ return window.allTimelineMonths[i]; }});
                var filteredOutOfSupport = filteredIndices.map(function(i) {{ return window.allTimelineData.out_of_support[i]; }});
                var filteredExtended = filteredIndices.map(function(i) {{ return window.allTimelineData.extended[i]; }});
                var filteredApproaching = filteredIndices.map(function(i) {{ return window.allTimelineData.approaching[i]; }});
                var filteredSupported = filteredIndices.map(function(i) {{ return window.allTimelineData.supported[i]; }});
                
                window.timelineChartInstance.data.labels = filteredMonths;
                window.timelineChartInstance.data.datasets[0].data = filteredOutOfSupport;
                window.timelineChartInstance.data.datasets[1].data = filteredExtended;
                window.timelineChartInstance.data.datasets[2].data = filteredApproaching;
                window.timelineChartInstance.data.datasets[3].data = filteredSupported;
                window.timelineChartInstance.update();
            }}
            
            function resetTimelineDateFilter() {{
                document.getElementById('timelineStartDate').value = window.allTimelineMonths[0] || '';
                document.getElementById('timelineEndDate').value = window.allTimelineMonths[window.allTimelineMonths.length - 1] || '';
                
                window.timelineChartInstance.data.labels = window.allTimelineMonths;
                window.timelineChartInstance.data.datasets[0].data = window.allTimelineData.out_of_support;
                window.timelineChartInstance.data.datasets[1].data = window.allTimelineData.extended;
                window.timelineChartInstance.data.datasets[2].data = window.allTimelineData.approaching;
                window.timelineChartInstance.data.datasets[3].data = window.allTimelineData.supported;
                window.timelineChartInstance.update();
            }}
            
            function showMonthResources(month) {{
                var resources = window.timelineResourcesData[month] || [];
                if (resources.length === 0) {{
                    alert('No resources found for ' + month);
                    return;
                }}
                // Apply current page filters
                resources = filterResourcesByCurrentFilters(resources);
                if (resources.length === 0) {{
                    alert('No resources match current filters for ' + month);
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
                            'extended_year_1': 0,
                            'extended_year_2': 0,
                            'extended_year_3': 0,
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
                            <span class="status-badge status-extended-year-1" data-count="{status_counts['extended_year_1']}">{status_counts['extended_year_1']}</span>
                            <span class="status-badge status-extended-year-2" data-count="{status_counts['extended_year_2']}">{status_counts['extended_year_2']}</span>
                            <span class="status-badge status-extended-year-3" data-count="{status_counts['extended_year_3']}">{status_counts['extended_year_3']}</span>
                            <span class="status-badge status-out-of-support" data-count="{status_counts['out_of_support']}">{status_counts['out_of_support']}</span>
                        </span>
                    </div>
                    <div class="service-group-content">
                        <div class="table-wrapper">
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

    def _generate_version_details_section(self, report: Report) -> str:
        """Generate the Version Details section with accordion-style cards for each Service+Engine."""
        import json
        from collections import defaultdict
        
        # Aggregate data by (service, engine) -> versions -> resources
        aggregated_data: Dict[tuple, Dict[str, list]] = {}
        
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                for engine_name, engine_group in service_group.engines.items():
                    key = (service_name, engine_name or "")
                    if key not in aggregated_data:
                        aggregated_data[key] = {}
                    
                    for version_name, version_group in engine_group.versions.items():
                        if version_name not in aggregated_data[key]:
                            aggregated_data[key][version_name] = []
                        aggregated_data[key][version_name].extend(version_group.resources)
        
        # Generate cards for each Service+Engine combination
        cards_html = []
        
        for (service, engine), versions_data in sorted(aggregated_data.items()):
            anchor_id = self._get_version_details_anchor_id(service, engine)
            display_name = f"{service} - {engine}" if engine and engine != "Unknown" and engine != "" else service
            
            # Calculate totals for this service+engine
            total_resources = 0
            status_counts = {
                'supported': 0, 
                'approaching': 0, 
                'extended_year_1': 0, 
                'extended_year_2': 0, 
                'extended_year_3': 0, 
                'out_of_support': 0
            }
            
            for version_name, resources in versions_data.items():
                total_resources += len(resources)
                for r in resources:
                    status_key = self._status_to_key(r.status)
                    status_counts[status_key] += 1
            
            # Generate version rows
            version_rows = []
            for version_name in sorted(versions_data.keys()):
                resources = versions_data[version_name]
                resource_count = len(resources)
                
                # Get dates
                eos_dates = [r.end_of_support for r in resources if r.end_of_support]
                ext_start_dates = [r.extended_support_start for r in resources if r.extended_support_start]
                ext_end_dates = [r.extended_support_end for r in resources if r.extended_support_end]
                
                # Get extended support year dates for timeline
                ext_y1_dates = [r.extended_support_year1_start for r in resources if r.extended_support_year1_start]
                ext_y3_dates = [r.extended_support_year3_start for r in resources if r.extended_support_year3_start]
                
                eos_date = min(eos_dates).strftime('%Y-%m-%d') if eos_dates else 'N/A'
                ext_start = min(ext_start_dates).strftime('%Y-%m-%d') if ext_start_dates else 'N/A'
                ext_end = max(ext_end_dates).strftime('%Y-%m-%d') if ext_end_dates else 'N/A'
                
                # Generate support lifecycle timeline bar
                timeline_html = self._generate_lifecycle_timeline_bar(
                    eos_date=min(eos_dates) if eos_dates else None,
                    ext_start=min(ext_start_dates) if ext_start_dates else None,
                    ext_y1_start=min(ext_y1_dates) if ext_y1_dates else None,
                    ext_y3_start=min(ext_y3_dates) if ext_y3_dates else None,
                    ext_end=max(ext_end_dates) if ext_end_dates else None
                )
                
                # Status summary
                version_status_counts = {}
                for r in resources:
                    status_label = self.STATUS_LABELS.get(r.status, "Unknown")
                    version_status_counts[status_label] = version_status_counts.get(status_label, 0) + 1
                status_summary = ", ".join([f"{k}: {v}" for k, v in sorted(version_status_counts.items())])
                
                version_rows.append(f"""
                    <tr>
                        <td>{self._escape_html(version_name)}</td>
                        <td>{resource_count}</td>
                        <td>{eos_date}</td>
                        <td>{ext_start}</td>
                        <td>{ext_end}</td>
                        <td>{status_summary}</td>
                        <td style="min-width: 280px;">{timeline_html}</td>
                    </tr>
                """)
            
            version_rows_html = '\n'.join(version_rows)
            
            # Generate status badges for header
            status_badges = []
            if status_counts['supported'] > 0:
                status_badges.append(f'<span class="stat-badge status-supported">{status_counts["supported"]} Supported</span>')
            if status_counts['approaching'] > 0:
                status_badges.append(f'<span class="stat-badge status-approaching">{status_counts["approaching"]} Approaching</span>')
            if status_counts['extended_year_1'] > 0:
                status_badges.append(f'<span class="stat-badge status-extended-year-1">{status_counts["extended_year_1"]} Ext Yr 1</span>')
            if status_counts['extended_year_2'] > 0:
                status_badges.append(f'<span class="stat-badge status-extended-year-2">{status_counts["extended_year_2"]} Ext Yr 2</span>')
            if status_counts['extended_year_3'] > 0:
                status_badges.append(f'<span class="stat-badge status-extended-year-3">{status_counts["extended_year_3"]} Ext Yr 3</span>')
            if status_counts['out_of_support'] > 0:
                status_badges.append(f'<span class="stat-badge status-out-of-support">{status_counts["out_of_support"]} Out of Support</span>')
            
            status_badges_html = ' '.join(status_badges)
            
            # Generate AWS documentation link if available
            docs_link_html = self._get_aws_docs_link_html(service)
            
            card_html = f"""
            <div class="version-detail-card" id="version-detail-{anchor_id}" data-service="{self._escape_html(service)}" data-engine="{self._escape_html(engine)}">
                <div class="version-detail-header" onclick="toggleVersionDetailCard('{anchor_id}')">
                    <h3>{self._escape_html(display_name)}{docs_link_html}</h3>
                    <div class="stats">
                        <span style="color: #666; margin-right: 10px;">{total_resources} resources, {len(versions_data)} versions</span>
                        {status_badges_html}
                        <span class="expand-icon">▼</span>
                    </div>
                </div>
                <div class="version-detail-content">
                    <div class="version-detail-summary">
                        <div class="summary-item">
                            <div class="count">{total_resources}</div>
                            <div class="label">Total Resources</div>
                        </div>
                        <div class="summary-item">
                            <div class="count">{len(versions_data)}</div>
                            <div class="label">Versions</div>
                        </div>
                        <div class="summary-item" style="background: #c8e6c9;">
                            <div class="count" style="color: #1b5e20;">{status_counts['supported']}</div>
                            <div class="label">Supported</div>
                        </div>
                        <div class="summary-item" style="background: #fff9c4;">
                            <div class="count" style="color: #f57f17;">{status_counts['approaching']}</div>
                            <div class="label">Approaching EOS</div>
                        </div>
                        <div class="summary-item" style="background: #bbdefb;">
                            <div class="count" style="color: #0d47a1;">{status_counts['extended_year_1']}</div>
                            <div class="label">Extended Support Y1</div>
                        </div>
                        <div class="summary-item" style="background: #90caf9;">
                            <div class="count" style="color: #1565c0;">{status_counts['extended_year_2']}</div>
                            <div class="label">Extended Support Y2</div>
                        </div>
                        <div class="summary-item" style="background: #64b5f6;">
                            <div class="count" style="color: #0d47a1;">{status_counts['extended_year_3']}</div>
                            <div class="label">Extended Support Y3</div>
                        </div>
                        <div class="summary-item" style="background: #ffcdd2;">
                            <div class="count" style="color: #b71c1c;">{status_counts['out_of_support']}</div>
                            <div class="label">Out of Support</div>
                        </div>
                    </div>
                    <div class="table-wrapper">
                        <table class="version-detail-table">
                            <thead>
                                <tr>
                                    <th>Version</th>
                                    <th>Resource Count</th>
                                    <th>End of Support</th>
                                    <th>Extended Support Start</th>
                                    <th>Extended Support End</th>
                                    <th>Status Summary</th>
                                    <th>Support Lifecycle</th>
                                </tr>
                            </thead>
                            <tbody>
                                {version_rows_html}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            """
            cards_html.append(card_html)
        
        cards_html_str = '\n'.join(cards_html)
        
        return f"""<div id="version-details-section" class="section">
    <h2>Version Details by Service
        <button class="collapse-btn" onclick="toggleSection('version-details-content')">−</button>
    </h2>
    <div id="version-details-content" class="collapsible-content">
        <p>Detailed version information for each Service+Engine combination. Click on a card to expand.</p>
        <div class="version-details-controls">
            <button onclick="expandAllVersionDetails()">Expand All</button>
            <button onclick="collapseAllVersionDetails()">Collapse All</button>
        </div>
        {cards_html_str if cards_html else '<p>No version details available.</p>'}
    </div>
</div>"""

    def _generate_footer(self) -> str:
        """Generate the page footer."""
        return f"""<div class="footer">
    <p>* Cost values marked with asterisk indicate future charges if resource is not upgraded before EOS</p>
    <p>Generated by AWS End-of-Support Tool v{__version__} | 
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
            'extended_year_1': 0,
            'extended_year_2': 0,
            'extended_year_3': 0,
            'out_of_support': 0
        }
        
        # Also collect detailed resources for click-through
        from collections import defaultdict
        service_resources = defaultdict(list)
        account_resources = defaultdict(list)
        status_resources = defaultdict(list)
        
        for account_name, account_group in report.accounts.items():
            if account_name not in account_data:
                account_data[account_name] = {'supported': 0, 'approaching': 0, 'extended_year_1': 0, 'extended_year_2': 0, 'extended_year_3': 0, 'out_of_support': 0}
            for service_name, service_group in account_group.services.items():
                if service_name not in service_data:
                    service_data[service_name] = {'supported': 0, 'approaching': 0, 'extended_year_1': 0, 'extended_year_2': 0, 'extended_year_3': 0, 'out_of_support': 0}
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
        service_extended_year_1 = json.dumps([v['extended_year_1'] for v in service_data.values()])
        service_extended_year_2 = json.dumps([v['extended_year_2'] for v in service_data.values()])
        service_extended_year_3 = json.dumps([v['extended_year_3'] for v in service_data.values()])
        service_out = json.dumps([v['out_of_support'] for v in service_data.values()])
        
        account_labels = json.dumps(list(account_data.keys()))
        account_supported = json.dumps([v['supported'] for v in account_data.values()])
        account_approaching = json.dumps([v['approaching'] for v in account_data.values()])
        account_extended_year_1 = json.dumps([v['extended_year_1'] for v in account_data.values()])
        account_extended_year_2 = json.dumps([v['extended_year_2'] for v in account_data.values()])
        account_extended_year_3 = json.dumps([v['extended_year_3'] for v in account_data.values()])
        account_out = json.dumps([v['out_of_support'] for v in account_data.values()])
        
        status_values = json.dumps([
            status_totals['supported'],
            status_totals['approaching'],
            status_totals['extended_year_1'],
            status_totals['extended_year_2'],
            status_totals['extended_year_3'],
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
            'extended_year_1': {},
            'extended_year_2': {},
            'extended_year_3': {},
            'out_of_support': {}
        }
        for svc_name, svc_counts in service_data.items():
            total_for_service = sum(svc_counts.values())
            if total_for_service > 0:
                status_service_summary['total'][svc_name] = total_for_service
            for status_key in ['supported', 'approaching', 'extended_year_1', 'extended_year_2', 'extended_year_3', 'out_of_support']:
                if svc_counts[status_key] > 0:
                    status_service_summary[status_key][svc_name] = svc_counts[status_key]
        
        status_service_summary_json = json.dumps(status_service_summary)
        
        return f"""<script>
// Chart click-through data
var serviceResourcesData = {service_resources_json};
var accountResourcesData = {account_resources_json};
var statusResourcesData = {status_resources_json};
var statusServiceSummary = {status_service_summary_json};
var statusLabelsMap = ['supported', 'approaching', 'extended_year_1', 'extended_year_2', 'extended_year_3', 'out_of_support'];
var statusDisplayNames = {{
    'supported': 'Supported',
    'approaching': 'Approaching EOS',
    'extended_year_1': 'Extended Support Y1',
    'extended_year_2': 'Extended Support Y2',
    'extended_year_3': 'Extended Support Y3',
    'out_of_support': 'Out of Support'
}};

// Helper function to filter resources based on current page filters
function filterResourcesByCurrentFilters(resources) {{
    var filters = getSelectedFilters();
    
    return resources.filter(function(r) {{
        // Check service filter
        if (filters.services.length > 0 && !filters.services.includes(r.service)) return false;
        
        // Check account filter
        if (filters.accounts.length > 0 && !filters.accounts.includes(r.account)) return false;
        
        // Check status filter (filters.statuses contains display names like "Supported")
        if (filters.statuses.length > 0) {{
            var statusLabel = statusDisplayNames[r.status];
            if (!filters.statuses.includes(statusLabel)) return false;
        }}
        
        return true;
    }});
}}

// Show resources for a specific status (from summary card click)
function showStatusResources(statusKey) {{
    var resources = statusResourcesData[statusKey] || [];
    // Apply current page filters
    resources = filterResourcesByCurrentFilters(resources);
    var title = statusDisplayNames[statusKey] + ' Resources';
    showChartResources(title, resources, {{ statuses: [statusKey] }});
}}

// Show all resources (from Total card click)
function showAllResources() {{
    var allResources = [];
    for (var status in statusResourcesData) {{
        allResources = allResources.concat(statusResourcesData[status]);
    }}
    // Apply current page filters
    allResources = filterResourcesByCurrentFilters(allResources);
    showChartResources('All Resources', allResources, {{}});
}}

// Summary card tooltip functions
var summaryTooltip = null;

function showSummaryTooltip(event, statusKey) {{
    // Get current filters
    var filters = getSelectedFilters();
    
    // Calculate filtered service counts based on current filters
    var filteredServiceCounts = {{}};
    
    // Iterate through all resources and count by service (respecting filters)
    for (var service in serviceResourcesData) {{
        // Check service filter
        if (filters.services.length > 0 && !filters.services.includes(service)) continue;
        
        var resources = serviceResourcesData[service];
        resources.forEach(function(r) {{
            // Check account filter
            if (filters.accounts.length > 0 && !filters.accounts.includes(r.account)) return;
            
            // Check status filter
            var statusLabel = statusDisplayNames[r.status];
            if (filters.statuses.length > 0 && !filters.statuses.includes(statusLabel)) return;
            
            // For 'total', count all; otherwise count only matching status
            if (statusKey === 'total' || r.status === statusKey) {{
                if (!filteredServiceCounts[service]) {{
                    filteredServiceCounts[service] = 0;
                }}
                filteredServiceCounts[service]++;
            }}
        }});
    }}
    
    var serviceList = Object.keys(filteredServiceCounts);
    
    if (serviceList.length === 0) return;
    
    // Sort by count descending
    serviceList.sort(function(a, b) {{ return filteredServiceCounts[b] - filteredServiceCounts[a]; }});
    
    // Create tooltip element if not exists
    if (!summaryTooltip) {{
        summaryTooltip = document.createElement('div');
        summaryTooltip.className = 'summary-card-tooltip';
        document.body.appendChild(summaryTooltip);
    }}
    
    // Build tooltip content
    var title = statusKey === 'total' ? 'All Resources' : statusDisplayNames[statusKey];
    var html = '<div class="tooltip-title">Resources by Service (filtered)</div>';
    
    var maxShow = 5;
    var shown = Math.min(serviceList.length, maxShow);
    
    for (var i = 0; i < shown; i++) {{
        var svc = serviceList[i];
        html += '<div class="tooltip-row">';
        html += '<span class="tooltip-service">' + svc + '</span>';
        html += '<span class="tooltip-count">' + filteredServiceCounts[svc] + '</span>';
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
    html += '.status-extended-year-1 {{ background: #bbdefb; color: #0d47a1; }}';
    html += '.status-extended-year-2 {{ background: #90caf9; color: #1565c0; }}';
    html += '.status-extended-year-3 {{ background: #64b5f6; color: #0d47a1; }}';
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
    html += '<p>Resources are classified into six status categories:</p>';
    html += '<div class="feature">';
    html += '<p><span class="status-example status-supported">Supported</span> - Resource version is fully supported with no immediate action required.</p>';
    html += '<p><span class="status-example status-approaching">Approaching EOS</span> - End-of-support date is within the configured threshold (default: 90 days). Plan your upgrade soon.</p>';
    html += '<p><span class="status-example status-extended-year-1">Extended Support Y1</span> - Resource is in Year 1 of extended support period.</p>';
    html += '<p><span class="status-example status-extended-year-2">Extended Support Y2</span> - Resource is in Year 2 of extended support period.</p>';
    html += '<p><span class="status-example status-extended-year-3">Extended Support Y3</span> - Resource is in Year 3 of extended support period.</p>';
    html += '<p><span class="status-example status-out">Out of Support</span> - Resource has passed its end-of-support date. Immediate action recommended.</p>';
    html += '</div>';
    html += '<h3>Cost Estimates</h3>';
    html += '<p>The report includes estimated extended support costs for applicable resources:</p>';
    html += '<div class="tip"><strong>Note:</strong> Costs marked with an asterisk (*) indicate <em>future charges</em> that will apply if the component is not upgraded before the End-of-Support date. These costs are in addition to regular service pricing.</div>';
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
    html += '<li><strong>Ext. Support Start</strong> - Extended support start date</li>';
    html += '<li><strong>Ext. Support End</strong> - Extended support end date</li>';
    html += '<li><strong>Est. Monthly Cost</strong> - Estimated monthly extended support cost</li>';
    html += '<li><strong>Est. Annual Cost</strong> - Estimated annual extended support cost</li>';
    html += '</ul>';
    html += '<div class="tip"><strong>Note:</strong> Cost values marked with * (asterisk) indicate future charges that will apply if the resource is not upgraded before EOS.</div>';
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
    var allStatuses = ['supported', 'approaching', 'extended_year_1', 'extended_year_2', 'extended_year_3', 'out_of_support'];
    
    var statusColors = {{
        'supported': {{ bg: '#c8e6c9', text: '#1b5e20' }},
        'approaching': {{ bg: '#fff9c4', text: '#f57f17' }},
        'extended_year_1': {{ bg: '#bbdefb', text: '#0d47a1' }},
        'extended_year_2': {{ bg: '#90caf9', text: '#1565c0' }},
        'extended_year_3': {{ bg: '#64b5f6', text: '#0d47a1' }},
        'out_of_support': {{ bg: '#ffcdd2', text: '#b71c1c' }}
    }};
    
    var statusLabels = {{
        'supported': 'Supported',
        'approaching': 'Approaching EOS',
        'extended_year_1': 'Extended Support Y1',
        'extended_year_2': 'Extended Support Y2',
        'extended_year_3': 'Extended Support Y3',
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
    html += '.filter-chip.status-extended_year_1.selected {{ background: #1976d2; border-color: #1976d2; }}' + nl;
    html += '.filter-chip.status-extended_year_2.selected {{ background: #1565c0; border-color: #1565c0; }}' + nl;
    html += '.filter-chip.status-extended_year_3.selected {{ background: #0d47a1; border-color: #0d47a1; }}' + nl;
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
                scrollX: true,
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

// Global flag to prevent sorting during column resize
window.isColumnResizing = false;

// Column resizing functionality
function initColumnResizers(tableSelector) {{
    // When scrollX is enabled, DataTables clones headers into .dataTables_scrollHead
    // We need to add resizers to the visible headers in the scroll head
    const wrapper = $(tableSelector).closest('.dataTables_wrapper');
    const dt = $(tableSelector).DataTable();
    let headerContainer;
    
    if (wrapper.length && wrapper.find('.dataTables_scrollHead').length) {{
        // scrollX is enabled - use the scroll head
        headerContainer = wrapper.find('.dataTables_scrollHead table thead')[0];
    }} else {{
        // No scrollX - use the original table
        headerContainer = document.querySelector(tableSelector + ' thead');
    }}
    
    if (!headerContainer) return;
    
    const headers = headerContainer.querySelectorAll('th');
    
    // Add capturing click handler to block sorting during resize
    headerContainer.addEventListener('click', function(e) {{
        if (window.isColumnResizing) {{
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            return false;
        }}
    }}, true);  // true = capturing phase, runs before DataTables handler
    
    headers.forEach(function(th, index) {{
        // Skip last column (no resizer needed)
        if (index === headers.length - 1) return;
        
        // Remove existing resizer if any
        const existingResizer = th.querySelector('.col-resizer');
        if (existingResizer) existingResizer.remove();
        
        // Create resizer element
        const resizer = document.createElement('div');
        resizer.className = 'col-resizer';
        th.appendChild(resizer);
        
        let startX, startWidth;
        
        resizer.addEventListener('mousedown', function(e) {{
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            
            window.isColumnResizing = true;
            startX = e.pageX;
            startWidth = th.offsetWidth;
            
            resizer.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            return false;
        }});
        
        function onMouseMove(e) {{
            e.preventDefault();
            const diff = e.pageX - startX;
            const newWidth = Math.max(50, startWidth + diff);
            
            // Update both the scroll header and the body table columns
            th.style.width = newWidth + 'px';
            th.style.minWidth = newWidth + 'px';
            
            // Also update the corresponding column in the body table
            const bodyTable = wrapper.find('.dataTables_scrollBody table');
            if (bodyTable.length) {{
                const bodyTh = bodyTable.find('thead th').eq(index);
                if (bodyTh.length) {{
                    bodyTh.css({{ width: newWidth + 'px', minWidth: newWidth + 'px' }});
                }}
            }}
        }}
        
        function onMouseUp(e) {{
            e.preventDefault();
            e.stopPropagation();
            
            resizer.classList.remove('resizing');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            
            // Delay resetting the flag to prevent the click from triggering sort
            setTimeout(function() {{
                window.isColumnResizing = false;
            }}, 200);
        }}
    }});
}}

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
        const statusCell = data[8];
        
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
    
    // Filter version detail cards
    filterVersionDetailCards(filters);
    
    // Update summary counts based on visible rows
    updateSummaryCounts(table);
    
    // Update charts based on filters
    updateChartsWithFilters(filters);
}}

// Filter version detail cards based on selected filters
function filterVersionDetailCards(filters) {{
    document.querySelectorAll('.version-detail-card').forEach(function(card) {{
        const service = card.dataset.service;
        
        // Check if service matches filter
        if (filters.services.length > 0 && !filters.services.includes(service)) {{
            card.style.display = 'none';
        }} else {{
            card.style.display = '';
        }}
    }});
}}

// Update charts based on filters
function updateChartsWithFilters(filters) {{
    // Recalculate chart data based on filtered resources
    var filteredServiceData = {{}};
    var filteredAccountData = {{}};
    var filteredStatusTotals = {{ supported: 0, approaching: 0, extended_year_1: 0, extended_year_2: 0, extended_year_3: 0, out_of_support: 0 }};
    
    // Get all resources and filter them
    for (var service in serviceResourcesData) {{
        if (filters.services.length > 0 && !filters.services.includes(service)) continue;
        
        var resources = serviceResourcesData[service];
        resources.forEach(function(r) {{
            // Check account filter
            if (filters.accounts.length > 0 && !filters.accounts.includes(r.account)) return;
            
            // Check status filter
            var statusLabel = statusDisplayNames[r.status];
            if (filters.statuses.length > 0 && !filters.statuses.includes(statusLabel)) return;
            
            // Count for service chart
            if (!filteredServiceData[service]) {{
                filteredServiceData[service] = {{ supported: 0, approaching: 0, extended_year_1: 0, extended_year_2: 0, extended_year_3: 0, out_of_support: 0 }};
            }}
            filteredServiceData[service][r.status]++;
            
            // Count for account chart
            if (!filteredAccountData[r.account]) {{
                filteredAccountData[r.account] = {{ supported: 0, approaching: 0, extended_year_1: 0, extended_year_2: 0, extended_year_3: 0, out_of_support: 0 }};
            }}
            filteredAccountData[r.account][r.status]++;
            
            // Count for status totals
            filteredStatusTotals[r.status]++;
        }});
    }}
    
    // Update service chart
    var serviceChart = Chart.getChart('serviceChart');
    if (serviceChart) {{
        var filteredServiceLabels = Object.keys(filteredServiceData).sort();
        serviceChart.data.labels = filteredServiceLabels;
        serviceChart.data.datasets[0].data = filteredServiceLabels.map(function(s) {{ return filteredServiceData[s].supported; }});
        serviceChart.data.datasets[1].data = filteredServiceLabels.map(function(s) {{ return filteredServiceData[s].approaching; }});
        serviceChart.data.datasets[2].data = filteredServiceLabels.map(function(s) {{ return filteredServiceData[s].extended_year_1; }});
        serviceChart.data.datasets[3].data = filteredServiceLabels.map(function(s) {{ return filteredServiceData[s].extended_year_2; }});
        serviceChart.data.datasets[4].data = filteredServiceLabels.map(function(s) {{ return filteredServiceData[s].extended_year_3; }});
        serviceChart.data.datasets[5].data = filteredServiceLabels.map(function(s) {{ return filteredServiceData[s].out_of_support; }});
        serviceChart.update();
    }}
    
    // Update account chart
    var accountChart = Chart.getChart('accountChart');
    if (accountChart) {{
        var filteredAccountLabels = Object.keys(filteredAccountData).sort();
        accountChart.data.labels = filteredAccountLabels;
        accountChart.data.datasets[0].data = filteredAccountLabels.map(function(a) {{ return filteredAccountData[a].supported; }});
        accountChart.data.datasets[1].data = filteredAccountLabels.map(function(a) {{ return filteredAccountData[a].approaching; }});
        accountChart.data.datasets[2].data = filteredAccountLabels.map(function(a) {{ return filteredAccountData[a].extended_year_1; }});
        accountChart.data.datasets[3].data = filteredAccountLabels.map(function(a) {{ return filteredAccountData[a].extended_year_2; }});
        accountChart.data.datasets[4].data = filteredAccountLabels.map(function(a) {{ return filteredAccountData[a].extended_year_3; }});
        accountChart.data.datasets[5].data = filteredAccountLabels.map(function(a) {{ return filteredAccountData[a].out_of_support; }});
        accountChart.update();
    }}
    
    // Update status pie chart
    var statusPieChart = Chart.getChart('statusPieChart');
    if (statusPieChart) {{
        statusPieChart.data.datasets[0].data = [
            filteredStatusTotals.supported,
            filteredStatusTotals.approaching,
            filteredStatusTotals.extended_year_1,
            filteredStatusTotals.extended_year_2,
            filteredStatusTotals.extended_year_3,
            filteredStatusTotals.out_of_support
        ];
        statusPieChart.update();
    }}
    
    // Update service pie chart
    var servicePieChart = Chart.getChart('servicePieChart');
    if (servicePieChart) {{
        var filteredServiceLabels = Object.keys(filteredServiceData).sort();
        servicePieChart.data.labels = filteredServiceLabels;
        servicePieChart.data.datasets[0].data = filteredServiceLabels.map(function(s) {{
            var d = filteredServiceData[s];
            return d.supported + d.approaching + d.extended_year_1 + d.extended_year_2 + d.extended_year_3 + d.out_of_support;
        }});
        servicePieChart.update();
    }}
    
    // Update timeline chart and list
    updateTimelineWithFilters(filters);
}}

// Update timeline chart and list based on filters
function updateTimelineWithFilters(filters) {{
    // Check if timeline data is available
    if (typeof window.allTimelineResourcesData === 'undefined' || !window.allTimelineResourcesData) {{
        return;
    }}
    
    // Filter timeline resources data
    var filteredMonthlyData = {{}};
    
    for (var month in window.allTimelineResourcesData) {{
        if (!window.allTimelineResourcesData.hasOwnProperty(month)) continue;
        var resources = window.allTimelineResourcesData[month];
        if (!resources || !Array.isArray(resources)) continue;
        
        var filteredResources = resources.filter(function(r) {{
            // Check service filter
            if (filters.services.length > 0 && filters.services.indexOf(r.service) === -1) return false;
            
            // Check account filter
            if (filters.accounts.length > 0 && filters.accounts.indexOf(r.account) === -1) return false;
            
            // Check status filter
            var statusLabel = statusDisplayNames[r.status];
            if (filters.statuses.length > 0 && filters.statuses.indexOf(statusLabel) === -1) return false;
            
            return true;
        }});
        
        if (filteredResources.length > 0) {{
            filteredMonthlyData[month] = {{
                supported: 0,
                approaching: 0,
                extended_year_1: 0,
                extended_year_2: 0,
                extended_year_3: 0,
                out_of_support: 0
            }};
            filteredResources.forEach(function(r) {{
                filteredMonthlyData[month][r.status]++;
            }});
        }}
    }}
    
    // Update timeline chart
    if (typeof window.timelineChartInstance !== 'undefined' && window.timelineChartInstance) {{
        var filteredMonths = Object.keys(filteredMonthlyData).sort();
        
        // Apply date range filter if set
        var startDate = document.getElementById('timelineStartDate').value;
        var endDate = document.getElementById('timelineEndDate').value;
        if (startDate && endDate) {{
            filteredMonths = filteredMonths.filter(function(m) {{
                return m >= startDate && m <= endDate;
            }});
        }}
        
        window.timelineChartInstance.data.labels = filteredMonths;
        window.timelineChartInstance.data.datasets[0].data = filteredMonths.map(function(m) {{ return filteredMonthlyData[m] ? filteredMonthlyData[m].out_of_support : 0; }});
        window.timelineChartInstance.data.datasets[1].data = filteredMonths.map(function(m) {{ return filteredMonthlyData[m] ? filteredMonthlyData[m].extended_year_3 : 0; }});
        window.timelineChartInstance.data.datasets[2].data = filteredMonths.map(function(m) {{ return filteredMonthlyData[m] ? filteredMonthlyData[m].extended_year_2 : 0; }});
        window.timelineChartInstance.data.datasets[3].data = filteredMonths.map(function(m) {{ return filteredMonthlyData[m] ? filteredMonthlyData[m].extended_year_1 : 0; }});
        window.timelineChartInstance.data.datasets[4].data = filteredMonths.map(function(m) {{ return filteredMonthlyData[m] ? filteredMonthlyData[m].approaching : 0; }});
        window.timelineChartInstance.data.datasets[5].data = filteredMonths.map(function(m) {{ return filteredMonthlyData[m] ? filteredMonthlyData[m].supported : 0; }});
        window.timelineChartInstance.update();
    }}
    
    // Update timeline list (Upcoming End-of-Support Events)
    var timelineItems = document.querySelectorAll('.timeline-item');
    timelineItems.forEach(function(item) {{
        var service = item.getAttribute('data-service') || '';
        var status = item.getAttribute('data-status') || '';
        
        // Service filter: if no services selected, show all; otherwise check if service is in selected list
        var serviceMatch = filters.services.length === 0 || filters.services.indexOf(service) !== -1;
        // Status filter: if no statuses selected, show all; otherwise check if status is in selected list
        var statusMatch = filters.statuses.length === 0 || filters.statuses.indexOf(status) !== -1;
        
        if (serviceMatch && statusMatch) {{
            item.style.display = '';
        }} else {{
            item.style.display = 'none';
        }}
    }});
}}

function updateSummaryCounts(table) {{
    let total = 0;
    let supported = 0;
    let approaching = 0;
    let extendedYear1 = 0;
    let extendedYear2 = 0;
    let extendedYear3 = 0;
    let outOfSupport = 0;
    
    table.rows({{ search: 'applied' }}).every(function() {{
        total++;
        const data = this.data();
        const statusCell = data[8];
        
        if (statusCell.includes('status-supported')) supported++;
        else if (statusCell.includes('status-approaching')) approaching++;
        else if (statusCell.includes('status-extended-year-1')) extendedYear1++;
        else if (statusCell.includes('status-extended-year-2')) extendedYear2++;
        else if (statusCell.includes('status-extended-year-3')) extendedYear3++;
        else if (statusCell.includes('status-out-of-support')) outOfSupport++;
    }});
    
    // Update the summary cards
    const cards = document.querySelectorAll('.summary-card .count');
    if (cards.length >= 7) {{
        cards[0].textContent = total;
        cards[1].textContent = supported;
        cards[2].textContent = approaching;
        cards[3].textContent = extendedYear1;
        cards[4].textContent = extendedYear2;
        cards[5].textContent = extendedYear3;
        cards[6].textContent = outOfSupport;
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
    if (cards.length >= 7) {{
        cards[0].textContent = '{report.total_resources}';
        cards[1].textContent = '{report.total_counts.get(SupportStatus.SUPPORTED, 0)}';
        cards[2].textContent = '{report.total_counts.get(SupportStatus.APPROACHING_EOS, 0)}';
        cards[3].textContent = '{report.total_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_1, 0)}';
        cards[4].textContent = '{report.total_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_2, 0)}';
        cards[5].textContent = '{report.total_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_3, 0)}';
        cards[6].textContent = '{report.total_counts.get(SupportStatus.OUT_OF_SUPPORT, 0)}';
    }}
    
    // Reset version detail cards visibility
    document.querySelectorAll('.version-detail-card').forEach(function(card) {{
        card.style.display = '';
    }});
    
    // Reset timeline list items visibility
    document.querySelectorAll('.timeline-item').forEach(function(item) {{
        item.style.display = '';
    }});
    
    // Reset timeline chart to show all data
    if (typeof window.timelineChartInstance !== 'undefined' && window.timelineChartInstance && typeof resetTimelineDateFilter === 'function') {{
        resetTimelineDateFilter();
    }}
    
    // Reset all charts to original data
    resetChartsToOriginal();
}}

// Reset all charts to their original unfiltered data
function resetChartsToOriginal() {{
    // Reset service chart
    var serviceChart = Chart.getChart('serviceChart');
    if (serviceChart) {{
        serviceChart.data.labels = serviceLabelsArray;
        serviceChart.data.datasets[0].data = {service_supported};
        serviceChart.data.datasets[1].data = {service_approaching};
        serviceChart.data.datasets[2].data = {service_extended_year_1};
        serviceChart.data.datasets[3].data = {service_extended_year_2};
        serviceChart.data.datasets[4].data = {service_extended_year_3};
        serviceChart.data.datasets[5].data = {service_out};
        serviceChart.update();
    }}
    
    // Reset account chart
    var accountChart = Chart.getChart('accountChart');
    if (accountChart) {{
        accountChart.data.labels = accountLabelsArray;
        accountChart.data.datasets[0].data = {account_supported};
        accountChart.data.datasets[1].data = {account_approaching};
        accountChart.data.datasets[2].data = {account_extended_year_1};
        accountChart.data.datasets[3].data = {account_extended_year_2};
        accountChart.data.datasets[4].data = {account_extended_year_3};
        accountChart.data.datasets[5].data = {account_out};
        accountChart.update();
    }}
    
    // Reset status pie chart
    var statusPieChart = Chart.getChart('statusPieChart');
    if (statusPieChart) {{
        statusPieChart.data.datasets[0].data = {status_values};
        statusPieChart.update();
    }}
    
    // Reset service pie chart
    var servicePieChart = Chart.getChart('servicePieChart');
    if (servicePieChart) {{
        servicePieChart.data.labels = serviceLabelsArray;
        servicePieChart.data.datasets[0].data = {service_totals};
        servicePieChart.update();
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
                    {{ label: 'Extended Support Y1', data: {service_extended_year_1}, backgroundColor: '#bbdefb' }},
                    {{ label: 'Extended Support Y2', data: {service_extended_year_2}, backgroundColor: '#90caf9' }},
                    {{ label: 'Extended Support Y3', data: {service_extended_year_3}, backgroundColor: '#64b5f6' }},
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
                        // Apply current page filters (account filter)
                        resources = filterResourcesByCurrentFilters(resources);
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
                    {{ label: 'Extended Support Y1', data: {account_extended_year_1}, backgroundColor: '#bbdefb' }},
                    {{ label: 'Extended Support Y2', data: {account_extended_year_2}, backgroundColor: '#90caf9' }},
                    {{ label: 'Extended Support Y3', data: {account_extended_year_3}, backgroundColor: '#64b5f6' }},
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
                        // Apply current page filters (service filter)
                        resources = filterResourcesByCurrentFilters(resources);
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
                labels: ['Supported', 'Approaching EOS', 'Extended Support Y1', 'Extended Support Y2', 'Extended Support Y3', 'Out of Support'],
                datasets: [{{ data: {status_values}, backgroundColor: ['#66bb6a', '#ffa726', '#bbdefb', '#90caf9', '#64b5f6', '#ef5350'] }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                onClick: function(event, elements) {{
                    if (elements.length > 0) {{
                        var index = elements[0].index;
                        var statusKey = statusLabelsMap[index];
                        var resources = statusResourcesData[statusKey] || [];
                        // Apply current page filters (service and account filters)
                        resources = filterResourcesByCurrentFilters(resources);
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
                        // Apply current page filters (account and status filters)
                        resources = filterResourcesByCurrentFilters(resources);
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

// Version Details functions
function toggleVersionDetailCard(anchorId) {{
    var card = document.getElementById('version-detail-' + anchorId);
    if (card) {{
        card.classList.toggle('expanded');
    }}
}}

function expandAllVersionDetails() {{
    document.querySelectorAll('.version-detail-card').forEach(function(card) {{
        card.classList.add('expanded');
    }});
}}

function collapseAllVersionDetails() {{
    document.querySelectorAll('.version-detail-card').forEach(function(card) {{
        card.classList.remove('expanded');
    }});
}}

function scrollToVersionDetail(event, anchorId) {{
    event.preventDefault();
    var card = document.getElementById('version-detail-' + anchorId);
    if (card) {{
        // Expand the card
        card.classList.add('expanded');
        // Scroll to it
        card.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}
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
            scrollX: true,
            language: {{ search: "Search:", lengthMenu: "Show _MENU_ entries" }},
            initComplete: function() {{
                // Add column resizers after DataTable init
                initColumnResizers('#resourcesDataTable');
            }}
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
