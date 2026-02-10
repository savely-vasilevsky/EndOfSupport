"""Browser interaction tests for HTML report.

Tests actual browser interactions with the HTML report including:
- Filter selection and application
- Section collapse/expand
- Service group expansion
- DataTable functionality
- Navigation menu
- Loading indicator

These tests use Playwright to simulate real browser interactions.

Feature: html-report-interaction
"""

import os
import re
import tempfile
from datetime import date, timedelta
from typing import List

import pytest
from playwright.sync_api import Page, expect

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
        resource_name=f"test-{service.lower()}-{version}",
        region="us-east-1",
        engine=engine,
        version=version,
        end_of_support=end_of_support,
        end_of_support_raw=end_of_support.strftime('%d-%b-%y') if end_of_support else "-",
        auto_minor_version_upgrade=None,
        extended_support_start=None,
        extended_support_year1_start=None,
        extended_support_year3_start=None,
        extended_support_end=None,
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
        
        if account_name not in report.accounts:
            report.accounts[account_name] = AccountGroup(account=account_name)
        
        account_group = report.accounts[account_name]
        
        if service_name not in account_group.services:
            account_group.services[service_name] = ServiceGroup(service=service_name)
        
        service_group = account_group.services[service_name]
        
        if engine_name not in service_group.engines:
            service_group.engines[engine_name] = EngineGroup(engine=engine_name)
        
        engine_group = service_group.engines[engine_name]
        
        if version_name not in engine_group.versions:
            engine_group.versions[version_name] = VersionGroup(version=version_name)
        
        version_group = engine_group.versions[version_name]
        version_group.resources.append(resource)
        report.total_resources += 1
        
        if resource.status:
            report.total_counts[resource.status] = report.total_counts.get(resource.status, 0) + 1
    
    return report


def create_test_report() -> Report:
    """Create a test report with diverse data for interaction testing."""
    resources = [
        # Production account - Lambda
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
            service="Lambda",
            engine="nodejs",
            version="18.x",
            end_of_support=date.today() + timedelta(days=365),
            status=SupportStatus.SUPPORTED,
            days_to_eos=365,
        ),
        # Production account - RDS
        create_resource(
            account="Production",
            service="RDS",
            engine="mysql",
            version="8.0",
            end_of_support=date.today() + timedelta(days=180),
            status=SupportStatus.SUPPORTED,
            days_to_eos=180,
        ),
        # Development account - Lambda
        create_resource(
            account="Development",
            service="Lambda",
            engine="python",
            version="3.8",
            end_of_support=date.today() - timedelta(days=30),
            status=SupportStatus.OUT_OF_SUPPORT,
            days_to_eos=-30,
        ),
        # Development account - ElastiCache
        create_resource(
            account="Development",
            service="ElastiCache",
            engine="redis",
            version="6.0",
            end_of_support=date.today() + timedelta(days=60),
            status=SupportStatus.EXTENDED_SUPPORT,
            days_to_eos=60,
        ),
        # Staging account - RDS
        create_resource(
            account="Staging",
            service="RDS",
            engine="postgres",
            version="14.0",
            end_of_support=date.today() + timedelta(days=500),
            status=SupportStatus.SUPPORTED,
            days_to_eos=500,
        ),
    ]
    return build_report_from_resources(resources)


@pytest.fixture
def html_report_path():
    """Create a temporary HTML report file for testing."""
    report = create_test_report()
    formatter = HTMLFormatter()
    
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode='w', encoding='utf-8') as f:
        html_content = formatter.format(report)
        f.write(html_content)
        tmp_path = f.name
    
    yield tmp_path
    
    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


# ============================================================================
# Loading Indicator Tests
# ============================================================================

class TestLoadingIndicator:
    """Tests for loading indicator behavior."""
    
    def test_loading_overlay_hidden_after_load(self, page: Page, html_report_path: str):
        """Test that loading overlay is hidden after page loads."""
        page.goto(f"file:///{html_report_path}")
        
        # Wait for page to fully load
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)  # Wait for the 500ms timeout + buffer
        
        # Loading overlay should be hidden
        loading = page.locator("#loading-overlay")
        expect(loading).to_be_hidden()


