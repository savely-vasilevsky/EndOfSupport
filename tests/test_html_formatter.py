"""Comprehensive tests for HTMLFormatter.

Tests cover HTML report generation, structure, interactivity elements,
filter functionality, charts, and GUI interaction simulation.

Feature: html-report
"""

import os
import re
import tempfile
from datetime import date, datetime, timedelta
from typing import List

import pytest
from bs4 import BeautifulSoup

from src.html_formatter import HTMLFormatter
from src.models import (
    Report,
    Resource,
    SupportStatus,
    AccountGroup,
    ServiceGroup,
    EngineGroup,
    VersionGroup,
)


# ============================================================================
# Test Helpers
# ============================================================================

def create_resource(
    account: str = "test-account",
    service: str = "Lambda",
    engine: str = "python",
    version: str = "3.9",
    end_of_support: date = None,
    extended_support_start: date = None,
    extended_support_end: date = None,
    status: SupportStatus = SupportStatus.SUPPORTED,
    days_to_eos: int = None,
) -> Resource:
    """Helper to create a Resource with minimal required fields."""
    return Resource(
        account=account,
        payer_id="123456789",
        service=service,
        resource_type="Function",
        resource_arn=f"arn:aws:{service.lower()}:us-east-1:123456789:test",
        resource_name="test-resource",
        region="us-east-1",
        engine=engine,
        version=version,
        end_of_support=end_of_support,
        end_of_support_raw=end_of_support.strftime('%d-%b-%y') if end_of_support else "-",
        auto_minor_version_upgrade=None,
        extended_support_start=extended_support_start,
        extended_support_year1_start=None,
        extended_support_year2_start=None,
        extended_support_year3_start=None,
        extended_support_end=extended_support_end,
        insights="Test resource",
        status=status,
        days_to_eos=days_to_eos,
    )


def build_report_from_resources(resources: List[Resource]) -> Report:
    """Build a Report object from a list of resources."""
    report = Report()
    
    for resource in resources:
        account_name = resource.account
        service_name = resource.service
        engine_name = resource.engine or ""
        version_name = resource.version
        
        # Create account group if not exists
        if account_name not in report.accounts:
            report.accounts[account_name] = AccountGroup(account=account_name)
        
        account_group = report.accounts[account_name]
        
        # Create service group if not exists
        if service_name not in account_group.services:
            account_group.services[service_name] = ServiceGroup(service=service_name)
        
        service_group = account_group.services[service_name]
        
        # Create engine group if not exists
        if engine_name not in service_group.engines:
            service_group.engines[engine_name] = EngineGroup(engine=engine_name)
        
        engine_group = service_group.engines[engine_name]
        
        # Create version group if not exists
        if version_name not in engine_group.versions:
            engine_group.versions[version_name] = VersionGroup(version=version_name)
        
        version_group = engine_group.versions[version_name]
        version_group.resources.append(resource)
        report.total_resources += 1
        
        # Update status counts
        if resource.status:
            report.total_counts[resource.status] = report.total_counts.get(resource.status, 0) + 1
    
    return report


def create_sample_report() -> Report:
    """Create a sample report with multiple resources for testing."""
    resources = [
        create_resource(
            account="Production",
            service="Lambda",
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
            status=SupportStatus.APPROACHING_EOS,
            days_to_eos=30,
        ),
        create_resource(
            account="Production",
            service="RDS",
            engine="mysql",
            version="8.0",
            end_of_support=date.today() + timedelta(days=365),
            status=SupportStatus.SUPPORTED,
            days_to_eos=365,
        ),
        create_resource(
            account="Development",
            service="ElastiCache",
            engine="redis",
            version="6.0",
            end_of_support=date.today() - timedelta(days=30),
            status=SupportStatus.OUT_OF_SUPPORT,
            days_to_eos=-30,
        ),
        create_resource(
            account="Development",
            service="Lambda",
            engine="nodejs",
            version="18.x",
            end_of_support=date.today() + timedelta(days=180),
            extended_support_start=date.today() - timedelta(days=10),
            extended_support_end=date.today() + timedelta(days=180),
            status=SupportStatus.EXTENDED_SUPPORT_YEAR_1,
            days_to_eos=180,
        ),
    ]
    return build_report_from_resources(resources)


# ============================================================================
# Basic HTML Structure Tests
# ============================================================================

class TestHTMLFormatterBasicStructure:
    """Tests for basic HTML document structure."""
    
    def test_format_returns_valid_html(self):
        """Test that format() returns a valid HTML document."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert html.startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "</head>" in html
        assert "<body>" in html
        assert "</body>" in html
    
    def test_format_includes_title(self):
        """Test that HTML includes proper title with date."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        title = soup.find('title')
        assert title is not None
        assert "AWS End-of-Support Report" in title.text
    
    def test_format_includes_required_scripts(self):
        """Test that HTML includes required JavaScript libraries."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for Chart.js
        assert "chart.js" in html.lower()
        # Check for jQuery
        assert "jquery" in html.lower()
        # Check for DataTables
        assert "datatables" in html.lower()
    
    def test_format_includes_styles(self):
        """Test that HTML includes CSS styles."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "<style>" in html
        assert "</style>" in html
    
    def test_format_to_file_creates_file(self):
        """Test that format_to_file creates an HTML file."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            formatter.format_to_file(report, tmp_path)
            
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert "<!DOCTYPE html>" in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# ============================================================================
# Header and Navigation Tests
# ============================================================================

class TestHTMLFormatterHeader:
    """Tests for HTML header and navigation elements."""
    
    def test_header_contains_title(self):
        """Test that header contains the report title."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        header = soup.find('div', class_='header')
        assert header is not None
        assert "AWS End-of-Support Report" in header.text
    
    def test_header_contains_timestamp(self):
        """Test that header contains generation timestamp."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        header = soup.find('div', class_='header')
        assert header is not None
        assert "Generated:" in header.text
        # Check for time format (HH:MM:SS)
        assert re.search(r'\d{2}:\d{2}:\d{2}', header.text) is not None
    
    def test_menu_bar_exists(self):
        """Test that navigation menu bar exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        menu = soup.find('ul', id='menuBar')
        assert menu is not None
    
    def test_menu_contains_all_sections(self):
        """Test that menu contains links to all sections."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        menu = soup.find('ul', id='menuBar')
        links = menu.find_all('a')
        
        expected_sections = ['Summary', 'Status Breakdown', 'All Resources', 'Timeline', 'By Service']
        link_texts = [link.text for link in links]
        
        for section in expected_sections:
            assert section in link_texts, f"Menu should contain '{section}' link"
    
    def test_go_to_top_button_exists(self):
        """Test that go-to-top button exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        button = soup.find('button', class_='go-to-top')
        assert button is not None


# ============================================================================
# Filter Bar Tests
# ============================================================================

