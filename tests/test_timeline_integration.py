"""Property-based tests for ExcelFormatter timeline integration.

This module contains property-based tests that verify the integration of
TimelineGenerator with ExcelFormatter. These tests validate that the
timeline sheet is correctly created, positioned, and integrated with
the Table of Contents.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**
"""

import os
import tempfile
from datetime import date, timedelta
from typing import List

import pytest
from hypothesis import given, settings, strategies as st
from openpyxl import load_workbook

from src.formatters import ExcelFormatter
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
        status=SupportStatus.SUPPORTED,
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
    
    return report


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def valid_date_strategy(draw):
    """Generate valid dates within a reasonable range for testing."""
    # Generate dates between today - 365 days and today + 730 days
    today = date.today()
    start_date = today - timedelta(days=365)
    end_date = today + timedelta(days=730)
    days_range = (end_date - start_date).days
    offset = draw(st.integers(min_value=0, max_value=days_range))
    return start_date + timedelta(days=offset)


@st.composite
def resource_strategy(draw):
    """Generate random Resource objects for property testing."""
    engine = draw(st.sampled_from(["python", "redis", "mysql", "postgres", None, "Unknown", ""]))
    version = draw(st.from_regex(r"[0-9]+\.[0-9]+", fullmatch=True))
    
    # Generate optional dates
    eos = draw(st.one_of(st.none(), valid_date_strategy()))
    ext_start = draw(st.one_of(st.none(), valid_date_strategy()))
    ext_end = draw(st.one_of(st.none(), valid_date_strategy()))
    
    return create_resource(
        account=draw(st.sampled_from(["account-1", "account-2", "account-3"])),
        service=draw(st.sampled_from(["Lambda", "RDS", "ElastiCache"])),
        engine=engine if engine else "python",  # Ensure non-None for simplicity
        version=version,
        end_of_support=eos,
        extended_support_start=ext_start,
        extended_support_end=ext_end,
    )


@st.composite
def report_with_resources_strategy(draw, min_resources=1, max_resources=10):
    """Generate random Report objects with at least one resource.
    
    This strategy ensures the report has at least min_resources resources,
    which is required for testing timeline sheet creation.
    """
    num_resources = draw(st.integers(min_value=min_resources, max_value=max_resources))
    resources = [draw(resource_strategy()) for _ in range(num_resources)]
    return build_report_from_resources(resources)


@st.composite
def report_strategy(draw, min_resources=0, max_resources=10):
    """Generate random Report objects (may be empty).
    
    This strategy can generate empty reports, which is useful for testing
    timeline sheet omission behavior.
    """
    num_resources = draw(st.integers(min_value=min_resources, max_value=max_resources))
    if num_resources == 0:
        return Report()
    resources = [draw(resource_strategy()) for _ in range(num_resources)]
    return build_report_from_resources(resources)


# ============================================================================
# Property Tests
# ============================================================================