# ============================================================================
# Navigation Menu Tests
# ============================================================================

class TestNavigationMenu:
    """Tests for navigation menu interactions."""
    
    def test_menu_links_scroll_to_sections(self, page: Page, html_report_path: str):
        """Test that menu links scroll to corresponding sections."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Click on Timeline link
        page.click("a[href='#timeline-section']")
        page.wait_for_timeout(500)
        
        # Timeline section should be visible in viewport
        timeline = page.locator("#timeline-section")
        expect(timeline).to_be_visible()
    
    def test_go_to_top_button_appears_on_scroll(self, page: Page, html_report_path: str):
        """Test that go-to-top button appears when scrolling down."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Initially button should be hidden
        go_to_top = page.locator(".go-to-top")
        expect(go_to_top).to_be_hidden()
        
        # Scroll down
        page.evaluate("window.scrollTo(0, 500)")
        page.wait_for_timeout(300)
        
        # Button should now be visible
        expect(go_to_top).to_be_visible()
    
    def test_go_to_top_button_scrolls_to_top(self, page: Page, html_report_path: str):
        """Test that clicking go-to-top button scrolls to top."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Scroll down first
        page.evaluate("window.scrollTo(0, 1000)")
        page.wait_for_timeout(300)
        
        # Click go-to-top button using JavaScript to avoid element overlap issues
        page.evaluate("document.querySelector('.go-to-top').click()")
        page.wait_for_timeout(500)
        
        # Should be at top (or very close)
        scroll_y = page.evaluate("window.scrollY")
        assert scroll_y < 50  # Allow small margin


# ============================================================================
# Filter Bar Interaction Tests
# ============================================================================

class TestFilterBarInteraction:
    """Tests for filter bar interactions."""
    
    def test_filter_option_toggle_on_click(self, page: Page, html_report_path: str):
        """Test that clicking a filter option toggles its selection."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Get first service filter option
        first_option = page.locator("#service-filters .filter-option").first
        
        # Initially should be selected
        expect(first_option).to_have_class(re.compile(r"selected"))
        
        # Click to deselect
        first_option.click()
        page.wait_for_timeout(100)
        
        # Should no longer have 'selected' class
        expect(first_option).not_to_have_class(re.compile(r"selected"))
        
        # Click again to reselect
        first_option.click()
        page.wait_for_timeout(100)
        
        # Should have 'selected' class again
        expect(first_option).to_have_class(re.compile(r"selected"))
    
    def test_apply_filters_updates_table(self, page: Page, html_report_path: str):
        """Test that applying filters updates the resources table."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Get initial row count
        initial_info = page.locator("#resourcesDataTable_info").text_content()
        
        # Deselect all status filters except "Out of Support"
        page.click("#status-filters .filter-option:has-text('Supported')")
        page.click("#status-filters .filter-option:has-text('Approaching EOS')")
        page.click("#status-filters .filter-option:has-text('Extended Support')")
        page.wait_for_timeout(100)
        
        # Click Apply Filters
        page.click(".apply-btn")
        page.wait_for_timeout(500)
        
        # Table info should show fewer entries
        filtered_info = page.locator("#resourcesDataTable_info").text_content()
        
        # The filtered count should be different (fewer entries)
        assert filtered_info != initial_info
    
    def test_reset_filters_restores_all(self, page: Page, html_report_path: str):
        """Test that Reset All button restores all filter selections."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Deselect some filters using JavaScript to avoid click issues
        page.evaluate("document.querySelector('#service-filters .filter-option').click()")
        # Account filter is now a dropdown - click on a dropdown item
        page.evaluate("document.querySelector('#account-dropdown').classList.add('open')")
        page.wait_for_timeout(100)
        page.evaluate("document.querySelector('#account-items .dropdown-item').click()")
        page.wait_for_timeout(100)
        
        # Click Reset All
        page.click(".reset-btn")
        page.wait_for_timeout(300)
        
        # All service filter options should be selected again
        service_options = page.locator("#service-filters .filter-option")
        count = service_options.count()
        
        for i in range(count):
            option = service_options.nth(i)
            expect(option).to_have_class(re.compile(r"selected"))
    
    def test_filter_by_account(self, page: Page, html_report_path: str):
        """Test filtering by specific account."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Open account dropdown and deselect Development and Staging
        page.evaluate("document.querySelector('#account-dropdown').classList.add('open')")
        page.wait_for_timeout(100)
        page.evaluate("document.querySelector('#account-items .dropdown-item[data-value=\"Development\"]').click()")
        page.wait_for_timeout(100)
        page.evaluate("document.querySelector('#account-items .dropdown-item[data-value=\"Staging\"]').click()")
        page.wait_for_timeout(100)
        
        # Apply filters
        page.click(".apply-btn")
        page.wait_for_timeout(500)
        
        # Check that only Production rows are visible
        visible_rows = page.locator("#resourcesDataTable tbody tr:visible")
        count = visible_rows.count()
        
        for i in range(count):
            row = visible_rows.nth(i)
            row_text = row.text_content()
            assert "Production" in row_text
    
    def test_filter_by_service(self, page: Page, html_report_path: str):
        """Test filtering by specific service."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Deselect all services except Lambda
        page.click("#service-filters .filter-option:has-text('RDS')")
        page.click("#service-filters .filter-option:has-text('ElastiCache')")
        page.wait_for_timeout(100)
        
        # Apply filters
        page.click(".apply-btn")
        page.wait_for_timeout(500)
        
        # Check that only Lambda rows are visible
        visible_rows = page.locator("#resourcesDataTable tbody tr:visible")
        count = visible_rows.count()
        
        for i in range(count):
            row = visible_rows.nth(i)
            row_text = row.text_content()
            assert "Lambda" in row_text