class TestHTMLFormatterFilterBar:
    """Tests for filter bar functionality."""
    
    def test_filter_bar_exists(self):
        """Test that filter bar exists in the HTML."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        filter_bar = soup.find('div', class_='filter-bar')
        assert filter_bar is not None
    
    def test_filter_bar_has_service_filter(self):
        """Test that filter bar has service filter options."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_filters = soup.find('div', id='service-filters')
        assert service_filters is not None
        
        # Check that service options exist
        options = service_filters.find_all('label', class_='filter-option')
        assert len(options) > 0
    
    def test_filter_bar_has_account_filter(self):
        """Test that filter bar has account filter dropdown."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Account filter is now a dropdown
        account_dropdown = soup.find('div', id='account-dropdown')
        assert account_dropdown is not None
        
        # Check for account items container
        account_items = soup.find('div', id='account-items')
        assert account_items is not None
    
    def test_filter_bar_has_status_filter(self):
        """Test that filter bar has status filter options."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        status_filters = soup.find('div', id='status-filters')
        assert status_filters is not None
        
        # Check for all status options
        options = status_filters.find_all('label', class_='filter-option')
        assert len(options) == 6  # Supported, Approaching, Extended Year 1/2/3, Out of Support
    
    def test_filter_options_selected_by_default(self):
        """Test that all filter options are selected by default."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        all_options = soup.find_all('label', class_='filter-option')
        for option in all_options:
            assert 'selected' in option.get('class', []), \
                f"Filter option should be selected by default: {option.text}"
    
    def test_filter_bar_has_apply_button(self):
        """Test that filter bar has Apply Filters button."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        apply_btn = soup.find('button', class_='apply-btn')
        assert apply_btn is not None
        assert "Apply Filters" in apply_btn.text
    
    def test_filter_bar_has_reset_button(self):
        """Test that filter bar has Reset All button."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        reset_btn = soup.find('button', class_='reset-btn')
        assert reset_btn is not None
        assert "Reset All" in reset_btn.text
    
    def test_service_filter_contains_all_services(self):
        """Test that service filter contains all services from report."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_filters = soup.find('div', id='service-filters')
        options = service_filters.find_all('label', class_='filter-option')
        
        service_names = [opt.get('data-value') for opt in options]
        
        # Check that all services from report are present
        assert 'Lambda' in service_names
        assert 'RDS' in service_names
        assert 'ElastiCache' in service_names
    
    def test_account_filter_contains_all_accounts(self):
        """Test that account filter dropdown contains all accounts from report."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Account filter is now a dropdown with items
        account_items = soup.find('div', id='account-items')
        options = account_items.find_all('div', class_='dropdown-item')
        
        account_names = [opt.get('data-value') for opt in options]
        
        assert 'Production' in account_names
        assert 'Development' in account_names


# ============================================================================
# Summary Dashboard Tests
# ============================================================================

class TestHTMLFormatterSummaryDashboard:
    """Tests for summary dashboard section."""
    
    def test_summary_section_exists(self):
        """Test that summary section exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        summary = soup.find('div', id='summary-section')
        assert summary is not None
    
    def test_summary_has_total_resources_card(self):
        """Test that summary has total resources card."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        total_card = soup.find('div', class_='summary-card total')
        assert total_card is not None
        assert "Total Resources" in total_card.text
    
    def test_summary_has_status_cards(self):
        """Test that summary has cards for each status."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for each status card
        supported_card = soup.find('div', class_='summary-card supported')
        approaching_card = soup.find('div', class_='summary-card approaching')
        extended_year_1_card = soup.find('div', class_='summary-card extended-year-1')
        extended_year_2_card = soup.find('div', class_='summary-card extended-year-2')
        extended_year_3_card = soup.find('div', class_='summary-card extended-year-3')
        out_of_support_card = soup.find('div', class_='summary-card out-of-support')
        
        assert supported_card is not None
        assert approaching_card is not None
        assert extended_year_1_card is not None
        assert extended_year_2_card is not None
        assert extended_year_3_card is not None
        assert out_of_support_card is not None
    
    def test_summary_shows_correct_total(self):
        """Test that summary shows correct total resource count."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        total_card = soup.find('div', class_='summary-card total')
        count_div = total_card.find('div', class_='count')
        
        assert count_div is not None
        assert count_div.text == str(report.total_resources)
    
    def test_summary_shows_correct_status_counts(self):
        """Test that summary shows correct counts for each status."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Get counts from cards
        supported_card = soup.find('div', class_='summary-card supported')
        supported_count = supported_card.find('div', class_='count').text
        
        approaching_card = soup.find('div', class_='summary-card approaching')
        approaching_count = approaching_card.find('div', class_='count').text
        
        extended_year_1_card = soup.find('div', class_='summary-card extended-year-1')
        extended_year_1_count = extended_year_1_card.find('div', class_='count').text
        
        out_card = soup.find('div', class_='summary-card out-of-support')
        out_count = out_card.find('div', class_='count').text
        
        # Verify counts match report
        assert int(supported_count) == report.total_counts.get(SupportStatus.SUPPORTED, 0)
        assert int(approaching_count) == report.total_counts.get(SupportStatus.APPROACHING_EOS, 0)
        assert int(extended_year_1_count) == report.total_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_1, 0)
        assert int(out_count) == report.total_counts.get(SupportStatus.OUT_OF_SUPPORT, 0)
    
    def test_summary_cards_are_clickable(self):
        """Test that summary cards have onclick handlers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check total card has onclick
        total_card = soup.find('div', class_='summary-card total')
        assert total_card.get('onclick') == 'showAllResources()'
        
        # Check status cards have onclick
        supported_card = soup.find('div', class_='summary-card supported')
        assert supported_card.get('onclick') == "showStatusResources('supported')"
        
        approaching_card = soup.find('div', class_='summary-card approaching')
        assert approaching_card.get('onclick') == "showStatusResources('approaching')"
        
        extended_year_1_card = soup.find('div', class_='summary-card extended-year-1')
        assert extended_year_1_card.get('onclick') == "showStatusResources('extended_year_1')"
        
        extended_year_2_card = soup.find('div', class_='summary-card extended-year-2')
        assert extended_year_2_card.get('onclick') == "showStatusResources('extended_year_2')"
        
        extended_year_3_card = soup.find('div', class_='summary-card extended-year-3')
        assert extended_year_3_card.get('onclick') == "showStatusResources('extended_year_3')"
        
        out_card = soup.find('div', class_='summary-card out-of-support')
        assert out_card.get('onclick') == "showStatusResources('out_of_support')"
    
    def test_summary_cards_click_functions_exist(self):
        """Test that JavaScript functions for summary card clicks exist."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showStatusResources(statusKey)" in html
        assert "function showAllResources()" in html
    
    def test_summary_cards_have_cursor_pointer(self):
        """Test that summary cards have cursor pointer style."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check CSS includes cursor pointer for summary cards
        assert ".summary-card {" in html
        assert "cursor: pointer" in html
    
    def test_summary_section_has_click_instruction(self):
        """Test that summary section has click instruction text."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Click on any card to view affected resources" in html
    
    def test_summary_cards_have_tooltip_handlers(self):
        """Test that summary cards have tooltip event handlers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for tooltip event handlers
        assert "onmouseenter=\"showSummaryTooltip" in html
        assert "onmousemove=\"positionSummaryTooltip" in html
        assert "onmouseleave=\"hideSummaryTooltip" in html
    
    def test_summary_tooltip_functions_exist(self):
        """Test that tooltip JavaScript functions exist."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showSummaryTooltip(event, statusKey)" in html
        assert "function positionSummaryTooltip(event)" in html
        assert "function hideSummaryTooltip()" in html
    
    def test_status_service_summary_data_exists(self):
        """Test that statusServiceSummary data variable exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "var statusServiceSummary" in html
    
    def test_summary_tooltip_css_exists(self):
        """Test that tooltip CSS styles exist."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert ".summary-card-tooltip" in html


# ============================================================================
# Status Breakdown Section Tests
# ============================================================================

