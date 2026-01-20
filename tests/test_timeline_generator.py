"""Unit tests for TimelineGenerator class."""

from datetime import date

import pytest

from src.formatters import TimelineGenerator, EngineVersionData
from src.models import (
    Report,
    Resource,
    SupportStatus,
    AccountGroup,
    ServiceGroup,
    EngineGroup,
    VersionGroup,
)


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
        extended_support_year3_start=None,
        extended_support_end=extended_support_end,
        insights="Test resource",
    )


def build_report_from_resources(resources: list) -> Report:
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


class TestCollectEngineVersions:
    """Tests for TimelineGenerator._collect_engine_versions method.
    
    Validates Requirements 2.1 and 2.4:
    - 2.1: Display one row for each unique engine-version combination
    - 2.4: Sort alphabetically by engine, then by version
    """
    
    def test_single_resource(self):
        """Test collecting a single resource."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date(2025, 10, 1),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 1
        assert result[0].engine == "python"
        assert result[0].version == "3.9"
        assert result[0].end_of_support == date(2025, 10, 1)
        assert result[0].resource_count == 1
    
    def test_multiple_unique_engine_versions(self):
        """Test collecting multiple unique engine-version combinations."""
        resources = [
            create_resource(engine="python", version="3.9"),
            create_resource(engine="python", version="3.10"),
            create_resource(engine="redis", version="6.0"),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 3
    
    def test_aggregates_duplicate_engine_versions(self):
        """Test that duplicate engine-version combinations are aggregated."""
        resources = [
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=date(2025, 10, 1),
            ),
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=date(2025, 12, 1),
            ),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 1
        assert result[0].engine == "python"
        assert result[0].version == "3.9"
        assert result[0].resource_count == 2
    
    def test_uses_earliest_eos(self):
        """Test that earliest EOS date is used when aggregating."""
        resources = [
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=date(2025, 12, 1),
            ),
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=date(2025, 10, 1),  # Earlier
            ),
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=date(2026, 1, 1),
            ),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 1
        assert result[0].end_of_support == date(2025, 10, 1)  # Earliest
    
    def test_uses_earliest_ext_start(self):
        """Test that earliest extended support start date is used when aggregating."""
        resources = [
            create_resource(
                engine="redis",
                version="6.0",
                extended_support_start=date(2025, 6, 15),
            ),
            create_resource(
                engine="redis",
                version="6.0",
                extended_support_start=date(2025, 3, 1),  # Earlier
            ),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 1
        assert result[0].extended_support_start == date(2025, 3, 1)  # Earliest
    
    def test_uses_latest_ext_end(self):
        """Test that latest extended support end date is used when aggregating."""
        resources = [
            create_resource(
                engine="mysql",
                version="8.0",
                extended_support_end=date(2026, 6, 15),
            ),
            create_resource(
                engine="mysql",
                version="8.0",
                extended_support_end=date(2027, 1, 1),  # Later
            ),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 1
        assert result[0].extended_support_end == date(2027, 1, 1)  # Latest
    
    def test_sorted_alphabetically_by_engine_then_version(self):
        """Test that results are sorted alphabetically by engine, then version."""
        resources = [
            create_resource(engine="redis", version="7.0"),
            create_resource(engine="python", version="3.10"),
            create_resource(engine="python", version="3.9"),
            create_resource(engine="mysql", version="8.0"),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 4
        assert result[0].engine == "mysql"
        assert result[0].version == "8.0"
        assert result[1].engine == "python"
        assert result[1].version == "3.10"
        assert result[2].engine == "python"
        assert result[2].version == "3.9"
        assert result[3].engine == "redis"
        assert result[3].version == "7.0"
    
    def test_case_insensitive_sorting(self):
        """Test that sorting is case-insensitive."""
        resources = [
            create_resource(engine="Redis", version="6.0"),
            create_resource(engine="python", version="3.9"),
            create_resource(engine="MySQL", version="8.0"),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 3
        # Should be sorted: MySQL, python, Redis (case-insensitive)
        assert result[0].engine == "MySQL"
        assert result[1].engine == "python"
        assert result[2].engine == "Redis"
    
    def test_empty_engine_sorted_first(self):
        """Test that empty engine values are sorted first."""
        resources = [
            create_resource(engine="python", version="3.9"),
            create_resource(engine="", version="18.x"),
            create_resource(engine="redis", version="6.0"),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 3
        # Empty string sorts before other strings
        assert result[0].engine == ""
        assert result[0].version == "18.x"
        assert result[1].engine == "python"
        assert result[2].engine == "redis"
    
    def test_handles_none_dates(self):
        """Test that None dates are handled correctly."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=None,
            extended_support_start=None,
            extended_support_end=None,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 1
        assert result[0].end_of_support is None
        assert result[0].extended_support_start is None
        assert result[0].extended_support_end is None
    
    def test_mixed_none_and_valid_dates(self):
        """Test aggregation when some resources have None dates and others have valid dates."""
        resources = [
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=None,
            ),
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=date(2025, 10, 1),
            ),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 1
        assert result[0].end_of_support == date(2025, 10, 1)
        assert result[0].resource_count == 2
    
    def test_empty_report(self):
        """Test handling of empty report."""
        report = Report()
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 0
    
    def test_multiple_accounts_same_engine_version(self):
        """Test that same engine-version across accounts is aggregated."""
        resources = [
            create_resource(
                account="account-1",
                engine="python",
                version="3.9",
                end_of_support=date(2025, 10, 1),
            ),
            create_resource(
                account="account-2",
                engine="python",
                version="3.9",
                end_of_support=date(2025, 12, 1),
            ),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        result = generator._collect_engine_versions()
        
        assert len(result) == 1
        assert result[0].engine == "python"
        assert result[0].version == "3.9"
        assert result[0].resource_count == 2
        assert result[0].end_of_support == date(2025, 10, 1)  # Earliest


from datetime import timedelta


class TestCalculateDateRange:
    """Tests for TimelineGenerator._calculate_date_range method.
    
    Validates Requirements 3.1, 3.2, 3.3:
    - 3.1: Timeline starts from the current date
    - 3.2: Timeline extends to the furthest future Support_Event date
    - 3.3: When no future dates exist, display at least 90 days from current date
    """
    
    def test_start_date_is_today(self):
        """Test that start date is always today (Requirement 3.1)."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert start_date == date.today()
    
    def test_end_date_is_max_eos_date(self):
        """Test that end date is the maximum EOS date when it's in the future."""
        future_date = date.today() + timedelta(days=180)
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=future_date,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == future_date
    
    def test_end_date_is_max_extended_support_start(self):
        """Test that end date considers extended_support_start dates."""
        future_date = date.today() + timedelta(days=200)
        resource = create_resource(
            engine="python",
            version="3.9",
            extended_support_start=future_date,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == future_date
    
    def test_end_date_is_max_extended_support_end(self):
        """Test that end date considers extended_support_end dates."""
        future_date = date.today() + timedelta(days=365)
        resource = create_resource(
            engine="python",
            version="3.9",
            extended_support_end=future_date,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == future_date
    
    def test_end_date_is_max_across_all_date_types(self):
        """Test that end date is the maximum across all date types."""
        eos_date = date.today() + timedelta(days=100)
        ext_start_date = date.today() + timedelta(days=150)
        ext_end_date = date.today() + timedelta(days=365)  # Maximum
        
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=eos_date,
            extended_support_start=ext_start_date,
            extended_support_end=ext_end_date,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == ext_end_date
    
    def test_end_date_is_max_across_multiple_resources(self):
        """Test that end date is the maximum across multiple resources."""
        resources = [
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=date.today() + timedelta(days=100),
            ),
            create_resource(
                engine="redis",
                version="6.0",
                end_of_support=date.today() + timedelta(days=200),  # Maximum
            ),
            create_resource(
                engine="mysql",
                version="8.0",
                end_of_support=date.today() + timedelta(days=150),
            ),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == date.today() + timedelta(days=200)
    
    def test_default_90_days_when_no_dates(self):
        """Test that end date is today + 90 days when no dates exist (Requirement 3.3)."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=None,
            extended_support_start=None,
            extended_support_end=None,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == date.today() + timedelta(days=90)
    
    def test_default_90_days_when_all_dates_in_past(self):
        """Test that end date is today + 90 days when all dates are in the past."""
        past_date = date.today() - timedelta(days=30)
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=past_date,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == date.today() + timedelta(days=90)
    
    def test_default_90_days_when_max_date_is_today(self):
        """Test that end date is today + 90 days when max date equals today."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today(),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == date.today() + timedelta(days=90)
    
    def test_empty_report_returns_90_days(self):
        """Test that empty report returns today + 90 days."""
        report = Report()
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert start_date == date.today()
        assert end_date == date.today() + timedelta(days=90)
    
    def test_mixed_past_and_future_dates(self):
        """Test with a mix of past and future dates."""
        resources = [
            create_resource(
                engine="python",
                version="3.9",
                end_of_support=date.today() - timedelta(days=30),  # Past
            ),
            create_resource(
                engine="redis",
                version="6.0",
                end_of_support=date.today() + timedelta(days=60),  # Future - max
            ),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        start_date, end_date = generator._calculate_date_range()
        
        assert end_date == date.today() + timedelta(days=60)


class TestGetCellColor:
    """Tests for TimelineGenerator._get_cell_color method.
    
    Validates Requirements 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.5:
    - 4.1: EOS date marked with red fill
    - 4.2: Extended Support Start marked with blue fill
    - 4.3: Extended Support End marked with dark red fill
    - 4.4: Priority logic for multiple events on same day
    - 5.1: Approaching EOS period marked with yellow
    - 5.2: Extended Support period marked with light blue
    - 5.3: Out of Support period marked with light red
    - 5.5: Weekend days have subtle gray background
    """
    
    def test_eos_event_returns_red(self):
        """Test that EOS event date returns red color (Requirement 4.1)."""
        report = Report()
        generator = TimelineGenerator(report)
        
        eos_date = date(2025, 6, 15)
        current_date = date(2025, 6, 15)  # Same as EOS
        
        result = generator._get_cell_color(
            current_date=current_date,
            eos_date=eos_date,
            ext_start=None,
            ext_end=None,
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_EOS_EVENT
    
    def test_ext_start_event_returns_blue(self):
        """Test that extended support start date returns blue color (Requirement 4.2)."""
        report = Report()
        generator = TimelineGenerator(report)
        
        ext_start = date(2025, 6, 15)
        current_date = date(2025, 6, 15)  # Same as ext_start
        
        result = generator._get_cell_color(
            current_date=current_date,
            eos_date=None,
            ext_start=ext_start,
            ext_end=date(2026, 6, 15),
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_EXT_START_EVENT
    
    def test_ext_end_event_returns_dark_red(self):
        """Test that extended support end date returns dark red color (Requirement 4.3)."""
        report = Report()
        generator = TimelineGenerator(report)
        
        ext_end = date(2026, 6, 15)
        current_date = date(2026, 6, 15)  # Same as ext_end
        
        result = generator._get_cell_color(
            current_date=current_date,
            eos_date=None,
            ext_start=date(2025, 6, 15),
            ext_end=ext_end,
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_EXT_END_EVENT
    
    def test_approaching_eos_returns_yellow(self):
        """Test that approaching EOS period returns yellow color (Requirement 5.1)."""
        report = Report()
        generator = TimelineGenerator(report, days_threshold=90)
        
        eos_date = date(2025, 6, 15)
        current_date = date(2025, 5, 1)  # 45 days before EOS
        
        result = generator._get_cell_color(
            current_date=current_date,
            eos_date=eos_date,
            ext_start=None,
            ext_end=None,
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_APPROACHING_EOS
    
    def test_extended_support_period_returns_light_blue(self):
        """Test that extended support period returns light blue color (Requirement 5.2)."""
        report = Report()
        generator = TimelineGenerator(report)
        
        ext_start = date(2025, 6, 1)
        ext_end = date(2026, 6, 1)
        current_date = date(2025, 9, 15)  # Within extended support period
        
        result = generator._get_cell_color(
            current_date=current_date,
            eos_date=date(2025, 5, 1),  # EOS before ext_start
            ext_start=ext_start,
            ext_end=ext_end,
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_EXTENDED_SUPPORT
    
    def test_out_of_support_returns_light_red(self):
        """Test that out of support period returns light red color (Requirement 5.3)."""
        report = Report()
        generator = TimelineGenerator(report)
        
        eos_date = date(2025, 6, 15)
        current_date = date(2025, 7, 1)  # After EOS, no extended support
        
        result = generator._get_cell_color(
            current_date=current_date,
            eos_date=eos_date,
            ext_start=None,
            ext_end=None,
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_OUT_OF_SUPPORT
    
    def test_weekend_returns_gray(self):
        """Test that weekend with no other state returns gray color (Requirement 5.5)."""
        report = Report()
        generator = TimelineGenerator(report)
        
        current_date = date(2025, 6, 14)  # A Saturday
        
        result = generator._get_cell_color(
            current_date=current_date,
            eos_date=None,
            ext_start=None,
            ext_end=None,
            is_weekend=True
        )
        
        assert result == TimelineGenerator.COLOR_WEEKEND
    
    def test_no_special_state_returns_none(self):
        """Test that no special state returns None."""
        report = Report()
        generator = TimelineGenerator(report)
        
        current_date = date(2025, 6, 16)  # A Monday
        
        result = generator._get_cell_color(
            current_date=current_date,
            eos_date=None,
            ext_start=None,
            ext_end=None,
            is_weekend=False
        )
        
        assert result is None
    
    # Priority tests (Requirement 4.4)
    
    def test_eos_event_takes_priority_over_ext_end(self):
        """Test that EOS event takes priority over ext_end event on same day."""
        report = Report()
        generator = TimelineGenerator(report)
        
        same_date = date(2025, 6, 15)
        
        result = generator._get_cell_color(
            current_date=same_date,
            eos_date=same_date,
            ext_start=date(2025, 1, 1),
            ext_end=same_date,  # Same as EOS
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_EOS_EVENT
    
    def test_eos_event_takes_priority_over_ext_start(self):
        """Test that EOS event takes priority over ext_start event on same day."""
        report = Report()
        generator = TimelineGenerator(report)
        
        same_date = date(2025, 6, 15)
        
        result = generator._get_cell_color(
            current_date=same_date,
            eos_date=same_date,
            ext_start=same_date,  # Same as EOS
            ext_end=date(2026, 6, 15),
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_EOS_EVENT
    
    def test_ext_end_takes_priority_over_ext_start(self):
        """Test that ext_end event takes priority over ext_start event on same day."""
        report = Report()
        generator = TimelineGenerator(report)
        
        same_date = date(2025, 6, 15)
        
        result = generator._get_cell_color(
            current_date=same_date,
            eos_date=None,
            ext_start=same_date,  # Same as ext_end
            ext_end=same_date,
            is_weekend=False
        )
        
        assert result == TimelineGenerator.COLOR_EXT_END_EVENT


class TestCreateHeaderRows:
    """Tests for TimelineGenerator._create_header_rows method.
    
    Validates Requirements 3.5, 3.6, 3.7, 3.8, 4.5:
    - 3.5: Display header row with day of week abbreviation (Mon-Sun)
    - 3.6: Display second header row with date in format "DD" (day number)
    - 3.7: Display third header row with month-year grouping "MMM YYYY"
    - 3.8: Weekend days have distinct background color
    - 4.5: Current date marker with distinct styling
    """
    
    @pytest.fixture
    def workbook(self):
        """Create a fresh workbook for each test."""
        from openpyxl import Workbook
        return Workbook()
    
    def test_returns_correct_start_row(self, workbook):
        """Test that method returns row 5 as the data start row."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 7)
        
        result = generator._create_header_rows(ws, start_date, end_date)
        
        assert result == 5  # Row 4 is separator, row 5 is first data row
    
    def test_day_of_week_abbreviations_correct(self, workbook):
        """Test that day of week abbreviations are correct (Requirement 3.5)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # June 2, 2025 is a Monday
        start_date = date(2025, 6, 2)
        end_date = date(2025, 6, 8)  # Sunday
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Row 2 should have day of week abbreviations
        # Column B = Monday, Column C = Tuesday, etc.
        assert ws.cell(row=2, column=2).value == "Mon"
        assert ws.cell(row=2, column=3).value == "Tue"
        assert ws.cell(row=2, column=4).value == "Wed"
        assert ws.cell(row=2, column=5).value == "Thu"
        assert ws.cell(row=2, column=6).value == "Fri"
        assert ws.cell(row=2, column=7).value == "Sat"
        assert ws.cell(row=2, column=8).value == "Sun"
    
    def test_day_numbers_correct(self, workbook):
        """Test that day numbers are correct (Requirement 3.6)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Row 3 should have day numbers
        assert ws.cell(row=3, column=2).value == 1
        assert ws.cell(row=3, column=3).value == 2
        assert ws.cell(row=3, column=4).value == 3
        assert ws.cell(row=3, column=5).value == 4
        assert ws.cell(row=3, column=6).value == 5
    
    def test_month_year_header_format(self, workbook):
        """Test that month-year header is formatted as 'MMM YYYY' (Requirement 3.7)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Row 1 should have month-year header
        assert ws.cell(row=1, column=2).value == "Jun 2025"
    
    def test_month_year_spans_correct_columns(self, workbook):
        """Test that month-year header spans all columns for that month."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # June 28 to July 3 - spans two months
        start_date = date(2025, 6, 28)
        end_date = date(2025, 7, 3)
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # June should span columns B-D (28, 29, 30)
        # July should span columns E-G (1, 2, 3)
        assert ws.cell(row=1, column=2).value == "Jun 2025"
        assert ws.cell(row=1, column=5).value == "Jul 2025"
    
    def test_weekend_columns_have_styling(self, workbook):
        """Test that weekend columns have distinct background color (Requirement 3.8)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # June 2, 2025 is Monday, June 7 is Saturday, June 8 is Sunday
        start_date = date(2025, 6, 2)
        end_date = date(2025, 6, 8)
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Saturday is column 7 (B=2, C=3, D=4, E=5, F=6, G=7)
        # Sunday is column 8
        saturday_dow_cell = ws.cell(row=2, column=7)
        saturday_day_cell = ws.cell(row=3, column=7)
        sunday_dow_cell = ws.cell(row=2, column=8)
        sunday_day_cell = ws.cell(row=3, column=8)
        
        # Check that weekend cells have the weekend fill color
        assert saturday_dow_cell.fill.start_color.rgb == TimelineGenerator.COLOR_WEEKEND or \
               saturday_dow_cell.fill.fgColor.rgb == TimelineGenerator.COLOR_WEEKEND or \
               "F0F0F0" in str(saturday_dow_cell.fill.start_color.rgb)
        assert saturday_day_cell.fill.start_color.rgb == TimelineGenerator.COLOR_WEEKEND or \
               saturday_day_cell.fill.fgColor.rgb == TimelineGenerator.COLOR_WEEKEND or \
               "F0F0F0" in str(saturday_day_cell.fill.start_color.rgb)
    
    def test_weekday_columns_no_weekend_styling(self, workbook):
        """Test that weekday columns do not have weekend styling."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # June 2, 2025 is Monday
        start_date = date(2025, 6, 2)
        end_date = date(2025, 6, 6)  # Friday
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Monday is column 2
        monday_dow_cell = ws.cell(row=2, column=2)
        
        # Weekday should not have weekend fill
        # Check that fill is not the weekend color
        fill_color = str(monday_dow_cell.fill.start_color.rgb) if monday_dow_cell.fill.start_color else ""
        assert "F0F0F0" not in fill_color or fill_color == "00000000"  # 00000000 is no fill
    
    def test_column_count_matches_date_range(self, workbook):
        """Test that number of date columns equals date range (Property 9)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 10)  # 10 days
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Should have 10 date columns (B through K)
        # Column A is for labels, columns B-K are for dates
        expected_columns = (end_date - start_date).days + 1
        
        # Check that the last date column has a value
        last_col = 1 + expected_columns  # Column A + date columns
        assert ws.cell(row=3, column=last_col).value == 10  # Day 10
        
        # Check that the column after last is empty
        assert ws.cell(row=3, column=last_col + 1).value is None
    
    def test_engine_version_label_in_column_a(self, workbook):
        """Test that column A has the Engine-Version label."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Row 3, Column A should have "Engine-Version" label
        assert ws.cell(row=3, column=1).value == "Engine-Version"
    
    def test_single_day_timeline(self, workbook):
        """Test timeline with a single day."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        single_date = date(2025, 6, 15)  # A Sunday
        
        generator._create_header_rows(ws, single_date, single_date)
        
        # Should have one date column
        assert ws.cell(row=2, column=2).value == "Sun"
        assert ws.cell(row=3, column=2).value == 15
        assert ws.cell(row=1, column=2).value == "Jun 2025"
    
    def test_multi_month_timeline(self, workbook):
        """Test timeline spanning multiple months."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_date = date(2025, 5, 30)
        end_date = date(2025, 7, 2)  # Spans May, June, July
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Check that all three months are present
        month_values = []
        for col in range(2, 50):  # Check enough columns
            val = ws.cell(row=1, column=col).value
            if val and val not in month_values:
                month_values.append(val)
        
        assert "May 2025" in month_values
        assert "Jun 2025" in month_values
        assert "Jul 2025" in month_values
    
    def test_today_marker_styling(self, workbook):
        """Test that today's date column has distinct styling (Requirement 4.5)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        today = date.today()
        start_date = today - timedelta(days=2)
        end_date = today + timedelta(days=2)
        
        generator._create_header_rows(ws, start_date, end_date)
        
        # Today should be in column 4 (A=1, day-2=2, day-1=3, today=4)
        today_col = 4
        today_dow_cell = ws.cell(row=2, column=today_col)
        today_day_cell = ws.cell(row=3, column=today_col)
        
        # Check that today's cells have a border (gold border for today marker)
        # The border should be medium style with gold color
        assert today_dow_cell.border is not None
        assert today_day_cell.border is not None
        
        # Check that the border has the today color
        if today_dow_cell.border.left:
            border_color = today_dow_cell.border.left.color
            if border_color:
                assert TimelineGenerator.COLOR_TODAY in str(border_color.rgb) or \
                       border_color.rgb == TimelineGenerator.COLOR_TODAY


# Property-Based Tests for Header Generation
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st


@st.composite
def date_range_strategy(draw, min_days=1, max_days=365):
    """Generate a valid date range for timeline testing.
    
    Returns a tuple of (start_date, end_date) where end_date >= start_date.
    """
    # Generate a start date within a reasonable range
    base_date = date(2024, 1, 1)
    start_offset = draw(st.integers(min_value=0, max_value=730))  # Up to 2 years from base
    start_date = base_date + timedelta(days=start_offset)
    
    # Generate duration (number of days in range)
    duration = draw(st.integers(min_value=min_days, max_value=max_days))
    end_date = start_date + timedelta(days=duration - 1)
    
    return (start_date, end_date)


class TestHeaderGenerationProperties:
    """Property-based tests for TimelineGenerator._create_header_rows method.
    
    Feature: timeline-view
    
    These tests verify that header generation is correct for any valid date range.
    """
    
    @given(date_range=date_range_strategy(min_days=1, max_days=100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property_10_header_content_correctness(self, date_range):
        """Property 10: Header Content Correctness
        
        *For any* date column in the Timeline sheet, the day-of-week header cell 
        SHALL contain the correct abbreviation (Mon-Sun) for that date, the day 
        number header cell SHALL contain the correct day of month (1-31), and the 
        month-year header SHALL correctly span all columns belonging to that month.
        
        Feature: timeline-view, Property 10: Header Content Correctness
        **Validates: Requirements 3.5, 3.6, 3.7**
        """
        from openpyxl import Workbook
        
        start_date, end_date = date_range
        
        # Create generator and worksheet
        report = Report()
        generator = TimelineGenerator(report)
        wb = Workbook()
        ws = wb.active
        
        # Generate headers
        generator._create_header_rows(ws, start_date, end_date)
        
        # Day of week abbreviations mapping (Python weekday() returns 0=Monday)
        day_abbrevs = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        # Track month spans for verification
        expected_month_spans = {}  # (year, month) -> (start_col, end_col)
        
        # Verify each date column
        current_date = start_date
        col_idx = 2  # Column B is first date column (Column A is labels)
        
        while current_date <= end_date:
            # Verify day of week abbreviation (Row 2)
            expected_dow = day_abbrevs[current_date.weekday()]
            actual_dow = ws.cell(row=2, column=col_idx).value
            assert actual_dow == expected_dow, \
                f"Day of week mismatch at column {col_idx} for {current_date}: " \
                f"expected '{expected_dow}', got '{actual_dow}'"
            
            # Verify day number (Row 3)
            expected_day = current_date.day
            actual_day = ws.cell(row=3, column=col_idx).value
            assert actual_day == expected_day, \
                f"Day number mismatch at column {col_idx} for {current_date}: " \
                f"expected {expected_day}, got {actual_day}"
            
            # Track month span
            year_month = (current_date.year, current_date.month)
            if year_month not in expected_month_spans:
                expected_month_spans[year_month] = (col_idx, col_idx)
            else:
                expected_month_spans[year_month] = (expected_month_spans[year_month][0], col_idx)
            
            current_date += timedelta(days=1)
            col_idx += 1
        
        # Verify month-year headers (Row 1)
        for (year, month), (start_col, end_col) in expected_month_spans.items():
            # Expected format: "MMM YYYY" (e.g., "Jan 2025")
            expected_month_year = date(year, month, 1).strftime("%b %Y")
            
            # The month-year header should be in the first column of the span
            actual_month_year = ws.cell(row=1, column=start_col).value
            assert actual_month_year == expected_month_year, \
                f"Month-year header mismatch at column {start_col}: " \
                f"expected '{expected_month_year}', got '{actual_month_year}'"
            
            # If span is more than one column, verify merged cells
            if end_col > start_col:
                # Check that merged cells exist for this range
                from openpyxl.utils import get_column_letter
                start_col_letter = get_column_letter(start_col)
                end_col_letter = get_column_letter(end_col)
                expected_merge_range = f"{start_col_letter}1:{end_col_letter}1"
                
                # Find if this merge range exists
                merge_found = False
                for merged_range in ws.merged_cells.ranges:
                    if str(merged_range) == expected_merge_range:
                        merge_found = True
                        break
                
                assert merge_found, \
                    f"Expected merged cells {expected_merge_range} for {expected_month_year} not found"
    
    @given(date_range=date_range_strategy(min_days=7, max_days=100))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property_11_weekend_column_styling(self, date_range):
        """Property 11: Weekend Column Styling
        
        *For any* date column representing a Saturday or Sunday, the header cells 
        SHALL have the weekend background color applied.
        
        Feature: timeline-view, Property 11: Weekend Column Styling
        **Validates: Requirements 3.8**
        """
        from openpyxl import Workbook
        
        start_date, end_date = date_range
        
        # Create generator and worksheet
        report = Report()
        generator = TimelineGenerator(report)
        wb = Workbook()
        ws = wb.active
        
        # Generate headers
        generator._create_header_rows(ws, start_date, end_date)
        
        # Verify each date column
        current_date = start_date
        col_idx = 2  # Column B is first date column
        
        while current_date <= end_date:
            is_weekend = current_date.weekday() >= 5  # Saturday=5, Sunday=6
            
            # Check both header rows (row 2 = day of week, row 3 = day number)
            dow_cell = ws.cell(row=2, column=col_idx)
            day_cell = ws.cell(row=3, column=col_idx)
            
            if is_weekend:
                # Weekend cells should have the weekend fill color
                # Check the fill color - it could be in start_color or fgColor
                dow_fill_color = self._get_fill_color(dow_cell)
                day_fill_color = self._get_fill_color(day_cell)
                
                assert dow_fill_color == TimelineGenerator.COLOR_WEEKEND, \
                    f"Weekend day-of-week cell at column {col_idx} ({current_date}, " \
                    f"{['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][current_date.weekday()]}) " \
                    f"should have weekend fill color {TimelineGenerator.COLOR_WEEKEND}, " \
                    f"got '{dow_fill_color}'"
                
                assert day_fill_color == TimelineGenerator.COLOR_WEEKEND, \
                    f"Weekend day-number cell at column {col_idx} ({current_date}) " \
                    f"should have weekend fill color {TimelineGenerator.COLOR_WEEKEND}, " \
                    f"got '{day_fill_color}'"
            else:
                # Weekday cells should NOT have the weekend fill color
                dow_fill_color = self._get_fill_color(dow_cell)
                day_fill_color = self._get_fill_color(day_cell)
                
                # Weekday cells should either have no fill or a different fill
                assert dow_fill_color != TimelineGenerator.COLOR_WEEKEND, \
                    f"Weekday day-of-week cell at column {col_idx} ({current_date}) " \
                    f"should NOT have weekend fill color"
                
                assert day_fill_color != TimelineGenerator.COLOR_WEEKEND, \
                    f"Weekday day-number cell at column {col_idx} ({current_date}) " \
                    f"should NOT have weekend fill color"
            
            current_date += timedelta(days=1)
            col_idx += 1
    
    def _get_fill_color(self, cell) -> str:
        """Extract the fill color from a cell.
        
        Returns the RGB hex color string or empty string if no fill.
        """
        if cell.fill is None:
            return ""
        
        # Try to get the color from different attributes
        fill = cell.fill
        
        # Check if it's a solid fill
        if fill.fill_type == "solid":
            # Try fgColor first (foreground color for solid fills)
            if fill.fgColor and fill.fgColor.rgb:
                color = str(fill.fgColor.rgb)
                # Remove alpha channel if present (ARGB format)
                if len(color) == 8 and color.startswith("00"):
                    return color[2:]
                elif len(color) == 8:
                    return color[2:]  # Skip alpha
                return color
            
            # Try start_color
            if fill.start_color and fill.start_color.rgb:
                color = str(fill.start_color.rgb)
                if len(color) == 8 and color.startswith("00"):
                    return color[2:]
                elif len(color) == 8:
                    return color[2:]
                return color
        
        return ""


class TestCreateDataRows:
    """Tests for TimelineGenerator._create_data_rows method.
    
    Validates Requirements 2.1, 4.1, 4.2, 4.3, 5.1, 5.2, 5.3:
    - 2.1: Display one row for each unique engine-version combination
    - 4.1: Red fill for End of Support date
    - 4.2: Blue fill for Extended Support Start date
    - 4.3: Dark red fill for Extended Support End date
    - 5.1: Yellow fill for "Approaching End-of-Support" period
    - 5.2: Light blue fill for Extended Support period
    - 5.3: Light red fill for Out of Support period
    """
    
    @pytest.fixture
    def workbook(self):
        """Create a fresh workbook for each test."""
        from openpyxl import Workbook
        return Workbook()
    
    def _get_fill_color(self, cell) -> str:
        """Extract the fill color from a cell.
        
        Returns the RGB hex color string or empty string if no fill.
        """
        if cell.fill is None:
            return ""
        
        fill = cell.fill
        
        if fill.fill_type == "solid":
            if fill.fgColor and fill.fgColor.rgb:
                color = str(fill.fgColor.rgb)
                if len(color) == 8:
                    return color[2:]  # Skip alpha
                return color
            
            if fill.start_color and fill.start_color.rgb:
                color = str(fill.start_color.rgb)
                if len(color) == 8:
                    return color[2:]
                return color
        
        return ""
    
    def test_returns_correct_row_after_data(self, workbook):
        """Test that method returns the row index after the last data row."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=date(2025, 10, 1),
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
            EngineVersionData(
                engine="redis",
                version="6.0",
                end_of_support=date(2025, 12, 1),
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        start_row = 5
        
        result = generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Should return start_row + number of engine_versions
        assert result == start_row + len(engine_versions)
    
    def test_creates_one_row_per_engine_version(self, workbook):
        """Test that one row is created per engine-version (Requirement 2.1)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=None,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
            EngineVersionData(
                engine="redis",
                version="6.0",
                end_of_support=None,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
            EngineVersionData(
                engine="mysql",
                version="8.0",
                end_of_support=None,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 3)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Check that each row has the correct label in column A
        assert ws.cell(row=5, column=1).value == "python 3.9"
        assert ws.cell(row=6, column=1).value == "redis 6.0"
        assert ws.cell(row=7, column=1).value == "mysql 8.0"
    
    def test_label_uses_display_name(self, workbook):
        """Test that labels use the display_name property."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=None,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
            EngineVersionData(
                engine="",  # Empty engine
                version="18.x",
                end_of_support=None,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
            EngineVersionData(
                engine="Unknown",  # Unknown engine
                version="2.0",
                end_of_support=None,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 3)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Check labels
        assert ws.cell(row=5, column=1).value == "python 3.9"
        assert ws.cell(row=6, column=1).value == "18.x"  # Just version when engine is empty
        assert ws.cell(row=7, column=1).value == "2.0"   # Just version when engine is "Unknown"
    
    def test_eos_event_cell_has_red_fill(self, workbook):
        """Test that EOS event date has red fill (Requirement 4.1)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        eos_date = date(2025, 6, 3)
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=eos_date,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # EOS date is June 3, which is column 4 (B=2, C=3, D=4)
        eos_cell = ws.cell(row=5, column=4)
        fill_color = self._get_fill_color(eos_cell)
        
        assert fill_color == TimelineGenerator.COLOR_EOS_EVENT
    
    def test_ext_start_event_cell_has_blue_fill(self, workbook):
        """Test that Extended Support Start date has blue fill (Requirement 4.2)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        ext_start_date = date(2025, 6, 3)
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=None,
                extended_support_start=ext_start_date,
                extended_support_end=date(2026, 6, 3),
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Ext start date is June 3, which is column 4
        ext_start_cell = ws.cell(row=5, column=4)
        fill_color = self._get_fill_color(ext_start_cell)
        
        assert fill_color == TimelineGenerator.COLOR_EXT_START_EVENT
    
    def test_ext_end_event_cell_has_dark_red_fill(self, workbook):
        """Test that Extended Support End date has dark red fill (Requirement 4.3)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        ext_end_date = date(2025, 6, 3)
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=None,
                extended_support_start=date(2025, 1, 1),
                extended_support_end=ext_end_date,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Ext end date is June 3, which is column 4
        ext_end_cell = ws.cell(row=5, column=4)
        fill_color = self._get_fill_color(ext_end_cell)
        
        assert fill_color == TimelineGenerator.COLOR_EXT_END_EVENT
    
    def test_approaching_eos_cells_have_yellow_fill(self, workbook):
        """Test that approaching EOS period has yellow fill (Requirement 5.1)."""
        report = Report()
        generator = TimelineGenerator(report, days_threshold=90)
        ws = workbook.active
        
        # EOS is 30 days from start_date
        start_date = date(2025, 6, 1)
        eos_date = date(2025, 7, 1)  # 30 days later
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=eos_date,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        end_date = date(2025, 6, 10)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # All dates from June 1-10 are within 90 days of EOS (July 1)
        # So they should all have yellow fill (approaching EOS)
        for col in range(2, 12):  # Columns B through K (June 1-10)
            cell = ws.cell(row=5, column=col)
            fill_color = self._get_fill_color(cell)
            assert fill_color == TimelineGenerator.COLOR_APPROACHING_EOS, \
                f"Cell at column {col} should have approaching EOS color"
    
    def test_extended_support_period_has_light_blue_fill(self, workbook):
        """Test that extended support period has light blue fill (Requirement 5.2)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # Extended support period from June 1 to June 10
        ext_start = date(2025, 6, 1)
        ext_end = date(2025, 6, 10)
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=date(2025, 5, 1),  # EOS before ext_start
                extended_support_start=ext_start,
                extended_support_end=ext_end,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 2)  # Start after ext_start
        end_date = date(2025, 6, 5)    # End before ext_end
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # All dates should be in extended support period (light blue)
        for col in range(2, 6):  # Columns B through E (June 2-5)
            cell = ws.cell(row=5, column=col)
            fill_color = self._get_fill_color(cell)
            assert fill_color == TimelineGenerator.COLOR_EXTENDED_SUPPORT, \
                f"Cell at column {col} should have extended support color"
    
    def test_out_of_support_period_has_light_red_fill(self, workbook):
        """Test that out of support period has light red fill (Requirement 5.3)."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # EOS is before the timeline start
        eos_date = date(2025, 5, 1)
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=eos_date,
                extended_support_start=None,  # No extended support
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)  # After EOS
        end_date = date(2025, 6, 5)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # All dates should be out of support (light red)
        for col in range(2, 7):  # Columns B through F (June 1-5)
            cell = ws.cell(row=5, column=col)
            fill_color = self._get_fill_color(cell)
            assert fill_color == TimelineGenerator.COLOR_OUT_OF_SUPPORT, \
                f"Cell at column {col} should have out of support color"
    
    def test_weekend_cells_have_gray_fill_when_no_other_state(self, workbook):
        """Test that weekend cells have gray fill when no other state applies."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=None,  # No dates
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        # June 7, 2025 is Saturday, June 8 is Sunday
        start_date = date(2025, 6, 7)
        end_date = date(2025, 6, 8)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Both days are weekends
        saturday_cell = ws.cell(row=5, column=2)
        sunday_cell = ws.cell(row=5, column=3)
        
        assert self._get_fill_color(saturday_cell) == TimelineGenerator.COLOR_WEEKEND
        assert self._get_fill_color(sunday_cell) == TimelineGenerator.COLOR_WEEKEND
    
    def test_freezes_column_a_and_header_rows(self, workbook):
        """Test that column A and header rows are frozen."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=None,
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Freeze panes should be set to B5
        assert ws.freeze_panes == "B5"
    
    def test_empty_engine_versions_list(self, workbook):
        """Test handling of empty engine versions list."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        engine_versions = []
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 5)
        start_row = 5
        
        result = generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Should return start_row (no rows added)
        assert result == start_row
        
        # Freeze panes should still be set
        assert ws.freeze_panes == "B5"
    
    def test_single_day_timeline(self, workbook):
        """Test timeline with a single day."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        single_date = date(2025, 6, 15)
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=single_date,  # EOS on this day
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, single_date, single_date, start_row)
        
        # Should have label in column A
        assert ws.cell(row=5, column=1).value == "python 3.9"
        
        # Should have EOS color in column B
        eos_cell = ws.cell(row=5, column=2)
        assert self._get_fill_color(eos_cell) == TimelineGenerator.COLOR_EOS_EVENT
    
    def test_multiple_engine_versions_with_different_dates(self, workbook):
        """Test multiple engine versions with different support dates."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        engine_versions = [
            EngineVersionData(
                engine="python",
                version="3.9",
                end_of_support=date(2025, 6, 3),  # EOS on June 3
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
            EngineVersionData(
                engine="redis",
                version="6.0",
                end_of_support=date(2025, 6, 5),  # EOS on June 5
                extended_support_start=None,
                extended_support_end=None,
                resource_count=1
            ),
        ]
        
        start_date = date(2025, 6, 1)
        end_date = date(2025, 6, 7)
        start_row = 5
        
        generator._create_data_rows(ws, engine_versions, start_date, end_date, start_row)
        
        # Row 5 (python 3.9): EOS on June 3 (column 4)
        assert self._get_fill_color(ws.cell(row=5, column=4)) == TimelineGenerator.COLOR_EOS_EVENT
        
        # Row 6 (redis 6.0): EOS on June 5 (column 6)
        assert self._get_fill_color(ws.cell(row=6, column=6)) == TimelineGenerator.COLOR_EOS_EVENT
        
        # Row 5: After EOS (June 4-7) should be out of support
        for col in [5, 6, 7, 8]:  # June 4, 5, 6, 7
            fill_color = self._get_fill_color(ws.cell(row=5, column=col))
            # Weekend days (June 7 is Saturday, June 8 is Sunday) might have different handling
            # but since we're past EOS, it should be out of support
            assert fill_color == TimelineGenerator.COLOR_OUT_OF_SUPPORT, \
                f"Row 5, column {col} should be out of support"


class TestCreateLegend:
    """Tests for TimelineGenerator._create_legend method.
    
    Validates Requirement 5.4:
    - 5.4: THE Timeline_Sheet SHALL include a legend explaining the color coding
    """
    
    @pytest.fixture
    def workbook(self):
        """Create a fresh workbook for each test."""
        from openpyxl import Workbook
        return Workbook()
    
    def _get_fill_color(self, cell) -> str:
        """Extract the fill color from a cell.
        
        Returns the RGB hex color string or empty string if no fill.
        """
        if cell.fill is None:
            return ""
        
        fill = cell.fill
        
        if fill.fill_type == "solid":
            if fill.fgColor and fill.fgColor.rgb:
                color = str(fill.fgColor.rgb)
                if len(color) == 8:
                    return color[2:]  # Skip alpha
                return color
            
            if fill.start_color and fill.start_color.rgb:
                color = str(fill.start_color.rgb)
                if len(color) == 8:
                    return color[2:]
                return color
        
        return ""
    
    def _has_border_color(self, cell, expected_color: str) -> bool:
        """Check if a cell has a border with the expected color.
        
        Args:
            cell: The cell to check.
            expected_color: The expected RGB hex color string.
            
        Returns:
            True if the cell has a border with the expected color.
        """
        if cell.border is None:
            return False
        
        for side_name in ['left', 'right', 'top', 'bottom']:
            side = getattr(cell.border, side_name, None)
            if side and side.color:
                color_rgb = str(side.color.rgb) if side.color.rgb else ""
                # Handle ARGB format (8 chars) vs RGB format (6 chars)
                if len(color_rgb) == 8:
                    color_rgb = color_rgb[2:]  # Skip alpha
                if color_rgb == expected_color:
                    return True
        
        return False
    
    def test_legend_title_present(self, workbook):
        """Test that legend has a title row."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Title should be in row start_row + 1 (after empty spacing row)
        title_cell = ws.cell(row=start_row + 1, column=1)
        assert title_cell.value == "Legend"
    
    def test_legend_title_is_bold(self, workbook):
        """Test that legend title is bold."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        title_cell = ws.cell(row=start_row + 1, column=1)
        assert title_cell.font.bold is True
    
    def test_legend_has_all_color_entries(self, workbook):
        """Test that legend includes all color states."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Expected descriptions
        expected_descriptions = [
            "End of Support Event",
            "Extended Support Start",
            "Extended Support End",
            "Approaching End of Support",
            "Extended Support Period",
            "Out of Support",
            "Weekend",
            "Today Marker",
        ]
        
        # Collect all descriptions from column B starting from row after title
        actual_descriptions = []
        for row in range(start_row + 2, start_row + 2 + len(expected_descriptions)):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value:
                actual_descriptions.append(desc_cell.value)
        
        assert len(actual_descriptions) == len(expected_descriptions)
        for expected in expected_descriptions:
            assert expected in actual_descriptions, f"Missing legend entry: {expected}"
    
    def test_eos_event_color_sample(self, workbook):
        """Test that End of Support Event has correct color sample."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Find the row with "End of Support Event" description
        for row in range(start_row + 2, start_row + 15):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value == "End of Support Event":
                color_cell = ws.cell(row=row, column=1)
                fill_color = self._get_fill_color(color_cell)
                assert fill_color == TimelineGenerator.COLOR_EOS_EVENT
                return
        
        pytest.fail("End of Support Event entry not found in legend")
    
    def test_ext_start_color_sample(self, workbook):
        """Test that Extended Support Start has correct color sample."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Find the row with "Extended Support Start" description
        for row in range(start_row + 2, start_row + 15):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value == "Extended Support Start":
                color_cell = ws.cell(row=row, column=1)
                fill_color = self._get_fill_color(color_cell)
                assert fill_color == TimelineGenerator.COLOR_EXT_START_EVENT
                return
        
        pytest.fail("Extended Support Start entry not found in legend")
    
    def test_ext_end_color_sample(self, workbook):
        """Test that Extended Support End has correct color sample."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Find the row with "Extended Support End" description
        for row in range(start_row + 2, start_row + 15):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value == "Extended Support End":
                color_cell = ws.cell(row=row, column=1)
                fill_color = self._get_fill_color(color_cell)
                assert fill_color == TimelineGenerator.COLOR_EXT_END_EVENT
                return
        
        pytest.fail("Extended Support End entry not found in legend")
    
    def test_approaching_eos_color_sample(self, workbook):
        """Test that Approaching End of Support has correct color sample."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Find the row with "Approaching End of Support" description
        for row in range(start_row + 2, start_row + 15):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value == "Approaching End of Support":
                color_cell = ws.cell(row=row, column=1)
                fill_color = self._get_fill_color(color_cell)
                assert fill_color == TimelineGenerator.COLOR_APPROACHING_EOS
                return
        
        pytest.fail("Approaching End of Support entry not found in legend")
    
    def test_extended_support_period_color_sample(self, workbook):
        """Test that Extended Support Period has correct color sample."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Find the row with "Extended Support Period" description
        for row in range(start_row + 2, start_row + 15):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value == "Extended Support Period":
                color_cell = ws.cell(row=row, column=1)
                fill_color = self._get_fill_color(color_cell)
                assert fill_color == TimelineGenerator.COLOR_EXTENDED_SUPPORT
                return
        
        pytest.fail("Extended Support Period entry not found in legend")
    
    def test_out_of_support_color_sample(self, workbook):
        """Test that Out of Support has correct color sample."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Find the row with "Out of Support" description
        for row in range(start_row + 2, start_row + 15):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value == "Out of Support":
                color_cell = ws.cell(row=row, column=1)
                fill_color = self._get_fill_color(color_cell)
                assert fill_color == TimelineGenerator.COLOR_OUT_OF_SUPPORT
                return
        
        pytest.fail("Out of Support entry not found in legend")
    
    def test_weekend_color_sample(self, workbook):
        """Test that Weekend has correct color sample."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Find the row with "Weekend" description
        for row in range(start_row + 2, start_row + 15):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value == "Weekend":
                color_cell = ws.cell(row=row, column=1)
                fill_color = self._get_fill_color(color_cell)
                assert fill_color == TimelineGenerator.COLOR_WEEKEND
                return
        
        pytest.fail("Weekend entry not found in legend")
    
    def test_today_marker_has_border(self, workbook):
        """Test that Today Marker has a gold border instead of fill."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Find the row with "Today Marker" description
        for row in range(start_row + 2, start_row + 15):
            desc_cell = ws.cell(row=row, column=2)
            if desc_cell.value == "Today Marker":
                color_cell = ws.cell(row=row, column=1)
                # Today marker should have a border, not a fill
                assert self._has_border_color(color_cell, TimelineGenerator.COLOR_TODAY), \
                    "Today Marker should have a gold border"
                return
        
        pytest.fail("Today Marker entry not found in legend")
    
    def test_legend_descriptions_in_column_b(self, workbook):
        """Test that all descriptions are in column B."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Check that descriptions are in column B
        expected_descriptions = [
            "End of Support Event",
            "Extended Support Start",
            "Extended Support End",
            "Approaching End of Support",
            "Extended Support Period",
            "Out of Support",
            "Weekend",
            "Today Marker",
        ]
        
        for i, expected in enumerate(expected_descriptions):
            row = start_row + 2 + i  # Title is at start_row + 1, entries start at start_row + 2
            desc_cell = ws.cell(row=row, column=2)
            assert desc_cell.value == expected, \
                f"Row {row} should have description '{expected}', got '{desc_cell.value}'"
    
    def test_legend_color_samples_in_column_a(self, workbook):
        """Test that all color samples are in column A."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Expected colors in order (excluding Today Marker which uses border)
        expected_colors = [
            TimelineGenerator.COLOR_EOS_EVENT,
            TimelineGenerator.COLOR_EXT_START_EVENT,
            TimelineGenerator.COLOR_EXT_END_EVENT,
            TimelineGenerator.COLOR_APPROACHING_EOS,
            TimelineGenerator.COLOR_EXTENDED_SUPPORT,
            TimelineGenerator.COLOR_OUT_OF_SUPPORT,
            TimelineGenerator.COLOR_WEEKEND,
            # Today Marker uses border, not fill
        ]
        
        for i, expected_color in enumerate(expected_colors):
            row = start_row + 2 + i
            color_cell = ws.cell(row=row, column=1)
            fill_color = self._get_fill_color(color_cell)
            assert fill_color == expected_color, \
                f"Row {row} should have color '{expected_color}', got '{fill_color}'"
    
    def test_legend_starts_after_spacing_row(self, workbook):
        """Test that legend starts after an empty spacing row."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        start_row = 10
        generator._create_legend(ws, start_row)
        
        # Row start_row should be empty (spacing row)
        # Title should be at start_row + 1
        spacing_cell = ws.cell(row=start_row, column=1)
        title_cell = ws.cell(row=start_row + 1, column=1)
        
        assert spacing_cell.value is None, "Spacing row should be empty"
        assert title_cell.value == "Legend", "Title should be at start_row + 1"
    
    def test_legend_with_different_start_rows(self, workbook):
        """Test that legend works correctly with different start rows."""
        report = Report()
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # Test with different start rows
        for start_row in [5, 10, 20, 50]:
            # Clear the worksheet
            for row in ws.iter_rows():
                for cell in row:
                    cell.value = None
            
            generator._create_legend(ws, start_row)
            
            # Title should be at start_row + 1
            title_cell = ws.cell(row=start_row + 1, column=1)
            assert title_cell.value == "Legend", \
                f"Title should be at row {start_row + 1} for start_row={start_row}"
            
            # First entry should be at start_row + 2
            first_entry_cell = ws.cell(row=start_row + 2, column=2)
            assert first_entry_cell.value == "End of Support Event", \
                f"First entry should be at row {start_row + 2} for start_row={start_row}"


class TestGenerate:
    """Tests for TimelineGenerator.generate method.
    
    Validates Requirement 1.1:
    - 1.1: WHEN the ExcelFormatter generates an Excel file, THE Timeline_Sheet SHALL be created as a new worksheet
    
    The generate method orchestrates:
    - Header creation (month-year, day of week, day number)
    - Data rows for each engine-version combination
    - Legend explaining color coding
    - Column widths (narrow for date columns, wider for label column)
    """
    
    @pytest.fixture
    def workbook(self):
        """Create a fresh workbook for each test."""
        from openpyxl import Workbook
        return Workbook()
    
    def test_generate_creates_headers(self, workbook):
        """Test that generate creates header rows."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Check that header row exists (Engine-Version label in column A, row 3)
        assert ws.cell(row=3, column=1).value == "Engine-Version"
    
    def test_generate_creates_data_rows(self, workbook):
        """Test that generate creates data rows for engine-versions."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Data rows start at row 5 (after headers and separator)
        # Check that the engine-version label is present
        assert ws.cell(row=5, column=1).value == "python 3.9"
    
    def test_generate_creates_legend(self, workbook):
        """Test that generate creates a legend section."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Find the legend title - it should be somewhere after the data rows
        legend_found = False
        for row in range(1, 50):
            if ws.cell(row=row, column=1).value == "Legend":
                legend_found = True
                break
        
        assert legend_found, "Legend title should be present in the worksheet"
    
    def test_generate_with_empty_report(self, workbook):
        """Test that generate handles empty report gracefully."""
        report = Report()
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # Should not raise an exception
        generator.generate(ws)
        
        # Check that headers are still created
        assert ws.cell(row=3, column=1).value == "Engine-Version"
        
        # Check that "no data" message is shown
        assert ws.cell(row=5, column=1).value == "No engine-version data available"
    
    def test_generate_with_multiple_engine_versions(self, workbook):
        """Test that generate creates rows for multiple engine-versions."""
        resources = [
            create_resource(engine="python", version="3.9", end_of_support=date.today() + timedelta(days=30)),
            create_resource(engine="redis", version="6.0", end_of_support=date.today() + timedelta(days=60)),
            create_resource(engine="mysql", version="8.0", end_of_support=date.today() + timedelta(days=90)),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Data rows start at row 5, sorted alphabetically by engine
        assert ws.cell(row=5, column=1).value == "mysql 8.0"
        assert ws.cell(row=6, column=1).value == "python 3.9"
        assert ws.cell(row=7, column=1).value == "redis 6.0"
    
    def test_generate_sets_column_a_width(self, workbook):
        """Test that generate sets column A width for labels."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Column A should be 25 characters wide (set in _create_header_rows)
        assert ws.column_dimensions["A"].width == 25
    
    def test_generate_sets_date_column_widths(self, workbook):
        """Test that generate sets narrow widths for date columns."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=7),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Date columns (B onwards) should be 4 characters wide
        assert ws.column_dimensions["B"].width == 4
        assert ws.column_dimensions["C"].width == 4
    
    def test_generate_freezes_panes(self, workbook):
        """Test that generate freezes column A and header rows."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() + timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Freeze panes should be at B5 (freezing rows 1-4 and column A)
        assert ws.freeze_panes == "B5"
    
    def test_generate_with_no_future_dates(self, workbook):
        """Test that generate handles resources with no future dates."""
        # All dates in the past
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=date.today() - timedelta(days=30),
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # Should not raise an exception
        generator.generate(ws)
        
        # Check that headers are created
        assert ws.cell(row=3, column=1).value == "Engine-Version"
        
        # Check that data row is created
        assert ws.cell(row=5, column=1).value == "python 3.9"
    
    def test_generate_with_none_dates(self, workbook):
        """Test that generate handles resources with None dates."""
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=None,
            extended_support_start=None,
            extended_support_end=None,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # Should not raise an exception
        generator.generate(ws)
        
        # Check that headers are created
        assert ws.cell(row=3, column=1).value == "Engine-Version"
        
        # Check that data row is created
        assert ws.cell(row=5, column=1).value == "python 3.9"
    
    def test_generate_legend_after_data_rows(self, workbook):
        """Test that legend appears after all data rows."""
        resources = [
            create_resource(engine="python", version="3.9", end_of_support=date.today() + timedelta(days=30)),
            create_resource(engine="redis", version="6.0", end_of_support=date.today() + timedelta(days=60)),
        ]
        report = build_report_from_resources(resources)
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Data rows are at 5 and 6, so legend should start after row 6
        # Legend title should be at row 8 (row 7 is spacing)
        legend_row = None
        for row in range(7, 20):
            if ws.cell(row=row, column=1).value == "Legend":
                legend_row = row
                break
        
        assert legend_row is not None, "Legend should be present"
        assert legend_row > 6, "Legend should appear after data rows"
    
    def test_generate_applies_cell_colors(self, workbook):
        """Test that generate applies appropriate cell colors for support events."""
        eos_date = date.today() + timedelta(days=10)
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=eos_date,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        generator.generate(ws)
        
        # Find the column for the EOS date
        # Start date is today, so EOS date column is at column B + 10 = column L (column 12)
        eos_col = 2 + 10  # Column B is 2, plus 10 days
        
        # Check that the EOS date cell has red fill
        eos_cell = ws.cell(row=5, column=eos_col)
        if eos_cell.fill and eos_cell.fill.fgColor:
            fill_color = eos_cell.fill.fgColor.rgb
            if isinstance(fill_color, str) and len(fill_color) == 8:
                fill_color = fill_color[2:]  # Remove alpha prefix
            assert fill_color == TimelineGenerator.COLOR_EOS_EVENT
    
    def test_generate_with_extended_support(self, workbook):
        """Test that generate handles extended support dates correctly."""
        eos_date = date.today() + timedelta(days=5)
        ext_start = date.today() + timedelta(days=5)
        ext_end = date.today() + timedelta(days=15)
        
        resource = create_resource(
            engine="python",
            version="3.9",
            end_of_support=eos_date,
            extended_support_start=ext_start,
            extended_support_end=ext_end,
        )
        report = build_report_from_resources([resource])
        
        generator = TimelineGenerator(report)
        ws = workbook.active
        
        # Should not raise an exception
        generator.generate(ws)
        
        # Check that data row is created
        assert ws.cell(row=5, column=1).value == "python 3.9"