class TestTimelineSheetCreation:
    """Property tests for Timeline sheet creation.
    
    **Property 1: Timeline Sheet Creation**
    *For any* Report object with at least one resource, when `format_to_file` 
    is called with `include_timeline=True`, the resulting Excel file SHALL 
    contain a worksheet named "Timeline".
    
    **Validates: Requirements 1.1**
    """
    
    @given(report=report_with_resources_strategy(min_resources=1, max_resources=5))
    @settings(max_examples=50, deadline=None)
    def test_timeline_sheet_created_when_include_timeline_true(self, report):
        """Property 1: Timeline sheet is created when include_timeline=True.
        
        **Validates: Requirements 1.1**
        
        For any Report object with at least one resource, when format_to_file
        is called with include_timeline=True, the resulting Excel file SHALL
        contain a worksheet named "Timeline".
        """
        formatter = ExcelFormatter()
        
        # Create a temporary file for the Excel output
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Generate Excel file with timeline enabled
            formatter.format_to_file(
                report=report,
                filepath=tmp_path,
                include_pivot=False,  # Disable pivot to simplify test
                include_timeline=True,
            )
            
            # Open the generated Excel file and verify Timeline sheet exists
            wb = load_workbook(tmp_path)
            sheet_names = wb.sheetnames
            wb.close()
            
            # Assert that "Timeline" sheet exists
            assert "Timeline" in sheet_names, (
                f"Timeline sheet not found in workbook. "
                f"Found sheets: {sheet_names}"
            )
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestTimelineSheetOmission:
    """Property tests for Timeline sheet omission.
    
    **Property 2: Timeline Sheet Omission**
    *For any* Report object, when `format_to_file` is called with 
    `include_timeline=False`, the resulting Excel file SHALL NOT contain 
    a worksheet named "Timeline".
    
    **Validates: Requirements 1.3**
    """
    
    @given(report=report_strategy(min_resources=0, max_resources=5))
    @settings(max_examples=50, deadline=None)
    def test_timeline_sheet_omitted_when_include_timeline_false(self, report):
        """Property 2: Timeline sheet is omitted when include_timeline=False.
        
        **Validates: Requirements 1.3**
        
        For any Report object, when format_to_file is called with 
        include_timeline=False, the resulting Excel file SHALL NOT contain 
        a worksheet named "Timeline".
        """
        formatter = ExcelFormatter()
        
        # Create a temporary file for the Excel output
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Generate Excel file with timeline disabled
            formatter.format_to_file(
                report=report,
                filepath=tmp_path,
                include_pivot=False,  # Disable pivot to simplify test
                include_timeline=False,
            )
            
            # Open the generated Excel file and verify Timeline sheet does NOT exist
            wb = load_workbook(tmp_path)
            sheet_names = wb.sheetnames
            wb.close()
            
            # Assert that "Timeline" sheet does NOT exist
            assert "Timeline" not in sheet_names, (
                f"Timeline sheet should not exist when include_timeline=False. "
                f"Found sheets: {sheet_names}"
            )
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestTableOfContentsIntegration:
    """Property tests for Table of Contents integration.
    
    **Property 3: Table of Contents Integration**
    *For any* Excel file generated with `include_timeline=True`, the 
    "Table of Contents" sheet SHALL contain a hyperlink entry for the 
    "Timeline" sheet.
    
    **Validates: Requirements 1.2**
    """
    
    @given(report=report_with_resources_strategy(min_resources=1, max_resources=5))
    @settings(max_examples=50, deadline=None)
    def test_toc_contains_timeline_hyperlink(self, report):
        """Property 3: Table of Contents contains Timeline hyperlink.
        
        **Validates: Requirements 1.2**
        
        For any Excel file generated with include_timeline=True, the 
        "Table of Contents" sheet SHALL contain a hyperlink entry for 
        the "Timeline" sheet.
        """
        formatter = ExcelFormatter()
        
        # Create a temporary file for the Excel output
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Generate Excel file with timeline enabled
            formatter.format_to_file(
                report=report,
                filepath=tmp_path,
                include_pivot=False,  # Disable pivot to simplify test
                include_timeline=True,
            )
            
            # Open the generated Excel file
            wb = load_workbook(tmp_path)
            
            # Verify Table of Contents sheet exists
            assert "Table of Contents" in wb.sheetnames, (
                "Table of Contents sheet not found"
            )
            
            toc_sheet = wb["Table of Contents"]
            
            # Search for Timeline entry in the Table of Contents
            # The TOC typically has sheet names in column A or B with hyperlinks
            timeline_found = False
            timeline_hyperlink_found = False
            
            for row in toc_sheet.iter_rows(min_row=1, max_row=toc_sheet.max_row):
                for cell in row:
                    # Check if cell contains "Timeline" text
                    if cell.value and "Timeline" in str(cell.value):
                        timeline_found = True
                        # Check if cell has a hyperlink
                        if cell.hyperlink is not None:
                            timeline_hyperlink_found = True
                            break
                if timeline_hyperlink_found:
                    break
            
            wb.close()
            
            # Assert that Timeline entry exists in TOC
            assert timeline_found, (
                "Timeline entry not found in Table of Contents"
            )
            
            # Assert that Timeline has a hyperlink
            assert timeline_hyperlink_found, (
                "Timeline entry in Table of Contents does not have a hyperlink"
            )
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestSheetPositioning:
    """Property tests for sheet positioning.
    
    **Property 4: Sheet Positioning**
    *For any* Excel file generated with both pivot and timeline enabled, 
    the "Timeline" sheet index SHALL be greater than the "Pivot" sheet index.
    
    **Validates: Requirements 1.4**
    """
    
    @given(report=report_with_resources_strategy(min_resources=1, max_resources=5))
    @settings(max_examples=50, deadline=None)
    def test_timeline_sheet_after_pivot_sheet(self, report):
        """Property 4: Timeline sheet is positioned after Pivot sheet.
        
        **Validates: Requirements 1.4**
        
        For any Excel file generated with both pivot and timeline enabled, 
        the "Timeline" sheet index SHALL be greater than the "Pivot" sheet index.
        """
        formatter = ExcelFormatter()
        
        # Create a temporary file for the Excel output
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Generate Excel file with both pivot and timeline enabled
            formatter.format_to_file(
                report=report,
                filepath=tmp_path,
                include_pivot=True,
                pivot_method="cross-platform",  # Use cross-platform to ensure Pivot is created
                include_timeline=True,
            )
            
            # Open the generated Excel file
            wb = load_workbook(tmp_path)
            sheet_names = wb.sheetnames
            wb.close()
            
            # Verify both Pivot and Timeline sheets exist
            assert "Pivot" in sheet_names, (
                f"Pivot sheet not found. Found sheets: {sheet_names}"
            )
            assert "Timeline" in sheet_names, (
                f"Timeline sheet not found. Found sheets: {sheet_names}"
            )
            
            # Get indices of Pivot and Timeline sheets
            pivot_index = sheet_names.index("Pivot")
            timeline_index = sheet_names.index("Timeline")
            
            # Assert that Timeline comes after Pivot
            assert timeline_index > pivot_index, (
                f"Timeline sheet (index {timeline_index}) should be positioned "
                f"after Pivot sheet (index {pivot_index}). "
                f"Sheet order: {sheet_names}"
            )
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# ============================================================================
# Additional Unit Tests for Edge Cases
# ============================================================================