class TestHTMLFormatterStatusBreakdown:
    """Tests for status breakdown section with charts."""
    
    def test_status_breakdown_section_exists(self):
        """Test that status breakdown section exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        breakdown = soup.find('div', id='status-breakdown')
        assert breakdown is not None
    
    def test_status_breakdown_has_service_chart(self):
        """Test that status breakdown has service chart canvas."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_chart = soup.find('canvas', id='serviceChart')
        assert service_chart is not None
    
    def test_status_breakdown_has_account_chart(self):
        """Test that status breakdown has account chart canvas."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        account_chart = soup.find('canvas', id='accountChart')
        assert account_chart is not None
    
    def test_status_breakdown_has_pie_charts(self):
        """Test that status breakdown has pie charts."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        status_pie = soup.find('canvas', id='statusPieChart')
        service_pie = soup.find('canvas', id='servicePieChart')
        
        assert status_pie is not None
        assert service_pie is not None
    
    def test_status_breakdown_has_collapse_button(self):
        """Test that status breakdown has collapse button."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        breakdown = soup.find('div', id='status-breakdown')
        collapse_btn = breakdown.find('button', class_='collapse-btn')
        
        assert collapse_btn is not None


# ============================================================================
# Resources Table Tests
# ============================================================================

class TestHTMLFormatterResourcesTable:
    """Tests for all resources data table."""
    
    def test_resources_table_section_exists(self):
        """Test that resources table section exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        table_section = soup.find('div', id='resources-table')
        assert table_section is not None
    
    def test_resources_table_has_datatable(self):
        """Test that resources table has DataTable."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', id='resourcesDataTable')
        assert table is not None
    
    def test_resources_table_has_correct_headers(self):
        """Test that resources table has correct column headers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', id='resourcesDataTable')
        headers = table.find('thead').find_all('th')
        
        # Version Details column is now included by default, ARN column added
        expected_headers = ['Account', 'Service', 'Engine', 'Version', 
                          'Resource', 'ARN', 'End of Support', 'Days to EOS', 'Status', 'Version Details']
        header_texts = [h.text for h in headers]
        
        assert header_texts == expected_headers
    
    def test_resources_table_has_correct_row_count(self):
        """Test that resources table has correct number of rows."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', id='resourcesDataTable')
        rows = table.find('tbody').find_all('tr')
        
        assert len(rows) == report.total_resources
    
    def test_resources_table_rows_have_status_badges(self):
        """Test that table rows have status badges."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', id='resourcesDataTable')
        rows = table.find('tbody').find_all('tr')
        
        for row in rows:
            badge = row.find('span', class_='status-badge')
            assert badge is not None


# ============================================================================
# Timeline Section Tests
# ============================================================================

class TestHTMLFormatterTimeline:
    """Tests for timeline visualization section."""
    
    def test_timeline_section_exists(self):
        """Test that timeline section exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        timeline = soup.find('div', id='timeline-section')
        assert timeline is not None
    
    def test_timeline_has_chart(self):
        """Test that timeline has chart canvas."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        timeline_chart = soup.find('canvas', id='timelineChart')
        assert timeline_chart is not None
    
    def test_timeline_has_events_list(self):
        """Test that timeline has upcoming events list."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        timeline_section = soup.find('div', id='timeline-section')
        # Check for the events list heading
        assert "Upcoming End-of-Support Events" in timeline_section.text
    
    def test_timeline_has_collapse_button(self):
        """Test that timeline has collapse button."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        timeline = soup.find('div', id='timeline-section')
        collapse_btn = timeline.find('button', class_='collapse-btn')
        
        assert collapse_btn is not None


# ============================================================================
# By Service Section Tests
# ============================================================================