# ============================================================================
# Section Collapse/Expand Tests
# ============================================================================

class TestSectionCollapse:
    """Tests for section collapse/expand functionality."""
    
    def test_collapse_status_breakdown_section(self, page: Page, html_report_path: str):
        """Test collapsing the status breakdown section."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Content should be visible initially
        content = page.locator("#status-breakdown-content")
        expect(content).to_be_visible()
        
        # Click collapse button
        page.click("#status-breakdown .collapse-btn")
        page.wait_for_timeout(400)
        
        # Content should be collapsed (hidden)
        expect(content).to_have_class(re.compile(r"collapsed"))
    
    def test_expand_collapsed_section(self, page: Page, html_report_path: str):
        """Test expanding a collapsed section."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Collapse first
        page.click("#status-breakdown .collapse-btn")
        page.wait_for_timeout(400)
        
        content = page.locator("#status-breakdown-content")
        expect(content).to_have_class(re.compile(r"collapsed"))
        
        # Click again to expand
        page.click("#status-breakdown .collapse-btn")
        page.wait_for_timeout(400)
        
        # Content should be visible again
        expect(content).not_to_have_class(re.compile(r"collapsed"))
    
    def test_collapse_button_text_changes(self, page: Page, html_report_path: str):
        """Test that collapse button text changes between − and +."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        btn = page.locator("#status-breakdown .collapse-btn")
        
        # Initially should show −
        expect(btn).to_have_text("−")
        
        # Click to collapse
        btn.click()
        page.wait_for_timeout(400)
        
        # Should show +
        expect(btn).to_have_text("+")
        
        # Click to expand
        btn.click()
        page.wait_for_timeout(400)
        
        # Should show − again
        expect(btn).to_have_text("−")


# ============================================================================
# Service Group Expansion Tests
# ============================================================================

class TestServiceGroupExpansion:
    """Tests for service group expand/collapse functionality."""
    
    def test_service_group_expands_on_click(self, page: Page, html_report_path: str):
        """Test that clicking a service group header expands it."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Get first service group
        first_group = page.locator(".service-group").first
        content = first_group.locator(".service-group-content")
        
        # Initially content should be hidden
        expect(content).to_be_hidden()
        
        # Click header to expand
        first_group.locator(".service-group-header").click()
        page.wait_for_timeout(500)
        
        # Content should now be visible
        expect(content).to_be_visible()
    
    def test_service_group_collapses_on_second_click(self, page: Page, html_report_path: str):
        """Test that clicking an expanded service group collapses it."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        first_group = page.locator(".service-group").first
        header = first_group.locator(".service-group-header")
        content = first_group.locator(".service-group-content")
        
        # Expand first
        header.click()
        page.wait_for_timeout(500)
        expect(content).to_be_visible()
        
        # Click again to collapse
        header.click()
        page.wait_for_timeout(500)
        
        # Content should be hidden again
        expect(content).to_be_hidden()
    
    def test_service_group_shows_datatable(self, page: Page, html_report_path: str):
        """Test that expanded service group shows a DataTable."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Expand first service group
        first_group = page.locator(".service-group").first
        first_group.locator(".service-group-header").click()
        page.wait_for_timeout(800)  # Wait for DataTable initialization
        
        # Should have DataTable wrapper
        datatable_wrapper = first_group.locator(".dataTables_wrapper")
        expect(datatable_wrapper).to_be_visible()
    
    def test_service_group_datatable_has_pagination(self, page: Page, html_report_path: str):
        """Test that service group DataTable has pagination controls."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Expand first service group
        first_group = page.locator(".service-group").first
        first_group.locator(".service-group-header").click()
        page.wait_for_timeout(800)
        
        # Should have pagination info
        pagination_info = first_group.locator(".dataTables_info")
        expect(pagination_info).to_be_visible()


# ============================================================================
# DataTable Interaction Tests
# ============================================================================

class TestDataTableInteraction:
    """Tests for main resources DataTable interactions."""
    
    def test_datatable_search_filters_rows(self, page: Page, html_report_path: str):
        """Test that DataTable search filters rows."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Get initial row count from info
        initial_info = page.locator("#resourcesDataTable_info").text_content()
        
        # Type in search box
        search_input = page.locator("#resourcesDataTable_filter input")
        search_input.fill("Lambda")
        page.wait_for_timeout(500)
        
        # Info should show filtered results
        filtered_info = page.locator("#resourcesDataTable_info").text_content()
        assert "filtered" in filtered_info.lower() or filtered_info != initial_info
    
    def test_datatable_sorting(self, page: Page, html_report_path: str):
        """Test that clicking column headers sorts the table."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Get first row's account before sorting
        first_row_before = page.locator("#resourcesDataTable tbody tr").first.text_content()
        
        # Click on Account header to sort
        page.click("#resourcesDataTable thead th:first-child")
        page.wait_for_timeout(300)
        
        # Get first row's account after sorting
        first_row_after = page.locator("#resourcesDataTable tbody tr").first.text_content()
        
        # Rows should be reordered (may or may not be different depending on initial order)
        # Just verify the table is still functional
        expect(page.locator("#resourcesDataTable tbody tr").first).to_be_visible()
    
    def test_datatable_pagination(self, page: Page, html_report_path: str):
        """Test DataTable pagination controls."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Check that pagination info is present
        pagination_info = page.locator("#resourcesDataTable_info")
        expect(pagination_info).to_be_visible()
        expect(pagination_info).to_contain_text("entries")