class TestTimelineIntegrationEdgeCases:
    """Unit tests for edge cases in timeline integration."""
    
    def test_empty_report_with_timeline_enabled(self):
        """Test that empty report with timeline enabled creates Timeline sheet."""
        report = Report()
        formatter = ExcelFormatter()
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            formatter.format_to_file(
                report=report,
                filepath=tmp_path,
                include_pivot=False,
                include_timeline=True,
            )
            
            wb = load_workbook(tmp_path)
            sheet_names = wb.sheetnames
            wb.close()
            
            # Timeline sheet should still be created even for empty report
            assert "Timeline" in sheet_names
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_single_resource_report(self):
        """Test timeline creation with a single resource."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        formatter = ExcelFormatter()
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            formatter.format_to_file(
                report=report,
                filepath=tmp_path,
                include_pivot=False,
                include_timeline=True,
            )
            
            wb = load_workbook(tmp_path)
            sheet_names = wb.sheetnames
            
            # Verify Timeline sheet exists
            assert "Timeline" in sheet_names
            
            # Verify Timeline sheet has content
            timeline_ws = wb["Timeline"]
            assert timeline_ws.max_row > 1, "Timeline sheet should have content"
            
            wb.close()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_default_include_timeline_is_true(self):
        """Test that include_timeline defaults to True."""
        resource = create_resource()
        report = build_report_from_resources([resource])
        formatter = ExcelFormatter()
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Call format_to_file without specifying include_timeline
            formatter.format_to_file(
                report=report,
                filepath=tmp_path,
                include_pivot=False,
            )
            
            wb = load_workbook(tmp_path)
            sheet_names = wb.sheetnames
            wb.close()
            
            # Timeline should be included by default
            assert "Timeline" in sheet_names, (
                "Timeline should be included by default"
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_sheet_order_with_all_sheets(self):
        """Test complete sheet order with all sheets enabled."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        formatter = ExcelFormatter()
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            formatter.format_to_file(
                report=report,
                filepath=tmp_path,
                include_pivot=True,
                pivot_method="cross-platform",
                include_timeline=True,
            )
            
            wb = load_workbook(tmp_path)
            sheet_names = wb.sheetnames
            wb.close()
            
            # Verify expected sheet order:
            # 1. Table of Contents
            # 2. Support Status Report
            # 3. Pivot
            # 4. Timeline
            assert sheet_names[0] == "Table of Contents", (
                f"First sheet should be 'Table of Contents', got '{sheet_names[0]}'"
            )
            assert sheet_names[1] == "Support Status Report", (
                f"Second sheet should be 'Support Status Report', got '{sheet_names[1]}'"
            )
            
            # Pivot should come before Timeline
            pivot_idx = sheet_names.index("Pivot")
            timeline_idx = sheet_names.index("Timeline")
            assert pivot_idx < timeline_idx, (
                f"Pivot (index {pivot_idx}) should come before Timeline (index {timeline_idx})"
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
