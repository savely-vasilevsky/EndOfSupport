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
            status=SupportStatus.EXTENDED_SUPPORT,
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
        """Test that filter bar has account filter options."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        account_filters = soup.find('div', id='account-filters')
        assert account_filters is not None
        
        options = account_filters.find_all('label', class_='filter-option')
        assert len(options) > 0
    
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
        assert len(options) == 4  # Supported, Approaching, Extended, Out of Support
    
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
        """Test that account filter contains all accounts from report."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        account_filters = soup.find('div', id='account-filters')
        options = account_filters.find_all('label', class_='filter-option')
        
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
        extended_card = soup.find('div', class_='summary-card extended')
        out_of_support_card = soup.find('div', class_='summary-card out-of-support')
        
        assert supported_card is not None
        assert approaching_card is not None
        assert extended_card is not None
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
        
        extended_card = soup.find('div', class_='summary-card extended')
        extended_count = extended_card.find('div', class_='count').text
        
        out_card = soup.find('div', class_='summary-card out-of-support')
        out_count = out_card.find('div', class_='count').text
        
        # Verify counts match report
        assert int(supported_count) == report.total_counts.get(SupportStatus.SUPPORTED, 0)
        assert int(approaching_count) == report.total_counts.get(SupportStatus.APPROACHING_EOS, 0)
        assert int(extended_count) == report.total_counts.get(SupportStatus.EXTENDED_SUPPORT, 0)
        assert int(out_count) == report.total_counts.get(SupportStatus.OUT_OF_SUPPORT, 0)


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
        
        expected_headers = ['Account', 'Service', 'Engine', 'Version', 
                          'Resource', 'End of Support', 'Days to EOS', 'Status']
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
            assert len(badges) == 4  # One for each status
    
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
    
    def test_loading_overlay_exists(self):
        """Test that loading overlay exists in HTML."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        loading = soup.find('div', id='loading-overlay')
        assert loading is not None
    
    def test_loading_overlay_has_spinner(self):
        """Test that loading overlay has spinner element."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        loading = soup.find('div', id='loading-overlay')
        spinner = loading.find('div', class_='spinner')
        
        assert spinner is not None
    
    def test_loading_overlay_has_text(self):
        """Test that loading overlay has loading text."""
        report = create_sample_report()
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        loading = soup.find('div', id='loading-overlay')
        assert "Loading report data" in loading.text
    
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
        
        # Should have 3 account filter options
        account_filters = soup.find('div', id='account-filters')
        options = account_filters.find_all('label', class_='filter-option')
        
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
        """Property: All unique accounts appear in filter."""
        report = build_report_from_resources(resources)
        formatter = HTMLFormatter()
        
        html = formatter.format(report)
        soup = BeautifulSoup(html, 'html.parser')
        
        account_filters = soup.find('div', id='account-filters')
        options = account_filters.find_all('label', class_='filter-option')
        filter_accounts = {opt.get('data-value') for opt in options}
        
        resource_accounts = {r.account for r in resources}
        
        assert resource_accounts == filter_accounts