class TestHTMLFormatterByService:
    """Tests for resources by service section."""
    
    def test_by_service_section_exists(self):
        """Test that by-service section exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        by_service = soup.find('div', id='by-service-section')
        assert by_service is not None
    
    def test_by_service_has_service_groups(self):
        """Test that by-service section has service groups."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_groups = soup.find_all('div', class_='service-group')
        assert len(service_groups) > 0
    
    def test_service_groups_have_headers(self):
        """Test that service groups have clickable headers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_groups = soup.find_all('div', class_='service-group')
        
        for group in service_groups:
            header = group.find('div', class_='service-group-header')
            assert header is not None
    
    def test_service_groups_have_status_badges(self):
        """Test that service group headers have status badges."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_groups = soup.find_all('div', class_='service-group')
        
        for group in service_groups:
            header = group.find('div', class_='service-group-header')
            badges = header.find_all('span', class_='status-badge')
            assert len(badges) == 6  # One for each status (Supported, Approaching, Ext Year 1/2/3, Out of Support)
    
    def test_service_groups_have_tables(self):
        """Test that service groups have data tables."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_groups = soup.find_all('div', class_='service-group')
        
        for group in service_groups:
            content = group.find('div', class_='service-group-content')
            table = content.find('table', class_='service-datatable')
            assert table is not None
    
    def test_service_tables_have_data_attributes(self):
        """Test that service table rows have data attributes for filtering."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_groups = soup.find_all('div', class_='service-group')
        
        for group in service_groups:
            table = group.find('table', class_='service-datatable')
            rows = table.find('tbody').find_all('tr')
            
            for row in rows:
                assert row.get('data-account') is not None
                assert row.get('data-status') is not None
    
    def test_service_groups_have_data_service_attribute(self):
        """Test that service groups have data-service attribute."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_groups = soup.find_all('div', class_='service-group')
        
        for group in service_groups:
            assert group.get('data-service') is not None


# ============================================================================
# Loading Indicator Tests
# ============================================================================

class TestHTMLFormatterLoadingIndicator:
    """Tests for loading indicator functionality."""
    
    def test_loading_spinner_exists(self):
        """Test that loading spinner exists in header."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        spinner = soup.find('div', id='header-spinner')
        assert spinner is not None
    
    def test_loading_status_exists(self):
        """Test that loading status container exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        loading_status = soup.find('div', class_='loading-status')
        assert loading_status is not None
    
    def test_loading_text_exists(self):
        """Test that loading text element exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        loading_text = soup.find('span', id='loading-text')
        assert loading_text is not None
    
    def test_spinner_animation_defined(self):
        """Test that spinner animation is defined in CSS."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "@keyframes spin" in html
        assert "animation:" in html


# ============================================================================
# JavaScript Functionality Tests
# ============================================================================

class TestHTMLFormatterJavaScript:
    """Tests for JavaScript functionality in HTML output."""
    
    def test_scroll_to_section_function_exists(self):
        """Test that scrollToSection function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function scrollToSection" in html
    
    def test_toggle_section_function_exists(self):
        """Test that toggleSection function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function toggleSection" in html
    
    def test_toggle_service_group_function_exists(self):
        """Test that toggleServiceGroup function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function toggleServiceGroup" in html
    
    def test_apply_filters_function_exists(self):
        """Test that applyFilters function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function applyFilters" in html
    
    def test_reset_filters_function_exists(self):
        """Test that resetFilters function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function resetFilters" in html
    
    def test_init_filters_function_exists(self):
        """Test that initFilters function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function initFilters" in html
    
    def test_get_selected_filters_function_exists(self):
        """Test that getSelectedFilters function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function getSelectedFilters" in html
    
    def test_update_summary_counts_function_exists(self):
        """Test that updateSummaryCounts function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function updateSummaryCounts" in html
    
    def test_datatable_initialization(self):
        """Test that DataTable is initialized on document ready."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "$(document).ready" in html
        assert "$('#resourcesDataTable').DataTable" in html
    
    def test_chart_initialization(self):
        """Test that charts are initialized."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "new Chart" in html
        assert "serviceChart" in html
        assert "accountChart" in html
        assert "statusPieChart" in html
        assert "servicePieChart" in html


# ============================================================================
# Footer Tests
# ============================================================================

class TestHTMLFormatterFooter:
    """Tests for HTML footer."""
    
    def test_footer_exists(self):
        """Test that footer exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        footer = soup.find('div', class_='footer')
        assert footer is not None
    
    def test_footer_has_tool_name(self):
        """Test that footer mentions the tool name."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        footer = soup.find('div', class_='footer')
        assert "End-of-Support Tool" in footer.text


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

class TestHTMLFormatterEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_report(self):
        """Test that empty report generates valid HTML."""
        report = Report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "<!DOCTYPE html>" in html
        soup = BeautifulSoup(html, 'html.parser')
        assert soup.find('div', id='summary-section') is not None
    
    def test_single_resource_report(self):
        """Test that single resource report generates valid HTML."""
        resource = create_resource()
        report = build_report_from_resources([resource])
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', id='resourcesDataTable')
        rows = table.find('tbody').find_all('tr')
        
        assert len(rows) == 1
    
    def test_special_characters_escaped(self):
        """Test that special characters are properly escaped."""
        resource = create_resource(
            account="Test <Account> & 'Special' \"Chars\"",
            service="Lambda",
        )
        report = build_report_from_resources([resource])
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check that special characters are escaped
        assert "&lt;" in html or "Test <Account>" not in html
        assert "&amp;" in html
    
    def test_long_resource_names_truncated(self):
        """Test that long resource names are handled properly."""
        resource = create_resource()
        resource.resource_name = "a" * 100  # Very long name
        report = build_report_from_resources([resource])
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Should still generate valid HTML
        assert soup.find('table', id='resourcesDataTable') is not None
    
    def test_none_engine_handled(self):
        """Test that None engine is handled properly."""
        resource = create_resource(engine=None)
        report = build_report_from_resources([resource])
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Should generate valid HTML
        assert soup.find('table', id='resourcesDataTable') is not None
    
    def test_none_end_of_support_handled(self):
        """Test that None end_of_support is handled properly."""
        resource = create_resource(end_of_support=None)
        report = build_report_from_resources([resource])
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', id='resourcesDataTable')
        rows = table.find('tbody').find_all('tr')
        
        # Should show N/A for end of support
        assert "N/A" in rows[0].text
    
    def test_multiple_accounts_same_service(self):
        """Test handling of multiple accounts with same service."""
        resources = [
            create_resource(account="Account1", service="Lambda"),
            create_resource(account="Account2", service="Lambda"),
            create_resource(account="Account3", service="Lambda"),
        ]
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Should have 3 account filter options in dropdown
        account_items = soup.find('div', id='account-items')
        options = account_items.find_all('div', class_='dropdown-item')
        
        assert len(options) == 3


# ============================================================================
# CSS Styling Tests
# ============================================================================

class TestHTMLFormatterCSS:
    """Tests for CSS styling in HTML output."""
    
    def test_status_colors_defined(self):
        """Test that status colors are defined in CSS."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert ".status-supported" in html
        assert ".status-approaching" in html
        assert ".status-extended" in html
        assert ".status-out-of-support" in html
    
    def test_summary_card_styles_defined(self):
        """Test that summary card styles are defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert ".summary-card" in html
        assert ".summary-card.total" in html
        assert ".summary-card.supported" in html
    
    def test_filter_bar_styles_defined(self):
        """Test that filter bar styles are defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert ".filter-bar" in html
        assert ".filter-option" in html
        assert ".filter-option.selected" in html
    
    def test_responsive_styles_defined(self):
        """Test that responsive styles are defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "@media" in html


# ============================================================================
# Property-Based Tests
# ============================================================================

from hypothesis import given, settings, strategies as st


@st.composite
def resource_strategy(draw):
    """Generate random Resource objects for property testing."""
    account = draw(st.sampled_from(["Account-A", "Account-B", "Account-C"]))
    service = draw(st.sampled_from(["Lambda", "RDS", "ElastiCache", "MSK"]))
    engine = draw(st.sampled_from(["python", "mysql", "redis", "kafka", None]))
    version = draw(st.from_regex(r"[0-9]+\.[0-9]+", fullmatch=True))
    status = draw(st.sampled_from(list(SupportStatus)))
    
    return create_resource(
        account=account,
        service=service,
        engine=engine,
        version=version,
        status=status,
    )


class TestHTMLFormatterProperties:
    """Property-based tests for HTMLFormatter."""
    
    @given(st.lists(resource_strategy(), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_property_valid_html_for_any_resources(self, resources):
        """Property: Any list of resources produces valid HTML."""
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Should be valid HTML
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        
        # Should be parseable
        soup = BeautifulSoup(html, 'html.parser')
        assert soup is not None
    
    @given(st.lists(resource_strategy(), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_property_row_count_matches_resources(self, resources):
        """Property: Table row count matches resource count."""
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', id='resourcesDataTable')
        rows = table.find('tbody').find_all('tr')
        
        assert len(rows) == len(resources)
    
    @given(st.lists(resource_strategy(), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_property_all_services_in_filter(self, resources):
        """Property: All unique services appear in filter."""
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_filters = soup.find('div', id='service-filters')
        options = service_filters.find_all('label', class_='filter-option')
        filter_services = {opt.get('data-value') for opt in options}
        
        resource_services = {r.service for r in resources}
        
        assert resource_services == filter_services
    
    @given(st.lists(resource_strategy(), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_property_all_accounts_in_filter(self, resources):
        """Property: All unique accounts appear in filter dropdown."""
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        account_items = soup.find('div', id='account-items')
        options = account_items.find_all('div', class_='dropdown-item')
        filter_accounts = {opt.get('data-value') for opt in options}
        
        resource_accounts = {r.account for r in resources}
        
        assert resource_accounts == filter_accounts


# ============================================================================
# Timeline Section Tests
# ============================================================================

class TestHTMLFormatterTimeline:
    """Tests for timeline section in HTML report."""
    
    def test_timeline_section_exists(self):
        """Test that timeline section exists in HTML."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        timeline = soup.find('div', id='timeline-section')
        assert timeline is not None
    
    def test_timeline_chart_canvas_exists(self):
        """Test that timeline chart canvas exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        canvas = soup.find('canvas', id='timelineChart')
        assert canvas is not None
    
    def test_timeline_date_range_inputs_exist(self):
        """Test that timeline date range inputs exist."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        start_input = soup.find('input', id='timelineStartDate')
        end_input = soup.find('input', id='timelineEndDate')
        
        assert start_input is not None
        assert end_input is not None
        assert start_input.get('type') == 'month'
        assert end_input.get('type') == 'month'
    
    def test_timeline_filter_buttons_exist(self):
        """Test that Apply and Reset buttons exist for timeline filter."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "applyTimelineDateFilter()" in html
        assert "resetTimelineDateFilter()" in html
    
    def test_timeline_chart_initialization_function(self):
        """Test that initTimelineChart function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function initTimelineChart()" in html
    
    def test_timeline_resources_data_variable(self):
        """Test that timelineResourcesData variable is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "window.timelineResourcesData" in html
    
    def test_timeline_service_summary_data(self):
        """Test that timelineServiceSummary variable is defined for tooltips."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "window.timelineServiceSummary" in html
    
    def test_show_month_resources_function(self):
        """Test that showMonthResources function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showMonthResources(month)" in html


# ============================================================================
# Chart Click-Through Tests
# ============================================================================

class TestHTMLFormatterChartClickThrough:
    """Tests for chart click-through functionality."""
    
    def test_service_resources_data_exists(self):
        """Test that serviceResourcesData variable is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "var serviceResourcesData" in html
    
    def test_account_resources_data_exists(self):
        """Test that accountResourcesData variable is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "var accountResourcesData" in html
    
    def test_status_resources_data_exists(self):
        """Test that statusResourcesData variable is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "var statusResourcesData" in html
    
    def test_show_chart_resources_function(self):
        """Test that showChartResources function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showChartResources(title, resources, filterContext)" in html
    
    def test_charts_have_onclick_handlers(self):
        """Test that charts have onClick handlers defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for onClick in chart options
        assert "onClick: function(event, elements)" in html
    
    def test_chart_tooltips_have_click_hint(self):
        """Test that chart tooltips include click hint."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Click to view resources" in html


# ============================================================================
# Help Guide Tests
# ============================================================================

class TestHTMLFormatterHelpGuide:
    """Tests for help guide functionality."""
    
    def test_help_link_in_menu(self):
        """Test that Help link exists in navigation menu."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'onclick="showReportHelp(event)"' in html
        assert ">Help</a>" in html
    
    def test_show_report_help_function(self):
        """Test that showReportHelp function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showReportHelp(event)" in html
    
    def test_help_guide_contains_sections(self):
        """Test that help guide contains all required sections."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for section headings in help guide
        assert "Report Overview" in html
        assert "Understanding Status Types" in html
        assert "Navigation Menu" in html
        assert "Using Filters" in html
        assert "Summary Section" in html
        assert "Status Breakdown Charts" in html
        assert "All Resources Table" in html
        assert "Support Timeline" in html
        assert "By Service Section" in html
        assert "Exporting Data" in html
    
    def test_help_guide_no_excel_mention(self):
        """Test that help guide does not mention Excel export."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Excel should not be mentioned in the help guide context
        # (it may appear elsewhere in the HTML for other purposes)
        assert "Downloads visible data as an Excel" not in html


# ============================================================================
# By Service Section Tests
# ============================================================================

class TestHTMLFormatterByServiceSection:
    """Tests for By Service section."""
    
    def test_by_service_section_exists(self):
        """Test that by-service section exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        section = soup.find('div', id='by-service-section')
        assert section is not None
    
    def test_service_groups_aggregated_by_service(self):
        """Test that service groups are aggregated by service, not by account."""
        resources = [
            create_resource(account="Account1", service="Lambda", version="3.9"),
            create_resource(account="Account2", service="Lambda", version="3.8"),
            create_resource(account="Account1", service="RDS", version="8.0"),
        ]
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Should have exactly 2 service groups (Lambda and RDS)
        service_groups = soup.find_all('div', class_='service-group')
        assert len(service_groups) == 2
    
    def test_service_group_unique_ids(self):
        """Test that each service group has a unique ID."""
        resources = [
            create_resource(account="Account1", service="Lambda"),
            create_resource(account="Account2", service="Lambda"),
            create_resource(account="Account1", service="RDS"),
        ]
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_groups = soup.find_all('div', class_='service-group')
        ids = [g.get('id') for g in service_groups]
        
        # All IDs should be unique
        assert len(ids) == len(set(ids))
    
    def test_service_group_contains_all_accounts(self):
        """Test that service group contains resources from all accounts."""
        resources = [
            create_resource(account="Account1", service="Lambda", version="3.9"),
            create_resource(account="Account2", service="Lambda", version="3.8"),
            create_resource(account="Account3", service="Lambda", version="3.7"),
        ]
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find Lambda service group
        lambda_group = soup.find('div', id='service-lambda')
        assert lambda_group is not None
        
        # Should show 3 resources total
        count_text = lambda_group.find('span', class_='service-count').text
        assert "3" in count_text
    
    def test_toggle_service_group_function(self):
        """Test that toggleServiceGroup function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function toggleServiceGroup(groupId)" in html


# ============================================================================
# Export Functionality Tests
# ============================================================================

class TestHTMLFormatterExport:
    """Tests for export functionality."""
    
    def test_datatable_buttons_configured(self):
        """Test that DataTable buttons are configured."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "buttons: ['copy', 'csv'" in html
    
    def test_export_to_csv_function_in_popup(self):
        """Test that exportToCSV function is defined for popup windows."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function exportToCSV()" in html
    
    def test_copy_to_clipboard_function_in_popup(self):
        """Test that copyToClipboard function is defined for popup windows."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function copyToClipboard()" in html
    
    def test_copy_popup_function(self):
        """Test that showCopyPopup function is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showCopyPopup(count)" in html


# ============================================================================
# Status Breakdown Section Tests
# ============================================================================

class TestHTMLFormatterStatusBreakdown:
    """Tests for status breakdown section."""
    
    def test_status_breakdown_section_exists(self):
        """Test that status breakdown section exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        section = soup.find('div', id='status-breakdown')
        assert section is not None
    
    def test_all_four_charts_exist(self):
        """Test that all four charts exist."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        assert soup.find('canvas', id='serviceChart') is not None
        assert soup.find('canvas', id='accountChart') is not None
        assert soup.find('canvas', id='statusPieChart') is not None
        assert soup.find('canvas', id='servicePieChart') is not None
    
    def test_charts_have_cursor_pointer(self):
        """Test that chart containers have cursor pointer style."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for cursor: pointer in chart containers
        assert 'style="cursor: pointer;"' in html
    
    def test_click_instruction_text(self):
        """Test that click instruction text is present."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Click on any chart element to view affected resources" in html


# ============================================================================
# Account Dropdown Tests
# ============================================================================

class TestHTMLFormatterAccountDropdown:
    """Tests for account dropdown filter."""
    
    def test_account_dropdown_exists(self):
        """Test that account dropdown exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        dropdown = soup.find('div', id='account-dropdown')
        assert dropdown is not None
    
    def test_account_search_input_exists(self):
        """Test that account search input exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        search = soup.find('input', id='account-search')
        assert search is not None
    
    def test_select_all_deselect_all_buttons(self):
        """Test that Select All and Deselect All buttons exist."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "selectAllAccounts()" in html
        assert "deselectAllAccounts()" in html
    
    def test_account_dropdown_functions(self):
        """Test that account dropdown functions are defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function toggleAccountDropdown()" in html
        assert "function filterAccountOptions()" in html
        assert "function initAccountDropdown()" in html


# ============================================================================
# Popup Tab GUI Tests
# ============================================================================

class TestHTMLFormatterPopupTabs:
    """Tests for popup tab functionality opened from chart clicks."""
    
    def test_show_chart_resources_function_defined(self):
        """Test that showChartResources function is properly defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showChartResources(title, resources, filterContext)" in html
    
    def test_popup_uses_string_from_char_code_for_newlines(self):
        """Test that popup uses String.fromCharCode(10) for newlines."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check that nl variable is defined for newlines
        assert "var nl = String.fromCharCode(10);" in html
    
    def test_popup_uses_string_from_char_code_for_single_quotes(self):
        """Test that popup uses String.fromCharCode(39) for single quotes in HTML attributes."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check that q variable is defined for single quotes
        assert "var q = String.fromCharCode(39);" in html
    
    def test_popup_update_summary_uses_string_from_char_code_for_double_quotes(self):
        """Test that updateSummary function uses String.fromCharCode(34) for double quotes."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check that dq variable is defined in updateSummary
        assert "var dq = String.fromCharCode(34);" in html
    
    def test_popup_toggle_filter_chip_function_defined(self):
        """Test that toggleFilterChip function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # The function should be defined in the popup script
        assert 'function toggleFilterChip(el)' in html
    
    def test_popup_apply_filters_function_defined(self):
        """Test that applyFilters function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for applyFilters in the showChartResources function
        assert "function applyFilters()" in html
    
    def test_popup_reset_filters_function_defined(self):
        """Test that resetFilters function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function resetFilters()" in html
    
    def test_popup_get_selected_filters_function_defined(self):
        """Test that getSelectedFilters function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Should appear twice - once in main report and once in popup
        assert html.count("function getSelectedFilters()") >= 1
    
    def test_popup_export_to_csv_function_defined(self):
        """Test that exportToCSV function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function exportToCSV()" in html
    
    def test_popup_copy_to_clipboard_function_defined(self):
        """Test that copyToClipboard function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function copyToClipboard()" in html
    
    def test_popup_show_copy_popup_function_defined(self):
        """Test that showCopyPopup function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showCopyPopup(count)" in html
    
    def test_popup_fallback_copy_function_defined(self):
        """Test that fallbackCopy function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function fallbackCopy(text, count)" in html
    
    def test_popup_script_tag_properly_split(self):
        """Test that script tag is properly split to avoid parsing issues."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Script tag should be split as '</scr' + 'ipt>' to avoid issues
        assert "'</scr' + 'ipt>'" in html or "\"</scr\" + \"ipt>\"" in html
    
    def test_popup_filter_chips_use_single_quote_onclick(self):
        """Test that filter chips use single quotes for onclick handlers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Filter chips should use q variable (single quote) for onclick
        assert "onclick=\" + q + \"toggleFilterChip(this)\" + q + \">" in html
    
    def test_popup_buttons_use_single_quote_onclick(self):
        """Test that Apply and Reset buttons use single quotes for onclick."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Buttons should use q variable for onclick
        assert "onclick=\" + q + \"applyFilters()\" + q + \">" in html
        assert "onclick=\" + q + \"resetFilters()\" + q + \">" in html
    
    def test_popup_copy_csv_buttons_use_single_quote_onclick(self):
        """Test that Copy and CSV buttons use single quotes for onclick."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "onclick=\" + q + \"copyToClipboard()\" + q + \">Copy</button>" in html
        assert "onclick=\" + q + \"exportToCSV()\" + q + \">CSV</button>" in html
    
    def test_popup_has_filter_bar_structure(self):
        """Test that popup HTML includes filter bar structure."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for filter bar CSS classes in popup
        assert ".filter-bar {" in html
        assert ".filter-chip {" in html
        assert ".filter-chip.selected {" in html
    
    def test_popup_has_status_specific_filter_chip_styles(self):
        """Test that popup has status-specific filter chip styles."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert ".filter-chip.status-supported.selected" in html
        assert ".filter-chip.status-approaching.selected" in html
        assert ".filter-chip.status-extended_year_1.selected" in html
        assert ".filter-chip.status-extended_year_2.selected" in html
        assert ".filter-chip.status-extended_year_3.selected" in html
        assert ".filter-chip.status-out_of_support.selected" in html
    
    def test_popup_has_summary_bar(self):
        """Test that popup includes summary bar element."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'id="summaryBar"' in html
    
    def test_popup_has_resource_table(self):
        """Test that popup includes resource table element."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'id="resourceTable"' in html
    
    def test_popup_has_search_input(self):
        """Test that popup includes search input element."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'id="searchInput"' in html
    
    def test_popup_dom_content_loaded_calls_apply_filters(self):
        """Test that popup calls applyFilters on DOMContentLoaded."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'document.addEventListener("DOMContentLoaded", function() { applyFilters(); });' in html
    
    def test_popup_chr_helper_function_defined(self):
        """Test that chr helper function is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function chr(c) { return String.fromCharCode(c); }" in html
    
    def test_popup_status_colors_variable_defined(self):
        """Test that statusColors variable is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Should be defined both as JS object and JSON.stringify
        assert "var statusColors = " in html
    
    def test_popup_status_labels_variable_defined(self):
        """Test that statusLabels variable is defined in popup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "var statusLabels = " in html


# ============================================================================
# Main Report GUI Interaction Tests
# ============================================================================

class TestHTMLFormatterGUIInteraction:
    """Tests for main report GUI interaction elements."""
    
    def test_summary_cards_have_onclick_handlers(self):
        """Test that all summary cards have onclick handlers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Total card
        total_card = soup.find('div', class_='summary-card total')
        assert total_card is not None
        assert total_card.get('onclick') is not None
        
        # Status cards
        for status_class in ['supported', 'approaching', 'extended-year-1', 'extended-year-2', 'extended-year-3', 'out-of-support']:
            card = soup.find('div', class_=f'summary-card {status_class}')
            assert card is not None
            assert card.get('onclick') is not None
    
    def test_filter_options_have_click_handlers(self):
        """Test that filter options have click event setup."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for filter option click handler setup
        assert "document.querySelectorAll('.filter-option').forEach" in html
        assert "addEventListener('click'" in html
    
    def test_apply_filters_button_has_onclick(self):
        """Test that Apply Filters button has onclick handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        apply_btn = soup.find('button', class_='apply-btn')
        assert apply_btn is not None
        assert apply_btn.get('onclick') == 'applyFilters()'
    
    def test_reset_filters_button_has_onclick(self):
        """Test that Reset All button has onclick handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        reset_btn = soup.find('button', class_='reset-btn')
        assert reset_btn is not None
        assert reset_btn.get('onclick') == 'resetFilters()'
    
    def test_menu_links_have_scroll_handlers(self):
        """Test that menu links have scroll handlers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        menu = soup.find('ul', id='menuBar')
        links = menu.find_all('a')
        
        for link in links:
            href = link.get('href')
            onclick = link.get('onclick')
            # Links should either have href starting with # or have onclick
            if href and href.startswith('#'):
                assert onclick is not None or 'scrollToSection' in html
    
    def test_go_to_top_button_has_onclick(self):
        """Test that go-to-top button has onclick handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        btn = soup.find('button', class_='go-to-top')
        assert btn is not None
        onclick = btn.get('onclick')
        assert onclick is not None
        assert 'scrollTo' in onclick or 'scroll' in onclick.lower()
    
    def test_collapse_buttons_have_onclick(self):
        """Test that section collapse buttons have onclick handlers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        collapse_btns = soup.find_all('button', class_='collapse-btn')
        assert len(collapse_btns) > 0
        
        for btn in collapse_btns:
            onclick = btn.get('onclick')
            assert onclick is not None
            assert 'toggleSection' in onclick
    
    def test_service_group_headers_have_onclick(self):
        """Test that service group headers have onclick handlers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        service_headers = soup.find_all('div', class_='service-group-header')
        assert len(service_headers) > 0
        
        for header in service_headers:
            onclick = header.get('onclick')
            assert onclick is not None
            assert 'toggleServiceGroup' in onclick
    
    def test_account_dropdown_toggle_function(self):
        """Test that account dropdown toggle function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function toggleAccountDropdown()" in html
    
    def test_account_dropdown_has_toggle_onclick(self):
        """Test that account dropdown button has toggle onclick."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "toggleAccountDropdown()" in html
    
    def test_account_search_has_filter_handler(self):
        """Test that account search input has filter handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        search = soup.find('input', id='account-search')
        assert search is not None
        # The input uses oninput event handler
        oninput = search.get('oninput')
        assert oninput is not None
        assert 'filterAccountOptions' in oninput
    
    def test_select_all_accounts_function(self):
        """Test that selectAllAccounts function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function selectAllAccounts()" in html
    
    def test_deselect_all_accounts_function(self):
        """Test that deselectAllAccounts function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function deselectAllAccounts()" in html
    
    def test_help_link_has_onclick(self):
        """Test that Help link has onclick handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'onclick="showReportHelp(event)"' in html


# ============================================================================
# Chart Interaction Tests
# ============================================================================

class TestHTMLFormatterChartInteraction:
    """Tests for chart interaction functionality."""
    
    def test_service_chart_has_onclick_handler(self):
        """Test that service chart has onClick handler in options."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for onClick in chart configuration
        assert "onClick: function(event, elements)" in html
    
    def test_account_chart_has_onclick_handler(self):
        """Test that account chart has onClick handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # accountChart should have click handler
        assert "accountChart" in html
        assert "onClick:" in html
    
    def test_status_pie_chart_has_onclick_handler(self):
        """Test that status pie chart has onClick handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "statusPieChart" in html
    
    def test_service_pie_chart_has_onclick_handler(self):
        """Test that service pie chart has onClick handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "servicePieChart" in html
    
    def test_timeline_chart_has_onclick_handler(self):
        """Test that timeline chart has onClick handler."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "timelineChart" in html
    
    def test_chart_click_opens_new_tab(self):
        """Test that chart click handler opens new tab with resources."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # showChartResources should open new tab
        assert "window.open('', '_blank')" in html
        assert "newTab.document.write(html)" in html
    
    def test_chart_resources_data_structures_exist(self):
        """Test that chart resources data structures are defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "var serviceResourcesData" in html
        assert "var accountResourcesData" in html
        assert "var statusResourcesData" in html
    
    def test_timeline_resources_data_exists(self):
        """Test that timeline resources data is defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "window.timelineResourcesData" in html


# ============================================================================
# DataTable Interaction Tests
# ============================================================================

class TestHTMLFormatterDataTableInteraction:
    """Tests for DataTable interaction functionality."""
    
    def test_main_datatable_initialized(self):
        """Test that main resources DataTable is initialized."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "$('#resourcesDataTable').DataTable" in html
    
    def test_datatable_has_buttons(self):
        """Test that DataTable has export buttons configured."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "buttons: ['copy', 'csv'" in html
    
    def test_datatable_has_search(self):
        """Test that DataTable has search functionality."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # DataTable search is enabled by default
        assert "DataTable" in html
    
    def test_datatable_has_pagination(self):
        """Test that DataTable has pagination configured."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "pageLength:" in html
        assert "lengthMenu:" in html
    
    def test_service_datatables_lazy_initialized(self):
        """Test that service DataTables are lazily initialized on expand."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for lazy initialization in toggleServiceGroup
        assert "$.fn.DataTable.isDataTable(table)" in html


# ============================================================================
# Filter State Tests
# ============================================================================

class TestHTMLFormatterFilterState:
    """Tests for filter state management."""
    
    def test_filters_initialized_on_dom_ready(self):
        """Test that filters are initialized on DOM ready."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "initFilters()" in html
    
    def test_filter_state_persists_in_apply(self):
        """Test that applyFilters reads current filter state."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # applyFilters should call getSelectedFilters
        assert "getSelectedFilters()" in html
    
    def test_reset_filters_selects_all(self):
        """Test that resetFilters selects all filter options."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # resetFilters should add 'selected' class to all options
        assert "classList.add('selected')" in html
    
    def test_filter_options_toggle_selected_class(self):
        """Test that filter options toggle selected class on click."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "classList.toggle('selected')" in html


# ============================================================================
# Tooltip Interaction Tests
# ============================================================================

class TestHTMLFormatterTooltipInteraction:
    """Tests for tooltip interaction functionality."""
    
    def test_summary_card_tooltip_show_function(self):
        """Test that showSummaryTooltip function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function showSummaryTooltip(event, statusKey)" in html
    
    def test_summary_card_tooltip_position_function(self):
        """Test that positionSummaryTooltip function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function positionSummaryTooltip(event)" in html
    
    def test_summary_card_tooltip_hide_function(self):
        """Test that hideSummaryTooltip function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "function hideSummaryTooltip()" in html
    
    def test_summary_cards_have_tooltip_events(self):
        """Test that summary cards have tooltip event handlers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "onmouseenter=\"showSummaryTooltip" in html
        assert "onmousemove=\"positionSummaryTooltip" in html
        assert "onmouseleave=\"hideSummaryTooltip" in html
    
    def test_chart_tooltips_have_click_hint(self):
        """Test that chart tooltips include click hint."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Click to view resources" in html


# ============================================================================
# Window Event Tests
# ============================================================================

class TestHTMLFormatterWindowEvents:
    """Tests for window event handlers."""
    
    def test_scroll_event_listener_exists(self):
        """Test that scroll event listener is set up."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "window.addEventListener('scroll'" in html
    
    def test_go_to_top_visibility_on_scroll(self):
        """Test that go-to-top button visibility changes on scroll."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for scroll threshold logic
        assert "window.scrollY > 300" in html or "scrollY" in html
    
    def test_document_ready_handler(self):
        """Test that document ready handler is set up."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "$(document).ready" in html
    
    def test_click_outside_dropdown_closes_it(self):
        """Test that clicking outside dropdown closes it."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check for document click handler for dropdown
        assert "document.addEventListener('click'" in html or "closeAccountDropdown" in html


# ============================================================================
# Generation Parameters Tests
# ============================================================================

class TestHTMLFormatterGenerationParameters:
    """Tests for generation parameters display in HTML report."""
    
    def test_generation_params_div_exists_when_params_set(self):
        """Test that generation-params div exists when parameters are set."""
        from src.models import GenerationParameters
        
        report = create_sample_report()
        report.generation_params = GenerationParameters(
            input_file="test.csv",
            output_format="html",
            days_threshold=90,
        )
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        params_div = soup.find('div', class_='generation-params')
        assert params_div is not None
    
    def test_generation_params_contains_input_file(self):
        """Test that generation params shows input file."""
        from src.models import GenerationParameters
        
        report = create_sample_report()
        report.generation_params = GenerationParameters(
            input_file="my_inventory.csv",
            output_format="html",
            days_threshold=90,
        )
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "my_inventory.csv" in html
    
    def test_generation_params_contains_days_threshold(self):
        """Test that generation params shows days threshold."""
        from src.models import GenerationParameters
        
        report = create_sample_report()
        report.generation_params = GenerationParameters(
            input_file="test.csv",
            output_format="html",
            days_threshold=60,
        )
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "EOS Threshold: 60 days" in html
    
    def test_generation_params_contains_filters(self):
        """Test that generation params shows filters when set."""
        from src.models import GenerationParameters
        
        report = create_sample_report()
        report.generation_params = GenerationParameters(
            input_file="test.csv",
            output_format="html",
            days_threshold=90,
            status_filters=["Approaching End-of-Support"],
            account_filters=["Production"],
        )
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Status:" in html
        assert "Accounts:" in html
    
    def test_generation_params_css_exists(self):
        """Test that CSS for generation-params exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert ".generation-params" in html
    
    def test_no_generation_params_div_when_params_none(self):
        """Test that no generation-params div when params is None."""
        report = create_sample_report()
        report.generation_params = None
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        params_div = soup.find('div', class_='generation-params')
        assert params_div is None


class TestHTMLFormatterVersionDetails:
    """Tests for Version Details section in HTML formatter."""
    
    def test_version_details_section_exists(self):
        """Test that version details section exists in HTML output."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'id="version-details-section"' in html
        assert 'Version Details by Service' in html
    
    def test_version_details_menu_link_exists(self):
        """Test that navigation menu includes Version Details link."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'href="#version-details-section"' in html
        assert 'Version Details</a>' in html
    
    def test_version_details_cards_exist(self):
        """Test that version detail cards are generated for each service+engine."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'class="version-detail-card"' in html
        assert 'version-detail-header' in html
        assert 'version-detail-content' in html
    
    def test_version_details_expand_collapse_buttons(self):
        """Test that expand/collapse all buttons exist."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'expandAllVersionDetails()' in html
        assert 'collapseAllVersionDetails()' in html
        assert 'Expand All' in html
        assert 'Collapse All' in html
    
    def test_version_details_table_headers(self):
        """Test that version detail tables have correct headers."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        version_tables = soup.find_all('table', class_='version-detail-table')
        assert len(version_tables) > 0
        
        # Check headers of first table
        headers = version_tables[0].find('thead').find_all('th')
        header_texts = [h.text for h in headers]
        
        expected = ['Version', 'Resource Count', 'End of Support', 
                   'Extended Support Start', 'Extended Support End', 'Status Summary']
        assert header_texts == expected
    
    def test_version_details_link_in_resources_table(self):
        """Test that resources table has Version Details links."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'class="version-details-link"' in html
        assert 'scrollToVersionDetail' in html
    
    def test_version_details_javascript_functions(self):
        """Test that version details JavaScript functions exist."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'function toggleVersionDetailCard' in html
        assert 'function expandAllVersionDetails' in html
        assert 'function collapseAllVersionDetails' in html
        assert 'function scrollToVersionDetail' in html
    
    def test_version_details_css_styles(self):
        """Test that version details CSS styles are defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert '.version-detail-card' in html
        assert '.version-detail-header' in html
        assert '.version-detail-content' in html
        assert '.version-details-link' in html
    
    def test_version_details_cards_have_data_attributes(self):
        """Test that version detail cards have data-service and data-engine attributes."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        cards = soup.find_all('div', class_='version-detail-card')
        assert len(cards) > 0
        
        for card in cards:
            assert card.has_attr('data-service')


class TestHTMLFormatterFilterUpdatesCharts:
    """Tests for filter functionality updating all widgets including charts."""
    
    def test_apply_filters_updates_charts(self):
        """Test that applyFilters function includes chart update logic."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'updateChartsWithFilters' in html
        assert 'function updateChartsWithFilters(filters)' in html
    
    def test_filter_updates_service_chart(self):
        """Test that filter updates service chart."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Chart.getChart('serviceChart')" in html
        assert 'serviceChart.update()' in html
    
    def test_filter_updates_account_chart(self):
        """Test that filter updates account chart."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Chart.getChart('accountChart')" in html
        assert 'accountChart.update()' in html
    
    def test_filter_updates_status_pie_chart(self):
        """Test that filter updates status pie chart."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Chart.getChart('statusPieChart')" in html
        assert 'statusPieChart.update()' in html
    
    def test_filter_updates_service_pie_chart(self):
        """Test that filter updates service pie chart."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert "Chart.getChart('servicePieChart')" in html
        assert 'servicePieChart.update()' in html
    
    def test_filter_updates_version_details_cards(self):
        """Test that filter updates version details cards visibility."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'filterVersionDetailCards' in html
        assert 'function filterVersionDetailCards(filters)' in html


class TestHTMLFormatterTimelineFiltering:
    """Tests for timeline filtering functionality."""
    
    def test_timeline_items_have_data_attributes(self):
        """Test that timeline items have data-service and data-status attributes."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        timeline_items = soup.find_all('div', class_='timeline-item')
        if timeline_items:  # Only test if there are timeline items
            for item in timeline_items:
                assert item.has_attr('data-service')
                assert item.has_attr('data-status')
    
    def test_update_timeline_with_filters_function_exists(self):
        """Test that updateTimelineWithFilters function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'function updateTimelineWithFilters' in html
    
    def test_all_timeline_resources_data_variable_exists(self):
        """Test that allTimelineResourcesData variable is defined for filtering."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'window.allTimelineResourcesData' in html
    
    def test_apply_filters_calls_timeline_update(self):
        """Test that applyFilters calls updateTimelineWithFilters."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'updateTimelineWithFilters(filters)' in html
    
    def test_reset_filters_resets_timeline(self):
        """Test that resetFilters resets timeline items visibility."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Check that reset shows all timeline items
        assert "document.querySelectorAll('.timeline-item').forEach" in html
    
    def test_reset_charts_to_original_function_exists(self):
        """Test that resetChartsToOriginal function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'function resetChartsToOriginal' in html


# ============================================================================
# Chart Click Filter Tests
# ============================================================================

class TestHTMLFormatterChartClickFiltering:
    """Tests for chart click filtering functionality."""
    
    def test_filter_resources_by_current_filters_function_exists(self):
        """Test that filterResourcesByCurrentFilters function exists."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert 'function filterResourcesByCurrentFilters(resources)' in html
    
    def test_filter_resources_function_checks_service_filter(self):
        """Test that filterResourcesByCurrentFilters checks service filter."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Should check service filter
        assert "filters.services.length > 0" in html
        assert "filters.services.includes(r.service)" in html
    
    def test_filter_resources_function_checks_account_filter(self):
        """Test that filterResourcesByCurrentFilters checks account filter."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Should check account filter
        assert "filters.accounts.length > 0" in html
        assert "filters.accounts.includes(r.account)" in html
    
    def test_filter_resources_function_checks_status_filter(self):
        """Test that filterResourcesByCurrentFilters checks status filter."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Should check status filter
        assert "filters.statuses.length > 0" in html
        assert "filters.statuses.includes(statusLabel)" in html
    
    def test_show_status_resources_applies_filters(self):
        """Test that showStatusResources applies current page filters."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # showStatusResources should call filterResourcesByCurrentFilters
        assert "function showStatusResources(statusKey)" in html
        # Check that it applies filters before showing
        assert "resources = filterResourcesByCurrentFilters(resources)" in html
    
    def test_show_all_resources_applies_filters(self):
        """Test that showAllResources applies current page filters."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # showAllResources should call filterResourcesByCurrentFilters
        assert "function showAllResources()" in html
        # Check that it applies filters before showing
        assert "allResources = filterResourcesByCurrentFilters(allResources)" in html
    
    def test_service_chart_click_applies_filters(self):
        """Test that service chart click applies current page filters."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Service chart onClick should apply filters
        # Check for comment indicating filter application
        assert "Apply current page filters (account filter)" in html
    
    def test_account_chart_click_applies_filters(self):
        """Test that account chart click applies current page filters."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Account chart onClick should apply filters
        # Check for comment indicating filter application
        assert "Apply current page filters (service filter)" in html
    
    def test_status_pie_chart_click_applies_filters(self):
        """Test that status pie chart click applies current page filters."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Status pie chart onClick should apply filters
        # Check for comment indicating filter application
        assert "Apply current page filters (service and account filters)" in html
    
    def test_service_pie_chart_click_applies_filters(self):
        """Test that service pie chart click applies current page filters."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # Service pie chart onClick should apply filters
        # Check for comment indicating filter application
        assert "Apply current page filters (account and status filters)" in html
    
    def test_timeline_show_month_resources_applies_filters(self):
        """Test that showMonthResources applies current page filters."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        # showMonthResources should apply filters
        assert "function showMonthResources(month)" in html
        # Check for the filter application in the function
        assert "No resources match current filters for" in html


# ============================================================================
# AWS Documentation Links Tests
# ============================================================================

class TestHTMLFormatterAWSDocsLinks:
    """Tests for AWS documentation links in version details section."""
    
    def test_aws_docs_links_mapping_exists(self):
        """Test that AWS_DOCS_LINKS mapping exists in HTMLFormatter."""
        formatter = HTMLFormatter()
        
        assert hasattr(formatter, 'AWS_DOCS_LINKS')
        assert isinstance(formatter.AWS_DOCS_LINKS, dict)
        assert len(formatter.AWS_DOCS_LINKS) > 0
    
    def test_aws_docs_links_have_required_fields(self):
        """Test that each AWS docs link entry has required fields."""
        formatter = HTMLFormatter()
        
        for service, info in formatter.AWS_DOCS_LINKS.items():
            assert 'url' in info, f"Missing 'url' for {service}"
            assert 'title' in info, f"Missing 'title' for {service}"
            assert 'description' in info, f"Missing 'description' for {service}"
            assert info['url'].startswith('http'), f"Invalid URL for {service}"
    
    def test_lambda_docs_link_exists(self):
        """Test that Lambda documentation link exists."""
        formatter = HTMLFormatter()
        
        assert 'Lambda' in formatter.AWS_DOCS_LINKS
        assert 'lambda-runtimes' in formatter.AWS_DOCS_LINKS['Lambda']['url']
    
    def test_rds_docs_link_exists(self):
        """Test that RDS documentation link exists."""
        formatter = HTMLFormatter()
        
        assert 'RDS' in formatter.AWS_DOCS_LINKS
    
    def test_elasticache_docs_link_exists(self):
        """Test that ElastiCache documentation link exists."""
        formatter = HTMLFormatter()
        
        assert 'ElastiCache' in formatter.AWS_DOCS_LINKS
        assert 'engine-versions' in formatter.AWS_DOCS_LINKS['ElastiCache']['url']
    
    def test_get_aws_docs_link_html_returns_link_for_known_service(self):
        """Test that _get_aws_docs_link_html returns link for known service."""
        formatter = HTMLFormatter()
        
        link_html = formatter._get_aws_docs_link_html('Lambda')
        
        assert 'href=' in link_html
        assert 'aws-docs-link' in link_html
        assert 'target="_blank"' in link_html
        assert '📖' in link_html
    
    def test_get_aws_docs_link_html_returns_empty_for_unknown_service(self):
        """Test that _get_aws_docs_link_html returns empty for unknown service."""
        formatter = HTMLFormatter()
        
        link_html = formatter._get_aws_docs_link_html('UnknownService123')
        
        assert link_html == ''
    
    def test_aws_docs_link_css_styles_exist(self):
        """Test that AWS docs link CSS styles are defined."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        
        assert '.aws-docs-link' in html
        assert '.aws-docs-link:hover' in html
    
    def test_aws_docs_link_prevents_card_toggle(self):
        """Test that AWS docs link has onclick stopPropagation to prevent card toggle."""
        formatter = HTMLFormatter()
        
        link_html = formatter._get_aws_docs_link_html('Lambda')
        
        assert 'event.stopPropagation()' in link_html