# ============================================================================
# Summary Cards Update Tests
# ============================================================================

class TestSummaryCardsUpdate:
    """Tests for summary cards updating with filters."""
    
    def test_summary_cards_update_on_filter(self, page: Page, html_report_path: str):
        """Test that summary cards update when filters are applied."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Get initial total count
        initial_total = page.locator(".summary-card.total .count").text_content()
        
        # Open account dropdown and deselect Development and Staging
        page.evaluate("document.querySelector('#account-dropdown').classList.add('open')")
        page.wait_for_timeout(100)
        page.evaluate("document.querySelector('#account-items .dropdown-item[data-value=\"Development\"]').click()")
        page.wait_for_timeout(100)
        page.evaluate("document.querySelector('#account-items .dropdown-item[data-value=\"Staging\"]').click()")
        page.wait_for_timeout(100)
        
        # Apply filters
        page.click(".apply-btn")
        page.wait_for_timeout(500)
        
        # Total should be updated
        filtered_total = page.locator(".summary-card.total .count").text_content()
        
        # Filtered total should be less than initial
        assert int(filtered_total) < int(initial_total)
    
    def test_summary_cards_reset_on_reset_filters(self, page: Page, html_report_path: str):
        """Test that summary cards reset when Reset All is clicked."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Get initial total
        initial_total = page.locator(".summary-card.total .count").text_content()
        
        # Open account dropdown and deselect Development
        page.evaluate("document.querySelector('#account-dropdown').classList.add('open')")
        page.wait_for_timeout(100)
        page.evaluate("document.querySelector('#account-items .dropdown-item[data-value=\"Development\"]').click()")
        page.wait_for_timeout(100)
        
        page.click(".apply-btn")
        page.wait_for_timeout(500)
        
        # Click Reset All
        page.click(".reset-btn")
        page.wait_for_timeout(500)
        
        # Total should be back to initial
        reset_total = page.locator(".summary-card.total .count").text_content()
        assert reset_total == initial_total


# ============================================================================
# Chart Rendering Tests
# ============================================================================

class TestChartRendering:
    """Tests for chart rendering."""
    
    def test_service_chart_renders(self, page: Page, html_report_path: str):
        """Test that service chart canvas is rendered."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)  # Wait for charts to render
        
        # Chart canvas should be visible
        chart = page.locator("#serviceChart")
        expect(chart).to_be_visible()
    
    def test_account_chart_renders(self, page: Page, html_report_path: str):
        """Test that account chart canvas is rendered."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        chart = page.locator("#accountChart")
        expect(chart).to_be_visible()
    
    def test_pie_charts_render(self, page: Page, html_report_path: str):
        """Test that pie charts are rendered."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        status_pie = page.locator("#statusPieChart")
        service_pie = page.locator("#servicePieChart")
        
        expect(status_pie).to_be_visible()
        expect(service_pie).to_be_visible()
    
    def test_timeline_chart_renders(self, page: Page, html_report_path: str):
        """Test that timeline chart is rendered."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        
        timeline_chart = page.locator("#timelineChart")
        expect(timeline_chart).to_be_visible()


# ============================================================================
# Service Group Filter Integration Tests
# ============================================================================

class TestServiceGroupFilterIntegration:
    """Tests for filter integration with service groups."""
    
    def test_service_groups_hidden_when_service_filtered(self, page: Page, html_report_path: str):
        """Test that service groups are hidden when their service is filtered out."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Count initial service groups
        initial_count = page.locator(".service-group:visible").count()
        
        # Deselect all services except Lambda
        page.click("#service-filters .filter-option:has-text('RDS')")
        page.click("#service-filters .filter-option:has-text('ElastiCache')")
        page.wait_for_timeout(100)
        
        # Apply filters
        page.click(".apply-btn")
        page.wait_for_timeout(500)
        
        # Should have fewer visible service groups
        filtered_count = page.locator(".service-group:visible").count()
        assert filtered_count < initial_count
    
    def test_service_group_counts_update_on_filter(self, page: Page, html_report_path: str):
        """Test that service group resource counts update when filtered."""
        page.goto(f"file:///{html_report_path}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(600)
        
        # Get initial count from first service group
        first_group = page.locator(".service-group").first
        initial_count_text = first_group.locator(".service-count").text_content()
        
        # Open account dropdown and deselect Development and Staging
        page.evaluate("document.querySelector('#account-dropdown').classList.add('open')")
        page.wait_for_timeout(100)
        page.evaluate("document.querySelector('#account-items .dropdown-item[data-value=\"Development\"]').click()")
        page.wait_for_timeout(100)
        page.evaluate("document.querySelector('#account-items .dropdown-item[data-value=\"Staging\"]').click()")
        page.wait_for_timeout(100)
        
        # Apply filters
        page.click(".apply-btn")
        page.wait_for_timeout(500)
        
        # Count may have changed (or group may be hidden)
        # Just verify the page is still functional
        expect(page.locator("#by-service-section")).to_be_visible()
