"""Output formatters for EndOfSupportTool.

Provides TextFormatter, CSVFormatter, JSONFormatter, and ExcelFormatter for generating
reports in different output formats.
"""

import csv
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Handle imports for both package and frozen executable modes
try:
    from .models import (
        Report,
        Resource,
        SupportStatus,
        AccountGroup,
        ServiceGroup,
        EngineGroup,
        VersionGroup,
    )
    from . import __version__
except ImportError:
    from models import (
        Report,
        Resource,
        SupportStatus,
        AccountGroup,
        ServiceGroup,
        EngineGroup,
        VersionGroup,
    )
    __version__ = "2.4.2"

# Optional Excel support
try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    Workbook = None  # For type hints when openpyxl not installed
    PatternFill = None  # For type hints when openpyxl not installed
    Font = None
    Alignment = None
    Border = None
    Side = None

# Optional win32com support for real pivot tables (Windows only)
try:
    import win32com.client
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False

# Path to pivot table template (for cross-platform support)
import sys
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


@dataclass
class EngineVersionData:
    """Aggregated support dates for a service-engine-version combination."""
    service: str
    engine: str
    version: str
    end_of_support: Optional[date]
    extended_support_start: Optional[date]
    extended_support_end: Optional[date]
    resource_count: int
    
    @property
    def display_name(self) -> str:
        """Get the display name for this engine-version.
        
        Returns "{engine} {version}" when engine is present and not "Unknown",
        otherwise returns just the version.
        """
        if self.engine and self.engine != "Unknown":
            return f"{self.engine} {self.version}"
        return self.version


class TimelineGenerator:
    """Generates a timeline visualization sheet for support events.
    
    Creates a Gantt-chart style visualization of support lifecycle events
    using daily columns with day-of-week indicators and weekend highlighting.
    Each row represents a unique engine-version combination, and columns
    represent individual days from the current date to the furthest future
    support event.
    """
    
    # Color constants for timeline visualization
    COLOR_WEEKEND = "F0F0F0"           # Light gray for weekends
    COLOR_TODAY = "FFD700"             # Gold border for today
    COLOR_APPROACHING_EOS = "FFEB9C"   # Yellow - approaching end of support
    COLOR_EXTENDED_SUPPORT = "BDD7EE"  # Light blue - in extended support
    COLOR_OUT_OF_SUPPORT = "FFC7CE"    # Light red - out of support
    COLOR_EOS_EVENT = "FF0000"         # Red - end of support event marker
    COLOR_EXT_START_EVENT = "0070C0"   # Blue - extended support start marker
    COLOR_EXT_END_EVENT = "C00000"     # Dark red - extended support end marker
    
    def __init__(self, report: Report, days_threshold: int = 90):
        """Initialize the timeline generator.
        
        Args:
            report: Report object containing resource data.
            days_threshold: Days before EOS to mark as "approaching".
        """
        self.report = report
        self.days_threshold = days_threshold
    
    def generate(self, ws) -> None:
        """Generate the timeline sheet content.
        
        Orchestrates the creation of the timeline sheet by:
        1. Collecting engine-version data from the report
        2. Calculating the date range for the timeline
        3. Creating header rows (month-year, day of week, day number)
        4. Creating data rows for each engine-version combination
        5. Creating a legend explaining the color coding
        
        Args:
            ws: openpyxl Worksheet to populate.
        """
        # Step 1: Collect engine-version data
        engine_versions = self._collect_engine_versions()
        
        # Step 2: Calculate date range
        start_date, end_date = self._calculate_date_range()
        
        # Step 3: Create header rows (returns the row index where data should start)
        data_start_row = self._create_header_rows(ws, start_date, end_date)
        
        # Step 4: Create data rows (or show message if no data)
        if engine_versions:
            next_row = self._create_data_rows(
                ws, 
                engine_versions, 
                start_date, 
                end_date, 
                data_start_row
            )
        else:
            # Handle empty data case - show a message
            no_data_cell = ws.cell(row=data_start_row, column=1, value="No engine-version data available")
            no_data_cell.font = Font(italic=True)
            next_row = data_start_row + 1
        
        # Step 5: Create legend below the data rows
        self._create_legend(ws, next_row)
    
    def _collect_engine_versions(self) -> List[EngineVersionData]:
        """Collect unique engine-version combinations with their dates.
        
        Iterates through report.accounts → services → engines → versions
        and aggregates dates for each unique service-engine-version combination.
        Uses earliest EOS, earliest ext_start, and latest ext_end.
        Results are sorted alphabetically by service, then engine, then version.
        
        Returns:
            Sorted list of EngineVersionData objects.
        """
        # Dictionary to aggregate data by (service, engine, version) key
        # Value: [earliest_eos, earliest_ext_start, latest_ext_end, resource_count]
        aggregated: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        
        # Iterate through the report hierarchy
        for account_name, account_group in self.report.accounts.items():
            for service_name, service_group in account_group.services.items():
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        # Create key from service, engine and version
                        key = (service_name, engine_name or "", version_name)
                        
                        # Initialize entry if not exists
                        if key not in aggregated:
                            aggregated[key] = {
                                "end_of_support": None,
                                "extended_support_start": None,
                                "extended_support_end": None,
                                "resource_count": 0,
                            }
                        
                        # Aggregate resource count
                        aggregated[key]["resource_count"] += len(version_group.resources)
                        
                        # Aggregate dates from resources
                        for resource in version_group.resources:
                            # Earliest EOS
                            if resource.end_of_support is not None:
                                current_eos = aggregated[key]["end_of_support"]
                                if current_eos is None or resource.end_of_support < current_eos:
                                    aggregated[key]["end_of_support"] = resource.end_of_support
                            
                            # Earliest extended support start
                            if resource.extended_support_start is not None:
                                current_ext_start = aggregated[key]["extended_support_start"]
                                if current_ext_start is None or resource.extended_support_start < current_ext_start:
                                    aggregated[key]["extended_support_start"] = resource.extended_support_start
                            
                            # Latest extended support end
                            if resource.extended_support_end is not None:
                                current_ext_end = aggregated[key]["extended_support_end"]
                                if current_ext_end is None or resource.extended_support_end > current_ext_end:
                                    aggregated[key]["extended_support_end"] = resource.extended_support_end
        
        # Convert to list of EngineVersionData objects
        result: List[EngineVersionData] = []
        for (service, engine, version), data in aggregated.items():
            result.append(EngineVersionData(
                service=service,
                engine=engine,
                version=version,
                end_of_support=data["end_of_support"],
                extended_support_start=data["extended_support_start"],
                extended_support_end=data["extended_support_end"],
                resource_count=data["resource_count"],
            ))
        
        # Sort alphabetically by service, then engine, then version (all case-insensitive)
        result.sort(key=lambda x: (x.service.lower(), x.engine.lower(), x.version.lower()))
        
        return result
    
    def _calculate_date_range(self) -> Tuple[date, date]:
        """Calculate the start and end dates for the timeline.
        
        Finds the maximum future date across all engine-versions.
        Returns (today, max_date) or (today, today + 90 days) if no future dates.
        
        Returns:
            Tuple of (start_date, end_date).
        """
        today = date.today()
        
        # Collect all engine-version data
        engine_versions = self._collect_engine_versions()
        
        # Find the maximum date across all support dates
        max_date: Optional[date] = None
        
        for ev in engine_versions:
            # Check end_of_support date
            if ev.end_of_support is not None:
                if max_date is None or ev.end_of_support > max_date:
                    max_date = ev.end_of_support
            
            # Check extended_support_start date
            if ev.extended_support_start is not None:
                if max_date is None or ev.extended_support_start > max_date:
                    max_date = ev.extended_support_start
            
            # Check extended_support_end date
            if ev.extended_support_end is not None:
                if max_date is None or ev.extended_support_end > max_date:
                    max_date = ev.extended_support_end
        
        # If no future dates exist, use today + 90 days as the end date
        if max_date is None or max_date <= today:
            end_date = today + timedelta(days=90)
        else:
            end_date = max_date
        
        return (today, end_date)
    
    def _create_header_rows(self, ws, start_date: date, end_date: date) -> int:
        """Create the header rows with year, month, week, and day granularity with Excel grouping.
        
        Creates a 6-row header structure with Excel column grouping for drill-down:
        - Row 1: Year headers (always visible at top)
        - Row 2: Month headers with vertical text (for months grouping view)
        - Row 3: Week number headers (visible when expanded to weeks)
        - Row 4: Day of week abbreviations (horizontal text)
        - Row 5: Day numbers (1-31)
        - Row 6: "Engine-Version" label row (separator before data)
        
        Column A contains labels: "Years", "Months", "Weeks", "Days", "", "Engine-Version"
        
        Excel grouping allows users to collapse/expand:
        - Collapse all: Shows only months (with vertical month names) - DEFAULT VIEW
        - Expand to weeks: Shows months and weeks
        - Expand to days: Shows full detail
        
        Args:
            ws: Worksheet to populate.
            start_date: First date in timeline.
            end_date: Last date in timeline.
            
        Returns:
            Row index where data rows should start (7).
        """
        # Day of week abbreviations
        day_abbrevs = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        # Style definitions
        header_font = Font(bold=True)
        header_alignment = Alignment(horizontal="center", vertical="center")
        # Vertical text alignment (bottom to top, text_rotation=90) for month headers
        vertical_alignment = Alignment(horizontal="center", vertical="center", text_rotation=90)
        weekend_fill = PatternFill(start_color=self.COLOR_WEEKEND, end_color=self.COLOR_WEEKEND, fill_type="solid")
        today_border = Border(
            left=Side(style="medium", color=self.COLOR_TODAY),
            right=Side(style="medium", color=self.COLOR_TODAY),
            top=Side(style="medium", color=self.COLOR_TODAY),
            bottom=Side(style="medium", color=self.COLOR_TODAY),
        )
        # Alternating colors for banded appearance (same palette, different shades)
        # Years use darker shades
        year_fills = [
            PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid"),  # Dark navy blue
            PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid"),  # Dark blue
        ]
        # Months use medium shades
        month_fills = [
            PatternFill(start_color="5B9BD5", end_color="5B9BD5", fill_type="solid"),  # Medium blue
            PatternFill(start_color="9DC3E6", end_color="9DC3E6", fill_type="solid"),  # Light blue
        ]
        year_month_font = Font(bold=True, color="FFFFFF")
        month_font_dark = Font(bold=True, color="000000")  # Dark text for lighter month backgrounds
        week_fill = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
        week_font = Font(bold=True, color="000000")
        label_font = Font(bold=True)
        label_alignment = Alignment(horizontal="left", vertical="center")
        
        # Column A and B labels for each row
        # Column A: Service, Column B: Engine-Version
        ws.cell(row=1, column=1, value="Years").font = label_font
        ws.cell(row=1, column=1).alignment = label_alignment
        ws.cell(row=2, column=1, value="Months").font = label_font
        ws.cell(row=2, column=1).alignment = label_alignment
        ws.cell(row=3, column=1, value="Weeks").font = label_font
        ws.cell(row=3, column=1).alignment = label_alignment
        ws.cell(row=4, column=1, value="Days").font = label_font
        ws.cell(row=4, column=1).alignment = label_alignment
        # Row 6 has Service and Engine-Version labels
        ws.cell(row=6, column=1, value="Service").font = label_font
        ws.cell(row=6, column=1).alignment = label_alignment
        ws.cell(row=6, column=2, value="Engine-Version").font = label_font
        ws.cell(row=6, column=2).alignment = label_alignment
        ws.column_dimensions["A"].width = 20  # Service column
        ws.column_dimensions["B"].width = 25  # Engine-Version column
        
        # Track spans for merging and grouping
        # Key: year, Value: (start_col, end_col)
        year_spans: Dict[int, Tuple[int, int]] = {}
        # Key: (year, month), Value: (start_col, end_col)
        month_spans: Dict[Tuple[int, int], Tuple[int, int]] = {}
        # Key: (year, week), Value: (start_col, end_col)
        week_spans: Dict[Tuple[int, int], Tuple[int, int]] = {}
        # Track which columns belong to which week for grouping
        week_columns: Dict[Tuple[int, int], List[int]] = {}
        
        today = date.today()
        current_date = start_date
        col_idx = 3  # Start from column C (A=Service, B=Engine-Version)
        
        while current_date <= end_date:
            day_of_week = current_date.weekday()
            day_abbrev = day_abbrevs[day_of_week]
            day_number = current_date.day
            year = current_date.year
            year_month = (current_date.year, current_date.month)
            # ISO week number (year, week)
            iso_cal = current_date.isocalendar()
            year_week = (iso_cal[0], iso_cal[1])
            
            is_weekend = day_of_week >= 5
            is_today = current_date == today
            
            # Track year span
            if year not in year_spans:
                year_spans[year] = (col_idx, col_idx)
            else:
                year_spans[year] = (year_spans[year][0], col_idx)
            
            # Track month span
            if year_month not in month_spans:
                month_spans[year_month] = (col_idx, col_idx)
            else:
                month_spans[year_month] = (month_spans[year_month][0], col_idx)
            
            # Track week span
            if year_week not in week_spans:
                week_spans[year_week] = (col_idx, col_idx)
                week_columns[year_week] = [col_idx]
            else:
                week_spans[year_week] = (week_spans[year_week][0], col_idx)
                week_columns[year_week].append(col_idx)
            
            # Row 4: Day of week abbreviation (horizontal text)
            dow_cell = ws.cell(row=4, column=col_idx, value=day_abbrev)
            dow_cell.font = header_font
            dow_cell.alignment = header_alignment
            
            # Row 5: Day number
            day_cell = ws.cell(row=5, column=col_idx, value=day_number)
            day_cell.font = header_font
            day_cell.alignment = header_alignment
            
            # Apply weekend styling
            if is_weekend:
                dow_cell.fill = weekend_fill
                day_cell.fill = weekend_fill
            
            # Apply today marker styling
            if is_today:
                dow_cell.border = today_border
                day_cell.border = today_border
            
            # Set narrow column width for date columns
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = 4
            
            current_date += timedelta(days=1)
            col_idx += 1
        
        # Row 1: Year headers with merged cells (alternating colors)
        sorted_years = sorted(year_spans.items())
        for idx, (year, (start_col, end_col)) in enumerate(sorted_years):
            year_cell = ws.cell(row=1, column=start_col, value=str(year))
            year_cell.font = year_month_font
            year_cell.fill = year_fills[idx % 2]  # Alternate between two shades
            year_cell.alignment = header_alignment
            
            if end_col > start_col:
                start_col_letter = get_column_letter(start_col)
                end_col_letter = get_column_letter(end_col)
                ws.merge_cells(f"{start_col_letter}1:{end_col_letter}1")
        
        # Row 2: Month headers with merged cells (alternating colors, vertical text)
        sorted_months = sorted(month_spans.items())
        for idx, ((year, month), (start_col, end_col)) in enumerate(sorted_months):
            month_date = date(year, month, 1)
            month_str = month_date.strftime("%B")  # Full month name
            
            month_cell = ws.cell(row=2, column=start_col, value=month_str)
            # Use dark text for lighter backgrounds (odd index = lighter shade)
            month_cell.font = month_font_dark if idx % 2 == 1 else year_month_font
            month_cell.fill = month_fills[idx % 2]  # Alternate between two shades
            month_cell.alignment = vertical_alignment  # Vertical text (bottom to top)
            
            if end_col > start_col:
                start_col_letter = get_column_letter(start_col)
                end_col_letter = get_column_letter(end_col)
                ws.merge_cells(f"{start_col_letter}2:{end_col_letter}2")
        
        # Row 3: Week headers with merged cells
        for (year, week), (start_col, end_col) in sorted(week_spans.items()):
            week_str = f"W{week}"
            week_cell = ws.cell(row=3, column=start_col, value=week_str)
            week_cell.font = week_font
            week_cell.fill = week_fill
            week_cell.alignment = header_alignment
            
            if end_col > start_col:
                start_col_letter = get_column_letter(start_col)
                end_col_letter = get_column_letter(end_col)
                ws.merge_cells(f"{start_col_letter}3:{end_col_letter}3")
        
        # Apply Excel column grouping (outline levels)
        # Grouping hierarchy:
        # - Level 0: First day of each month (always visible - monthly summary)
        # - Level 1: First day of each week (visible when expanded to weeks)
        # - Level 2: Other days (visible when expanded to days)
        
        # Identify first column of each month
        first_col_of_month = set()
        for year_month, (start_col, end_col) in month_spans.items():
            first_col_of_month.add(start_col)
        
        # Identify first column of each week
        first_col_of_week = set()
        for year_week, columns in week_columns.items():
            if columns:
                first_col_of_week.add(columns[0])
        
        # Apply outline levels to all date columns
        total_days = (end_date - start_date).days + 1
        for day_offset in range(total_days):
            col_idx = 3 + day_offset  # Column C is index 3 (A=Service, B=Engine-Version)
            col_letter = get_column_letter(col_idx)
            
            if col_idx in first_col_of_month:
                # First day of month - always visible (level 0)
                ws.column_dimensions[col_letter].outlineLevel = 0
            elif col_idx in first_col_of_week:
                # First day of week (but not first of month) - level 1
                ws.column_dimensions[col_letter].outlineLevel = 1
                ws.column_dimensions[col_letter].hidden = True  # Hidden by default (months view)
            else:
                # Other days - level 2
                ws.column_dimensions[col_letter].outlineLevel = 2
                ws.column_dimensions[col_letter].hidden = True  # Hidden by default (months view)
        
        # Configure outline settings - summary columns to the left (so collapse hides to the right)
        ws.sheet_properties.outlinePr.summaryBelow = False
        ws.sheet_properties.outlinePr.summaryRight = False
        
        # Set row heights
        ws.row_dimensions[2].height = 70  # Month row (vertical text needs more height)
        ws.row_dimensions[4].height = 20  # Day of week row (horizontal text)
        
        # Return the row index where data rows should start (row 6 is separator, row 7 is first data row)
        return 7
    
    def _create_data_rows(
        self, 
        ws, 
        engine_versions: List[EngineVersionData],
        start_date: date,
        end_date: date,
        start_row: int
    ) -> int:
        """Create the data rows for each engine-version combination.
        
        Creates one row per engine-version with:
        - Column A: Service name
        - Column B: Engine-Version label
        - Column C onwards: Date cells with color coding
        
        Fills cells with appropriate colors based on _get_cell_color.
        Freezes columns A-B and header rows.
        Adds row grouping by service.
        
        Args:
            ws: Worksheet to populate.
            engine_versions: List of engine-version data.
            start_date: First date in timeline.
            end_date: Last date in timeline.
            start_row: Row index to start data rows.
            
        Returns:
            Row index after last data row.
        """
        # Style definitions
        label_font = Font(bold=False)
        label_alignment = Alignment(horizontal="left", vertical="center")
        service_font = Font(bold=True)
        
        current_row = start_row
        current_service = None
        service_start_row = None
        
        # Create one row per engine-version
        for ev_data in engine_versions:
            # Track service grouping
            if ev_data.service != current_service:
                # Close previous service group if exists
                if current_service is not None and service_start_row is not None:
                    # Apply row grouping for previous service (all rows except first)
                    for row_idx in range(service_start_row + 1, current_row):
                        ws.row_dimensions[row_idx].outlineLevel = 1
                
                # Start new service group
                current_service = ev_data.service
                service_start_row = current_row
            
            # Column A: Service name
            service_cell = ws.cell(row=current_row, column=1, value=ev_data.service)
            service_cell.font = service_font
            service_cell.alignment = label_alignment
            
            # Column B: Engine-Version label
            label_cell = ws.cell(row=current_row, column=2, value=ev_data.display_name)
            label_cell.font = label_font
            label_cell.alignment = label_alignment
            
            # Fill cells for each date in the range
            current_date = start_date
            col_idx = 3  # Start from column C (A=Service, B=Engine-Version)
            
            while current_date <= end_date:
                # Determine if this date is a weekend (Saturday=5, Sunday=6)
                is_weekend = current_date.weekday() >= 5
                
                # Get the appropriate cell color based on support dates
                cell_color = self._get_cell_color(
                    current_date=current_date,
                    eos_date=ev_data.end_of_support,
                    ext_start=ev_data.extended_support_start,
                    ext_end=ev_data.extended_support_end,
                    is_weekend=is_weekend
                )
                
                # Apply fill color if one was determined
                if cell_color is not None:
                    cell = ws.cell(row=current_row, column=col_idx)
                    cell.fill = PatternFill(
                        start_color=cell_color,
                        end_color=cell_color,
                        fill_type="solid"
                    )
                
                # Move to next day
                current_date += timedelta(days=1)
                col_idx += 1
            
            # Move to next row
            current_row += 1
        
        # Close last service group
        if current_service is not None and service_start_row is not None:
            for row_idx in range(service_start_row + 1, current_row):
                ws.row_dimensions[row_idx].outlineLevel = 1
        
        # Freeze columns A-B and header rows
        # Freeze panes at C7 (row 7 is first data row, column C is first date column)
        # This freezes rows 1-6 (headers) and columns A-B (Service, Engine-Version)
        ws.freeze_panes = "C7"
        
        # Return the row index after the last data row
        return current_row
    
    def _create_legend(self, ws, start_row: int) -> None:
        """Create the color legend below the timeline.
        
        Adds legend section below data rows with color samples
        and descriptions for all states.
        
        Args:
            ws: Worksheet to populate.
            start_row: Row index to start legend.
        """
        # Style definitions
        title_font = Font(bold=True, size=12)
        label_font = Font(bold=False)
        label_alignment = Alignment(horizontal="left", vertical="center")
        
        # Leave an empty row for spacing
        current_row = start_row + 1
        
        # Legend title
        title_cell = ws.cell(row=current_row, column=1, value="Legend")
        title_cell.font = title_font
        current_row += 1
        
        # Define legend entries: (color_code, description)
        legend_entries = [
            (self.COLOR_EOS_EVENT, "End of Support Event"),
            (self.COLOR_EXT_START_EVENT, "Extended Support Start"),
            (self.COLOR_EXT_END_EVENT, "Extended Support End"),
            (self.COLOR_APPROACHING_EOS, "Approaching End of Support"),
            (self.COLOR_EXTENDED_SUPPORT, "Extended Support Period"),
            (self.COLOR_OUT_OF_SUPPORT, "Out of Support"),
            (self.COLOR_WEEKEND, "Weekend"),
            (self.COLOR_TODAY, "Today Marker"),
        ]
        
        # Create legend entries
        for color_code, description in legend_entries:
            # Column A: Color sample cell
            color_cell = ws.cell(row=current_row, column=1)
            
            # For the "Today Marker", use a border instead of fill
            if color_code == self.COLOR_TODAY:
                today_border = Border(
                    left=Side(style="medium", color=self.COLOR_TODAY),
                    right=Side(style="medium", color=self.COLOR_TODAY),
                    top=Side(style="medium", color=self.COLOR_TODAY),
                    bottom=Side(style="medium", color=self.COLOR_TODAY),
                )
                color_cell.border = today_border
            else:
                color_cell.fill = PatternFill(
                    start_color=color_code,
                    end_color=color_code,
                    fill_type="solid"
                )
            
            # Column B: Description
            desc_cell = ws.cell(row=current_row, column=2, value=description)
            desc_cell.font = label_font
            desc_cell.alignment = label_alignment
            
            current_row += 1
    
    def _get_cell_color(
        self, 
        current_date: date,
        eos_date: Optional[date],
        ext_start: Optional[date],
        ext_end: Optional[date],
        is_weekend: bool
    ) -> Optional[str]:
        """Determine the fill color for a timeline cell.
        
        Calculates cell color based on date relationship to EOS, ext_start, ext_end.
        Implements priority logic:
        - EOS event > ext_end event > ext_start event > out of support > 
          extended support > approaching EOS
        
        Args:
            current_date: The date this cell represents.
            eos_date: End of support date for this engine-version.
            ext_start: Extended support start date.
            ext_end: Extended support end date.
            is_weekend: Whether this date is a weekend.
            
        Returns:
            RGB hex color string or None.
        """
        # Priority 1: EOS event (exact date match)
        if eos_date is not None and current_date == eos_date:
            return self.COLOR_EOS_EVENT
        
        # Priority 2: Extended support end event (exact date match)
        if ext_end is not None and current_date == ext_end:
            return self.COLOR_EXT_END_EVENT
        
        # Priority 3: Extended support start event (exact date match)
        if ext_start is not None and current_date == ext_start:
            return self.COLOR_EXT_START_EVENT
        
        # Priority 4: Out of support (past EOS, no extended support covering this date)
        # A date is "out of support" if:
        # - It's after the EOS date, AND
        # - Either there's no extended support, OR the date is after ext_end
        if eos_date is not None and current_date > eos_date:
            # Check if extended support covers this date
            has_extended_support = (
                ext_start is not None and 
                ext_end is not None and 
                ext_start <= current_date <= ext_end
            )
            if not has_extended_support:
                return self.COLOR_OUT_OF_SUPPORT
        
        # Priority 5: Extended support period (between ext_start and ext_end)
        if (ext_start is not None and ext_end is not None and 
            ext_start <= current_date <= ext_end):
            return self.COLOR_EXTENDED_SUPPORT
        
        # Priority 6: Approaching EOS (within days_threshold before EOS)
        if eos_date is not None:
            days_until_eos = (eos_date - current_date).days
            if 0 < days_until_eos <= self.days_threshold:
                return self.COLOR_APPROACHING_EOS
        
        # Priority 7: Weekend (only if no other state applies)
        if is_weekend:
            return self.COLOR_WEEKEND
        
        # No special coloring needed
        return None


class BaseFormatter(ABC):
    """Abstract base class for report formatters."""
    
    @abstractmethod
    def format(self, report: Report) -> str:
        """Format the report as a string.
        
        Args:
            report: Report object to format.
            
        Returns:
            Formatted string representation of the report.
        """
        pass


class TextFormatter(BaseFormatter):
    """Formats report as human-readable text for console output.
    
    Produces hierarchical output with indentation showing the
    Account -> Service -> Engine -> Version structure.
    """
    
    def __init__(self, indent_size: int = 2):
        """Initialize formatter with configurable indentation.
        
        Args:
            indent_size: Number of spaces per indentation level.
        """
        self.indent_size = indent_size
    
    def format(self, report: Report) -> str:
        """Format report as human-readable text.
        
        Args:
            report: Report object to format.
            
        Returns:
            Formatted text string with hierarchical structure.
        """
        lines: List[str] = []
        
        # Header
        lines.append("=" * 80)
        lines.append(f"AWS Resource Support Status Report v{__version__}")
        lines.append(f"Generated: {report.generated_at.isoformat()}")
        
        # Generation parameters
        if report.generation_params:
            lines.append(f"Parameters: {report.generation_params.to_display_string()}")
        
        lines.append("=" * 80)
        lines.append("")
        
        # Summary section
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Resources: {report.total_resources}")
        lines.append("")
        lines.append("Status Breakdown:")
        for status in SupportStatus:
            count = report.total_counts.get(status, 0)
            lines.append(f"  {status.value}: {count}")
        lines.append("")
        
        # Detailed breakdown by account
        if report.accounts:
            lines.append("DETAILED BREAKDOWN")
            lines.append("-" * 40)
            lines.append("")
            
            for account_name, account_group in sorted(report.accounts.items()):
                lines.extend(self._format_account(account_group))
        
        return "\n".join(lines)
    
    def _format_account(self, account: AccountGroup) -> List[str]:
        """Format an account group with its services.
        
        Args:
            account: AccountGroup to format.
            
        Returns:
            List of formatted lines.
        """
        lines: List[str] = []
        indent = " " * self.indent_size
        
        lines.append(f"Account: {account.account}")
        lines.append(self._format_status_counts(account.status_counts, indent))
        
        for service_name, service_group in sorted(account.services.items()):
            lines.extend(self._format_service(service_group, 1))
        
        lines.append("")
        return lines
    
    def _format_service(self, service: ServiceGroup, level: int) -> List[str]:
        """Format a service group with its engines.
        
        Args:
            service: ServiceGroup to format.
            level: Indentation level.
            
        Returns:
            List of formatted lines.
        """
        lines: List[str] = []
        indent = " " * (self.indent_size * level)
        
        lines.append(f"{indent}Service: {service.service}")
        lines.append(self._format_status_counts(service.status_counts, indent + " " * self.indent_size))
        
        for engine_name, engine_group in sorted(service.engines.items()):
            lines.extend(self._format_engine(engine_group, level + 1))
        
        return lines
    
    def _format_engine(self, engine: EngineGroup, level: int) -> List[str]:
        """Format an engine group with its versions.
        
        Args:
            engine: EngineGroup to format.
            level: Indentation level.
            
        Returns:
            List of formatted lines.
        """
        lines: List[str] = []
        indent = " " * (self.indent_size * level)
        
        lines.append(f"{indent}Engine: {engine.engine}")
        lines.append(self._format_status_counts(engine.status_counts, indent + " " * self.indent_size))
        
        for version_name, version_group in sorted(engine.versions.items()):
            lines.extend(self._format_version(version_group, level + 1))
        
        return lines
    
    def _format_version(self, version: VersionGroup, level: int) -> List[str]:
        """Format a version group with its resources.
        
        Args:
            version: VersionGroup to format.
            level: Indentation level.
            
        Returns:
            List of formatted lines.
        """
        lines: List[str] = []
        indent = " " * (self.indent_size * level)
        resource_indent = " " * (self.indent_size * (level + 1))
        
        lines.append(f"{indent}Version: {version.version}")
        lines.append(self._format_status_counts(version.status_counts, indent + " " * self.indent_size))
        
        # List resources
        lines.append(f"{indent}Resources:")
        for resource in version.resources:
            lines.extend(self._format_resource(resource, resource_indent))
        
        return lines
    
    def _format_resource(self, resource: Resource, indent: str) -> List[str]:
        """Format a single resource with its details.
        
        Args:
            resource: Resource to format.
            indent: Indentation string.
            
        Returns:
            List of formatted lines.
        """
        lines: List[str] = []
        
        status_str = resource.status.value if resource.status else "Unknown"
        lines.append(f"{indent}- {resource.resource_name} [{status_str}]")
        lines.append(f"{indent}  ARN: {resource.resource_arn}")
        lines.append(f"{indent}  Region: {resource.region}")
        
        # End of Support date
        if resource.end_of_support:
            lines.append(f"{indent}  End of Support: {resource.end_of_support.isoformat()}")
        elif resource.end_of_support_raw:
            lines.append(f"{indent}  End of Support: {resource.end_of_support_raw}")
        
        # Days to EOS
        if resource.days_to_eos is not None:
            if resource.days_to_eos > 0:
                lines.append(f"{indent}  Days until EOS: {resource.days_to_eos}")
            elif resource.days_to_eos == 0:
                lines.append(f"{indent}  Days until EOS: Today")
            else:
                lines.append(f"{indent}  Days past EOS: {abs(resource.days_to_eos)}")
        
        # Extended support dates
        if resource.extended_support_start:
            lines.append(f"{indent}  Extended Support Start: {resource.extended_support_start.isoformat()}")
        if resource.extended_support_end:
            lines.append(f"{indent}  Extended Support End: {resource.extended_support_end.isoformat()}")
        
        # Extended support cost estimates (add * for Approaching EOS - future cost if not upgraded)
        # Don't show cost for Supported status (no extended support cost applies)
        if resource.est_monthly_ext_support_cost and resource.status != SupportStatus.SUPPORTED:
            monthly_cost = resource.est_monthly_ext_support_cost
            annual_cost = resource.est_annual_ext_support_cost or ""
            if resource.status == SupportStatus.APPROACHING_EOS:
                monthly_cost = f"{monthly_cost}*"
                annual_cost = f"{annual_cost}*" if annual_cost else ""
            lines.append(f"{indent}  Est. Monthly Cost: {monthly_cost}")
            if annual_cost:
                lines.append(f"{indent}  Est. Annual Cost: {annual_cost}")
        
        return lines
    
    def _format_status_counts(
        self, 
        counts: Dict[SupportStatus, int], 
        indent: str
    ) -> str:
        """Format status counts as a single line.
        
        Args:
            counts: Dictionary of status to count.
            indent: Indentation string.
            
        Returns:
            Formatted status counts string.
        """
        parts = []
        for status in SupportStatus:
            count = counts.get(status, 0)
            if count > 0:
                # Use abbreviated status names
                abbrev = self._status_abbreviation(status)
                parts.append(f"{abbrev}:{count}")
        
        if parts:
            return f"{indent}[{', '.join(parts)}]"
        return f"{indent}[No resources]"
    
    def _status_abbreviation(self, status: SupportStatus) -> str:
        """Get abbreviated status name.
        
        Args:
            status: SupportStatus enum value.
            
        Returns:
            Abbreviated status string.
        """
        abbreviations = {
            SupportStatus.SUPPORTED: "OK",
            SupportStatus.APPROACHING_EOS: "WARN",
            SupportStatus.EXTENDED_SUPPORT_YEAR_1: "EXT1",
            SupportStatus.EXTENDED_SUPPORT_YEAR_2: "EXT2",
            SupportStatus.EXTENDED_SUPPORT_YEAR_3: "EXT3",
            SupportStatus.OUT_OF_SUPPORT: "OOS",
        }
        return abbreviations.get(status, "?")



class CSVFormatter(BaseFormatter):
    """Formats report as CSV with flattened hierarchy.
    
    Each row represents a single resource with all its fields
    plus the computed status and grouping information.
    """
    
    # CSV column headers
    HEADERS = [
        "Account",
        "Service",
        "Engine",
        "Version",
        "Resource Name",
        "Resource ARN",
        "Region",
        "Resource Type",
        "Instance Type",
        "Status",
        "Days to EOS",
        "End of Support",
        "Extended Support Start",
        "Extended Support End",
        "Est. Monthly Cost",
        "Est. Annual Cost",
        "Insights",
    ]
    
    def format(self, report: Report) -> str:
        """Format report as CSV string.
        
        Flattens the hierarchical structure into rows, one per resource.
        
        Args:
            report: Report object to format.
            
        Returns:
            CSV formatted string.
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Write generation info as comment rows
        output.write(f"# AWS End-of-Support Report v{__version__}\n")
        output.write(f"# Generated: {report.generated_at.isoformat()}\n")
        if report.generation_params:
            output.write(f"# Parameters: {report.generation_params.to_display_string()}\n")
        output.write("#\n")
        
        # Write header row
        writer.writerow(self.HEADERS)
        
        # Write resource rows
        for account_name, account_group in sorted(report.accounts.items()):
            for service_name, service_group in sorted(account_group.services.items()):
                for engine_name, engine_group in sorted(service_group.engines.items()):
                    for version_name, version_group in sorted(engine_group.versions.items()):
                        for resource in version_group.resources:
                            writer.writerow(self._resource_to_row(resource))
        
        return output.getvalue()
    
    def _resource_to_row(self, resource: Resource) -> List[str]:
        """Convert a resource to a CSV row.
        
        Args:
            resource: Resource to convert.
            
        Returns:
            List of string values for the CSV row.
        """
        # Add star (*) to cost if status is Approaching EOS (future cost if not upgraded)
        # Don't show cost for Supported status (no extended support cost applies)
        monthly_cost = ""
        annual_cost = ""
        if resource.status != SupportStatus.SUPPORTED:
            monthly_cost = resource.est_monthly_ext_support_cost or ""
            annual_cost = resource.est_annual_ext_support_cost or ""
            if resource.status == SupportStatus.APPROACHING_EOS and monthly_cost:
                monthly_cost = f"{monthly_cost}*"
                annual_cost = f"{annual_cost}*" if annual_cost else ""
        
        return [
            resource.account,
            resource.service,
            resource.engine or "",
            resource.version,
            resource.resource_name,
            resource.resource_arn,
            resource.region,
            resource.resource_type,
            resource.instance_type or "",
            resource.status.value if resource.status else "",
            str(resource.days_to_eos) if resource.days_to_eos is not None else "",
            resource.end_of_support.isoformat() if resource.end_of_support else resource.end_of_support_raw,
            resource.extended_support_start.isoformat() if resource.extended_support_start else "",
            resource.extended_support_end.isoformat() if resource.extended_support_end else "",
            monthly_cost,
            annual_cost,
            resource.insights,
        ]



class JSONFormatter(BaseFormatter):
    """Formats report as JSON with nested hierarchical structure.
    
    Preserves the Account -> Service -> Engine -> Version hierarchy
    and includes all resource details and status counts.
    """
    
    def __init__(self, indent: int = 2):
        """Initialize formatter with configurable JSON indentation.
        
        Args:
            indent: Number of spaces for JSON indentation.
        """
        self.indent = indent
    
    def format(self, report: Report) -> str:
        """Format report as JSON string.
        
        Preserves hierarchical structure with all details.
        
        Args:
            report: Report object to format.
            
        Returns:
            JSON formatted string.
        """
        data = self._report_to_dict(report)
        return json.dumps(data, indent=self.indent, default=str)
    
    def _report_to_dict(self, report: Report) -> Dict[str, Any]:
        """Convert Report to dictionary for JSON serialization.
        
        Args:
            report: Report to convert.
            
        Returns:
            Dictionary representation of the report.
        """
        result = {
            "tool_version": __version__,
            "generated_at": report.generated_at.isoformat(),
            "total_resources": report.total_resources,
            "total_counts": self._status_counts_to_dict(report.total_counts),
            "accounts": {
                name: self._account_to_dict(group)
                for name, group in sorted(report.accounts.items())
            },
        }
        
        # Add generation parameters if available
        if report.generation_params:
            result["generation_parameters"] = {
                "input_file": report.generation_params.input_file,
                "output_format": report.generation_params.output_format,
                "days_threshold": report.generation_params.days_threshold,
                "status_filters": report.generation_params.status_filters,
                "account_filters": report.generation_params.account_filters,
                "service_filters": report.generation_params.service_filters,
            }
        
        return result
    
    def _account_to_dict(self, account: AccountGroup) -> Dict[str, Any]:
        """Convert AccountGroup to dictionary.
        
        Args:
            account: AccountGroup to convert.
            
        Returns:
            Dictionary representation.
        """
        return {
            "account": account.account,
            "status_counts": self._status_counts_to_dict(account.status_counts),
            "services": {
                name: self._service_to_dict(group)
                for name, group in sorted(account.services.items())
            },
        }
    
    def _service_to_dict(self, service: ServiceGroup) -> Dict[str, Any]:
        """Convert ServiceGroup to dictionary.
        
        Args:
            service: ServiceGroup to convert.
            
        Returns:
            Dictionary representation.
        """
        return {
            "service": service.service,
            "status_counts": self._status_counts_to_dict(service.status_counts),
            "engines": {
                name: self._engine_to_dict(group)
                for name, group in sorted(service.engines.items())
            },
        }
    
    def _engine_to_dict(self, engine: EngineGroup) -> Dict[str, Any]:
        """Convert EngineGroup to dictionary.
        
        Args:
            engine: EngineGroup to convert.
            
        Returns:
            Dictionary representation.
        """
        return {
            "engine": engine.engine,
            "status_counts": self._status_counts_to_dict(engine.status_counts),
            "versions": {
                name: self._version_to_dict(group)
                for name, group in sorted(engine.versions.items())
            },
        }
    
    def _version_to_dict(self, version: VersionGroup) -> Dict[str, Any]:
        """Convert VersionGroup to dictionary.
        
        Args:
            version: VersionGroup to convert.
            
        Returns:
            Dictionary representation.
        """
        return {
            "version": version.version,
            "status_counts": self._status_counts_to_dict(version.status_counts),
            "resources": [
                self._resource_to_dict(r) for r in version.resources
            ],
        }
    
    def _resource_to_dict(self, resource: Resource) -> Dict[str, Any]:
        """Convert Resource to dictionary.
        
        Args:
            resource: Resource to convert.
            
        Returns:
            Dictionary representation with all fields.
        """
        # Add star (*) to cost if status is Approaching EOS (future cost if not upgraded)
        # Don't show cost for Supported status (no extended support cost applies)
        monthly_cost = None
        annual_cost = None
        if resource.status != SupportStatus.SUPPORTED:
            monthly_cost = resource.est_monthly_ext_support_cost
            annual_cost = resource.est_annual_ext_support_cost
            if resource.status == SupportStatus.APPROACHING_EOS and monthly_cost:
                monthly_cost = f"{monthly_cost}*"
                annual_cost = f"{annual_cost}*" if annual_cost else None
        
        return {
            "account": resource.account,
            "payer_id": resource.payer_id,
            "service": resource.service,
            "resource_type": resource.resource_type,
            "resource_arn": resource.resource_arn,
            "resource_name": resource.resource_name,
            "region": resource.region,
            "engine": resource.engine,
            "version": resource.version,
            "instance_type": resource.instance_type,
            "end_of_support": resource.end_of_support.isoformat() if resource.end_of_support else None,
            "end_of_support_raw": resource.end_of_support_raw,
            "auto_minor_version_upgrade": resource.auto_minor_version_upgrade,
            "extended_support_start": resource.extended_support_start.isoformat() if resource.extended_support_start else None,
            "extended_support_year1_start": resource.extended_support_year1_start.isoformat() if resource.extended_support_year1_start else None,
            "extended_support_year3_start": resource.extended_support_year3_start.isoformat() if resource.extended_support_year3_start else None,
            "extended_support_end": resource.extended_support_end.isoformat() if resource.extended_support_end else None,
            "insights": resource.insights,
            "status": resource.status.value if resource.status else None,
            "days_to_eos": resource.days_to_eos,
            "est_monthly_ext_support_cost": monthly_cost,
            "est_annual_ext_support_cost": annual_cost,
        }
    
    def _status_counts_to_dict(self, counts: Dict[SupportStatus, int]) -> Dict[str, int]:
        """Convert status counts to dictionary with string keys.
        
        Args:
            counts: Dictionary with SupportStatus keys.
            
        Returns:
            Dictionary with string keys for JSON serialization.
        """
        return {
            status.value: counts.get(status, 0)
            for status in SupportStatus
        }


class ExcelFormatter(BaseFormatter):
    """Formats report as Excel file with styling and conditional formatting.
    
    Creates a professional Excel spreadsheet with:
    - Styled header row
    - Conditional formatting based on support status
    - Auto-adjusted column widths
    """
    
    # Column headers (same as CSV)
    HEADERS = [
        "Account",
        "Service",
        "Engine",
        "Version",
        "Resource Name",
        "Resource ARN",
        "Region",
        "Resource Type",
        "Instance Type",
        "Status",
        "Days to EOS",
        "End of Support",
        "Extended Support Start",
        "Extended Support End",
        "Est. Monthly Cost",
        "Est. Annual Cost",
        "Insights",
    ]
    
    # Status colors (RGB hex)
    STATUS_COLORS = {
        SupportStatus.SUPPORTED: "C6EFCE",              # Light green
        SupportStatus.APPROACHING_EOS: "FFEB9C",        # Light yellow/orange
        SupportStatus.EXTENDED_SUPPORT_YEAR_1: "BDD7EE", # Light blue
        SupportStatus.EXTENDED_SUPPORT_YEAR_2: "9DC3E6", # Medium blue
        SupportStatus.EXTENDED_SUPPORT_YEAR_3: "8DB4D8", # Darker blue
        SupportStatus.OUT_OF_SUPPORT: "FFC7CE",         # Light red
    }
    
    def __init__(self):
        """Initialize the Excel formatter."""
        if not EXCEL_AVAILABLE:
            raise ImportError(
                "Excel support requires openpyxl. Install with: pip install openpyxl"
            )
    
    def _is_file_locked(self, filepath: str) -> bool:
        """Check if a file is locked by another process.
        
        Args:
            filepath: Path to the file to check.
            
        Returns:
            True if the file is locked, False otherwise.
        """
        if not os.path.exists(filepath):
            return False
        try:
            with open(filepath, 'a'):
                pass
            return False
        except (IOError, PermissionError):
            return True
    
    def format(self, report: Report) -> str:
        """Not used for Excel - use format_to_file instead.
        
        Args:
            report: Report object to format.
            
        Returns:
            Empty string (Excel requires binary file output).
        """
        raise NotImplementedError(
            "ExcelFormatter requires format_to_file() for binary output"
        )
    
    def format_to_file(
        self, 
        report: Report, 
        filepath: str, 
        include_pivot: bool = True, 
        pivot_method: str = "auto", 
        pivot_per_account: bool = False,
        include_timeline: bool = True,
        days_threshold: int = 90,
        include_version_details: bool = False
    ) -> None:
        """Format report and save directly to Excel file.
        
        Args:
            report: Report object to format.
            filepath: Path to save the Excel file.
            include_pivot: Whether to include a pivot table/summary sheet.
            pivot_method: Method for creating pivot table:
                - "auto": Use Windows COM if available, otherwise template/summary
                - "windows": Force Windows COM (requires Excel installed)
                - "cross-platform": Force template-based or summary approach
            pivot_per_account: If True, create a separate pivot tab for each account.
            include_timeline: Whether to include the timeline visualization sheet.
            days_threshold: Days before EOS to mark as "approaching" in timeline.
            include_version_details: If True, create hidden tabs for each Service+Engine
                combination and add hyperlinks in the main report.
        """
        # Check if file is locked before starting
        if self._is_file_locked(filepath):
            raise IOError(f"Cannot write to '{filepath}' - file is open in another application. Please close it and try again.")
        
        wb = Workbook()
        
        # Determine headers based on version details option
        headers = list(self.HEADERS)
        if include_version_details:
            # Append "Version Details" at the end so pivot can exclude it
            headers.append("Version Details")
        
        # Create Table of Contents as first sheet
        toc_sheet = wb.active
        toc_sheet.title = "Table of Contents"
        
        # Create data sheet as second sheet
        ws = wb.create_sheet("Support Status Report")
        
        # Style definitions
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        
        # Write header row
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Freeze header row
        ws.freeze_panes = "A2"
        
        # Collect Service+Engine combinations for version detail sheets
        service_engine_map = {}  # (service, engine) -> sheet_name
        if include_version_details:
            service_engine_map = self._collect_service_engine_combinations(report)
        
        # Write data rows
        row_idx = 2
        for account_name, account_group in sorted(report.accounts.items()):
            for service_name, service_group in sorted(account_group.services.items()):
                for engine_name, engine_group in sorted(service_group.engines.items()):
                    for version_name, version_group in sorted(engine_group.versions.items()):
                        for resource in version_group.resources:
                            row_data = self._resource_to_row(resource)
                            status_fill = self._get_status_fill(resource.status)
                            
                            # If version details enabled, append the link column at the end
                            if include_version_details:
                                key = (service_name, engine_name or "")
                                sheet_name = service_engine_map.get(key, "")
                                row_data = list(row_data)
                                # Use HYPERLINK formula with meaningful text like "See Lambda_python tab"
                                if sheet_name:
                                    link_text = f"See {sheet_name} tab"
                                    hyperlink_formula = f'=HYPERLINK("#\'{sheet_name}\'!A1","{link_text}")'
                                    row_data.append(hyperlink_formula)
                                else:
                                    row_data.append("")
                            
                            for col_idx, value in enumerate(row_data, start=1):
                                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                                cell.border = thin_border
                                if status_fill:
                                    cell.fill = status_fill
                                
                                # Style the hyperlink formula column (last column when version details enabled)
                                if include_version_details and col_idx == len(row_data):
                                    cell.font = Font(color="0563C1", underline="single")
                            
                            row_idx += 1
        
        # Auto-adjust column widths
        self._auto_adjust_columns(ws, headers)
        
        # Add autofilter
        data_row_count = row_idx - 1
        if data_row_count > 1:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{data_row_count}"
        
        # Create pivot table/summary
        # Track sheet names for TOC
        sheet_info = [
            ("Table of Contents", "Index of all worksheets with navigation links"),
            ("Support Status Report", "Raw data with all resources and their support status"),
        ]
        
        if include_pivot:
            use_windows = (pivot_method == "windows") or (pivot_method == "auto" and WIN32COM_AVAILABLE)
            
            # For cross-platform with template, we need to handle pivot creation differently
            # to maintain correct sheet order
            if use_windows and WIN32COM_AVAILABLE:
                # Will be created via win32com after save - just add to TOC
                sheet_info.append(("Pivot", "Pivot table summary of all resources by Service/Engine/Version"))
                
                # Per-account pivots will also be created via win32com
                if pivot_per_account:
                    for account_name in sorted(report.accounts.keys()):
                        safe_account_name = account_name[:20].replace("/", "-").replace("\\", "-").replace(":", "-")
                        sheet_name = f"Pivot_{safe_account_name}"
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        sheet_info.append((sheet_name, f"Pivot table for account: {account_name}"))
            else:
                # Cross-platform: check if template exists for real pivot
                template_path = os.path.join(TEMPLATE_DIR, "pivot_template.xlsx")
                use_template = os.path.exists(template_path)
                
                if use_template:
                    # Template will be applied after save - just add to TOC
                    sheet_info.append(("Pivot", "Pivot table (refreshes when opened in Excel)"))
                else:
                    # No template - create styled summary
                    self._create_pivot_summary_sheet(wb, report)
                    sheet_info.append(("Pivot", "Summary of all resources by Service/Engine/Version"))
                
                # Per-account pivots - always styled summaries in cross-platform mode
                if pivot_per_account:
                    self._create_pivot_summary_per_account(wb, report)
                    for account_name in sorted(report.accounts.keys()):
                        safe_account_name = account_name[:20].replace("/", "-").replace("\\", "-").replace(":", "-")
                        sheet_name = f"Pivot_{safe_account_name}"
                        if len(sheet_name) > 31:
                            sheet_name = sheet_name[:31]
                        sheet_info.append((sheet_name, f"Summary for account: {account_name}"))
        
        # Create Timeline sheet if requested
        if include_timeline:
            timeline_ws = wb.create_sheet("Timeline")
            timeline_generator = TimelineGenerator(report, days_threshold)
            timeline_generator.generate(timeline_ws)
            sheet_info.append(("Timeline", "Visual timeline of support events by engine-version"))
        
        # Create version detail sheets if requested
        version_detail_sheets = []
        if include_version_details:
            version_detail_sheets = self._create_version_detail_sheets(wb, report, service_engine_map)
            for sheet_name, description in version_detail_sheets:
                sheet_info.append((sheet_name, description))
        
        # Populate Table of Contents
        self._create_table_of_contents(toc_sheet, sheet_info, report)
        
        # Save workbook first
        logger.info(f"Saving initial workbook to {filepath}")
        wb.save(filepath)
        logger.info(f"Initial workbook saved with sheets: {wb.sheetnames}")
        
        # Now handle pivot creation that requires post-save processing
        if include_pivot:
            # Need at least 2 rows (header + 1 data row) for pivot table
            if data_row_count < 2:
                logger.warning(f"Skipping pivot creation: not enough data rows ({data_row_count}). Need at least 2 rows (header + data).")
            else:
                use_windows = (pivot_method == "windows") or (pivot_method == "auto" and WIN32COM_AVAILABLE)
                logger.info(f"Pivot creation: include_pivot={include_pivot}, pivot_method={pivot_method}, use_windows={use_windows}, WIN32COM_AVAILABLE={WIN32COM_AVAILABLE}")
                
                # Include all columns in pivot source (including Version Details)
                # The Version Details column shows "See X tab" text which is meaningful in drill-down
                pivot_col_count = len(headers)
                
                pivot_created = False
                if use_windows and WIN32COM_AVAILABLE:
                    # Create real pivot tables with win32com
                    logger.info(f"Creating real pivot table with win32com: data_row_count={data_row_count}, col_count={pivot_col_count}")
                    try:
                        self._create_real_pivot_table_with_per_account(
                            filepath, report, data_row_count, pivot_per_account, days_threshold, 
                            pivot_col_count, None
                        )
                        pivot_created = True
                    except Exception as e:
                        logger.warning(f"Windows COM pivot creation failed: {e}. Falling back to cross-platform summary.")
                
                # Fallback to cross-platform if Windows COM failed or not available
                if not pivot_created:
                    # Re-open the workbook and add the summary sheet
                    logger.info("Creating cross-platform pivot summary as fallback")
                    from openpyxl import load_workbook
                    wb_fallback = load_workbook(filepath)
                    logger.info(f"Fallback: Loaded workbook with sheets: {wb_fallback.sheetnames}")
                    self._create_pivot_summary_sheet(wb_fallback, report)
                    if pivot_per_account:
                        self._create_pivot_summary_per_account(wb_fallback, report)
                    logger.info(f"Fallback: After adding pivot, sheets: {wb_fallback.sheetnames}")
                    wb_fallback.save(filepath)
                    wb_fallback.close()
                    logger.info("Cross-platform pivot summary created successfully")
        else:
            logger.info("Pivot creation skipped: include_pivot=False")
    
    def _create_pivot_summary_sheet(self, wb: Workbook, report: Report) -> None:
        """Create a styled pivot-like summary sheet (cross-platform).
        
        This creates a formatted summary that looks like a pivot table
        but works on all platforms without requiring Excel/win32com.
        
        Args:
            wb: Workbook to add the sheet to.
            report: Report object with hierarchical data.
        """
        # Insert Pivot sheet right after Support Status Report (index 1, since TOC is 0)
        ws = wb.create_sheet("Pivot", 2)
        
        # Style definitions
        filter_font = Font(bold=False)
        filter_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        service_font = Font(bold=True)
        service_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        engine_font = Font(bold=False)
        engine_fill = PatternFill(start_color="E9EDF4", end_color="E9EDF4", fill_type="solid")
        total_font_white = Font(bold=True, color="FFFFFF")
        total_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        
        # Write filter rows (like Excel pivot table filters)
        ws.cell(row=1, column=1, value="Account").font = filter_font
        ws.cell(row=1, column=1).fill = filter_fill
        ws.cell(row=1, column=2, value="(All)").font = filter_font
        ws.cell(row=1, column=2).fill = filter_fill
        
        ws.cell(row=2, column=1, value="Days to EOS").font = filter_font
        ws.cell(row=2, column=1).fill = filter_fill
        ws.cell(row=2, column=2, value="(All)").font = filter_font
        ws.cell(row=2, column=2).fill = filter_fill
        
        # Row 3: Empty row
        # Row 4: Header row
        ws.cell(row=4, column=1, value="Row Labels").font = header_font
        ws.cell(row=4, column=1).fill = header_fill
        ws.cell(row=4, column=2, value="Resources").font = header_font
        ws.cell(row=4, column=2).fill = header_fill
        
        # Aggregate data by Service → Engine → Version
        service_data: Dict[str, Dict[str, Dict[str, int]]] = {}
        
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                if service_name not in service_data:
                    service_data[service_name] = {}
                
                for engine_name, engine_group in service_group.engines.items():
                    display_engine = engine_name if engine_name and engine_name != "Unknown" else "(blank)"
                    
                    if display_engine not in service_data[service_name]:
                        service_data[service_name][display_engine] = {}
                    
                    for version_name, version_group in engine_group.versions.items():
                        resource_count = len(version_group.resources)
                        if version_name in service_data[service_name][display_engine]:
                            service_data[service_name][display_engine][version_name] += resource_count
                        else:
                            service_data[service_name][display_engine][version_name] = resource_count
        
        # Write pivot data (starting at row 5)
        row_idx = 5
        grand_total = 0
        
        for service_name in sorted(service_data.keys()):
            engines = service_data[service_name]
            service_total = sum(sum(versions.values()) for versions in engines.values())
            grand_total += service_total
            
            # Service row
            cell = ws.cell(row=row_idx, column=1, value=service_name)
            cell.font = service_font
            cell.fill = service_fill
            cell = ws.cell(row=row_idx, column=2, value=service_total)
            cell.font = service_font
            cell.fill = service_fill
            row_idx += 1
            
            for engine_name in sorted(engines.keys()):
                versions = engines[engine_name]
                engine_total = sum(versions.values())
                
                # Engine row (indented)
                cell = ws.cell(row=row_idx, column=1, value=f"    {engine_name}")
                cell.font = engine_font
                cell.fill = engine_fill
                cell = ws.cell(row=row_idx, column=2, value=engine_total)
                cell.font = engine_font
                cell.fill = engine_fill
                row_idx += 1
                
                for version_name in sorted(versions.keys()):
                    count = versions[version_name]
                    # Version row (more indented)
                    ws.cell(row=row_idx, column=1, value=f"        {version_name}")
                    ws.cell(row=row_idx, column=2, value=count)
                    row_idx += 1
        
        # Grand Total row
        cell = ws.cell(row=row_idx, column=1, value="Grand Total")
        cell.font = total_font_white
        cell.fill = total_fill
        cell = ws.cell(row=row_idx, column=2, value=grand_total)
        cell.font = total_font_white
        cell.fill = total_fill
        
        # Adjust column widths
        ws.column_dimensions["A"].width = 40
        ws.column_dimensions["B"].width = 12
        
        # Freeze after header row
        ws.freeze_panes = "A5"
    
    def _create_table_of_contents(self, ws, sheet_info: List[tuple], report: Report) -> None:
        """Create a Table of Contents sheet with links to all other sheets.
        
        Args:
            ws: Worksheet to populate with TOC.
            sheet_info: List of tuples (sheet_name, description).
            report: Report object with generation parameters.
        """
        # Style definitions
        title_font = Font(bold=True, size=16, color="4472C4")
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        link_font = Font(color="0563C1", underline="single")
        params_font = Font(italic=True, size=10, color="666666")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        
        # Title with version
        ws.cell(row=1, column=1, value=f"AWS End-of-Support Report v{__version__}").font = title_font
        ws.merge_cells("A1:C1")
        
        # Subtitle with generation info
        ws.cell(row=2, column=1, value="Table of Contents")
        ws.cell(row=2, column=1).font = Font(bold=True, size=12)
        
        # Generation parameters (row 3)
        params_row = 3
        if report.generation_params:
            params_str = report.generation_params.to_display_string()
            ws.cell(row=params_row, column=1, value=f"Parameters: {params_str}")
            ws.cell(row=params_row, column=1).font = params_font
            ws.merge_cells(f"A{params_row}:B{params_row}")
        
        # Header row (row 5)
        header_row = 5
        ws.cell(row=header_row, column=1, value="Sheet Name").font = header_font
        ws.cell(row=header_row, column=1).fill = header_fill
        ws.cell(row=header_row, column=1).border = thin_border
        
        ws.cell(row=header_row, column=2, value="Description").font = header_font
        ws.cell(row=header_row, column=2).fill = header_fill
        ws.cell(row=header_row, column=2).border = thin_border
        
        # Sheet entries
        row_idx = header_row + 1
        for sheet_name, description in sheet_info:
            # Sheet name with hyperlink
            cell = ws.cell(row=row_idx, column=1, value=sheet_name)
            cell.hyperlink = f"#'{sheet_name}'!A1"
            cell.font = link_font
            cell.border = thin_border
            
            # Description
            desc_cell = ws.cell(row=row_idx, column=2, value=description)
            desc_cell.border = thin_border
            
            row_idx += 1
        
        # Adjust column widths
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 60
        
        # Freeze header row (row 6 = A6)
        ws.freeze_panes = "A6"
    
    def _create_pivot_summary_per_account(self, wb: Workbook, report: Report) -> None:
        """Create a styled pivot-like summary sheet for each account.
        
        Args:
            wb: Workbook to add the sheets to.
            report: Report object with hierarchical data.
        """
        # Style definitions
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        service_font = Font(bold=True)
        service_fill = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")
        engine_font = Font(bold=False)
        engine_fill = PatternFill(start_color="E9EDF4", end_color="E9EDF4", fill_type="solid")
        total_font_white = Font(bold=True, color="FFFFFF")
        total_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        
        for account_name, account_group in sorted(report.accounts.items()):
            # Create sheet name (Excel limits to 31 chars)
            safe_account_name = account_name[:20].replace("/", "-").replace("\\", "-").replace(":", "-")
            sheet_name = f"Pivot_{safe_account_name}"
            if len(sheet_name) > 31:
                sheet_name = sheet_name[:31]
            
            ws = wb.create_sheet(sheet_name)
            
            # Header row
            ws.cell(row=1, column=1, value="Row Labels").font = header_font
            ws.cell(row=1, column=1).fill = header_fill
            ws.cell(row=1, column=2, value="Resources").font = header_font
            ws.cell(row=1, column=2).fill = header_fill
            
            # Aggregate data by Service → Engine → Version for this account
            service_data: Dict[str, Dict[str, Dict[str, int]]] = {}
            
            for service_name, service_group in account_group.services.items():
                if service_name not in service_data:
                    service_data[service_name] = {}
                
                for engine_name, engine_group in service_group.engines.items():
                    display_engine = engine_name if engine_name and engine_name != "Unknown" else "(blank)"
                    
                    if display_engine not in service_data[service_name]:
                        service_data[service_name][display_engine] = {}
                    
                    for version_name, version_group in engine_group.versions.items():
                        resource_count = len(version_group.resources)
                        if version_name in service_data[service_name][display_engine]:
                            service_data[service_name][display_engine][version_name] += resource_count
                        else:
                            service_data[service_name][display_engine][version_name] = resource_count
            
            # Write pivot data
            row_idx = 2
            grand_total = 0
            
            for service_name in sorted(service_data.keys()):
                engines = service_data[service_name]
                service_total = sum(sum(versions.values()) for versions in engines.values())
                grand_total += service_total
                
                # Service row
                cell = ws.cell(row=row_idx, column=1, value=service_name)
                cell.font = service_font
                cell.fill = service_fill
                cell = ws.cell(row=row_idx, column=2, value=service_total)
                cell.font = service_font
                cell.fill = service_fill
                row_idx += 1
                
                for engine_name in sorted(engines.keys()):
                    versions = engines[engine_name]
                    engine_total = sum(versions.values())
                    
                    # Engine row (indented)
                    cell = ws.cell(row=row_idx, column=1, value=f"    {engine_name}")
                    cell.font = engine_font
                    cell.fill = engine_fill
                    cell = ws.cell(row=row_idx, column=2, value=engine_total)
                    cell.font = engine_font
                    cell.fill = engine_fill
                    row_idx += 1
                    
                    for version_name in sorted(versions.keys()):
                        count = versions[version_name]
                        ws.cell(row=row_idx, column=1, value=f"        {version_name}")
                        ws.cell(row=row_idx, column=2, value=count)
                        row_idx += 1
            
            # Grand Total row
            cell = ws.cell(row=row_idx, column=1, value="Grand Total")
            cell.font = total_font_white
            cell.fill = total_fill
            cell = ws.cell(row=row_idx, column=2, value=grand_total)
            cell.font = total_font_white
            cell.fill = total_fill
            
            # Adjust column widths
            ws.column_dimensions["A"].width = 40
            ws.column_dimensions["B"].width = 12
            
            # Freeze header row
            ws.freeze_panes = "A2"
    
    def _create_pivot_tables_per_account_win32(self, filepath: str, report: Report, data_row_count: int) -> None:
        """Create real Excel PivotTables for each account using win32com.
        
        Args:
            filepath: Path to the Excel file.
            report: Report object with hierarchical data.
            data_row_count: Number of data rows in the source sheet.
        """
        import pythoncom
        pythoncom.CoInitialize()
        
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            abs_path = os.path.abspath(filepath)
            wb = excel.Workbooks.Open(abs_path)
            
            data_sheet = wb.Sheets("Support Status Report")
            last_col = get_column_letter(len(self.HEADERS))
            source_range = f"'Support Status Report'!A1:{last_col}{data_row_count}"
            
            # Create pivot cache once
            pivot_cache = wb.PivotCaches().Create(
                SourceType=1,  # xlDatabase
                SourceData=source_range
            )
            
            for account_name in sorted(report.accounts.keys()):
                # Create sheet name (Excel limits to 31 chars)
                safe_account_name = account_name[:20].replace("/", "-").replace("\\", "-").replace(":", "-")
                sheet_name = f"Pivot_{safe_account_name}"
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[:31]
                
                # Create a new sheet for this account's pivot
                pivot_sheet = wb.Sheets.Add(After=wb.Sheets(wb.Sheets.Count))
                pivot_sheet.Name = sheet_name
                
                # Create pivot table
                pivot_table = pivot_cache.CreatePivotTable(
                    TableDestination=pivot_sheet.Range("A4"),
                    TableName=f"Pivot_{safe_account_name}"
                )
                
                # Add row fields (Service -> Engine -> Version hierarchy)
                pivot_table.PivotFields("Service").Orientation = 1  # xlRowField
                pivot_table.PivotFields("Service").Position = 1
                
                pivot_table.PivotFields("Engine").Orientation = 1  # xlRowField
                pivot_table.PivotFields("Engine").Position = 2
                
                pivot_table.PivotFields("Version").Orientation = 1  # xlRowField
                pivot_table.PivotFields("Version").Position = 3
                
                # Add data field (count of resources)
                data_field = pivot_table.PivotFields("Resource Name")
                data_field.Orientation = 4  # xlDataField
                data_field.Function = -4112  # xlCount
                data_field.Name = "Resources"
                
                # Add page filter for Account and set to this account
                account_field = pivot_table.PivotFields("Account")
                account_field.Orientation = 3  # xlPageField
                account_field.CurrentPage = account_name
                
                # Add Days to EOS as page filter
                pivot_table.PivotFields("Days to EOS").Orientation = 3  # xlPageField
                
                # Apply pivot table style
                pivot_table.TableStyle2 = "PivotStyleMedium2"
            
            wb.Save()
            wb.Close()
            excel.Quit()
            
        except Exception as e:
            try:
                wb.Close(SaveChanges=False)
                excel.Quit()
            except:
                pass
            raise e
        finally:
            pythoncom.CoUninitialize()
    
    def _create_real_pivot_table_with_per_account(self, filepath: str, report: Report, data_row_count: int, pivot_per_account: bool, days_threshold: int = 90, col_count: int = None, service_engine_map: Dict[Tuple[str, str], str] = None) -> None:
        """Create real Excel PivotTables using win32com - main pivot and optionally per-account.
        
        Args:
            filepath: Path to the Excel file.
            report: Report object with hierarchical data.
            data_row_count: Number of data rows in the source sheet.
            pivot_per_account: Whether to also create per-account pivot tables.
            days_threshold: Days threshold for filtering "Days to EOS" (default 90).
            col_count: Number of columns in the data sheet (default: len(self.HEADERS)).
            service_engine_map: If provided, re-apply hyperlinks in "Version Details" column after save.
        """
        import pythoncom
        import time
        logger.info("Starting _create_real_pivot_table_with_per_account")
        pythoncom.CoInitialize()
        
        excel = None
        wb = None
        try:
            # Try to dispatch Excel with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"Dispatching Excel.Application (attempt {attempt + 1}/{max_retries})")
                    excel = win32com.client.Dispatch("Excel.Application")
                    excel.Visible = False
                    excel.DisplayAlerts = False
                    logger.info("Excel.Application dispatched successfully")
                    break
                except Exception as e:
                    logger.warning(f"Failed to dispatch Excel (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Wait before retry
                    else:
                        raise
            
            abs_path = os.path.abspath(filepath)
            logger.info(f"Opening workbook: {abs_path}")
            wb = excel.Workbooks.Open(abs_path)
            logger.info("Workbook opened successfully")
            
            # Use provided column count or default to HEADERS length
            actual_col_count = col_count if col_count else len(self.HEADERS)
            last_col = get_column_letter(actual_col_count)
            source_range = f"'Support Status Report'!A1:{last_col}{data_row_count}"
            logger.info(f"Source range for pivot: {source_range}")
            
            # Create pivot cache once
            logger.info("Creating pivot cache")
            pivot_cache = wb.PivotCaches().Create(
                SourceType=1,  # xlDatabase
                SourceData=source_range
            )
            
            # Create main Pivot sheet (insert after Support Status Report)
            logger.info("Creating Pivot sheet")
            data_sheet = wb.Sheets("Support Status Report")
            pivot_sheet = wb.Sheets.Add(After=data_sheet)
            pivot_sheet.Name = "Pivot"
            
            # Create main pivot table
            logger.info("Creating main pivot table")
            pivot_table = pivot_cache.CreatePivotTable(
                TableDestination=pivot_sheet.Range("A4"),
                TableName="SupportStatusPivot"
            )
            
            # Add row fields (Service -> Engine -> Version hierarchy)
            logger.info("Adding row fields to pivot table")
            pivot_table.PivotFields("Service").Orientation = 1  # xlRowField
            pivot_table.PivotFields("Service").Position = 1
            
            pivot_table.PivotFields("Engine").Orientation = 1  # xlRowField
            pivot_table.PivotFields("Engine").Position = 2
            
            pivot_table.PivotFields("Version").Orientation = 1  # xlRowField
            pivot_table.PivotFields("Version").Position = 3
            
            # Add data field (count of resources)
            logger.info("Adding data field to pivot table")
            data_field = pivot_table.PivotFields("Resource Name")
            data_field.Orientation = 4  # xlDataField
            data_field.Function = -4112  # xlCount
            data_field.Name = "Resources"
            
            # Add page filters (report filters)
            logger.info("Adding page filters to pivot table")
            days_to_eos_field = pivot_table.PivotFields("Days to EOS")
            days_to_eos_field.Orientation = 3  # xlPageField
            
            # Apply filter: show only items <= days_threshold
            try:
                days_to_eos_field.EnableMultiplePageItems = True
                for item in days_to_eos_field.PivotItems():
                    try:
                        item_value = item.Value
                        if item_value == "(blank)" or item_value == "" or item_value is None:
                            item.Visible = False
                        else:
                            try:
                                num_value = int(float(str(item_value)))
                                item.Visible = (num_value <= days_threshold)
                            except (ValueError, TypeError):
                                item.Visible = False
                    except:
                        pass
            except:
                pass
            
            pivot_table.PivotFields("Account").Orientation = 3  # xlPageField
            
            # Apply pivot table style
            pivot_table.TableStyle2 = "PivotStyleMedium2"
            
            # Create per-account pivot tables if requested
            if pivot_per_account:
                for account_name in sorted(report.accounts.keys()):
                    # Create sheet name (Excel limits to 31 chars)
                    safe_account_name = account_name[:20].replace("/", "-").replace("\\", "-").replace(":", "-")
                    sheet_name = f"Pivot_{safe_account_name}"
                    if len(sheet_name) > 31:
                        sheet_name = sheet_name[:31]
                    
                    # Create a new sheet for this account's pivot
                    account_pivot_sheet = wb.Sheets.Add(After=wb.Sheets(wb.Sheets.Count))
                    account_pivot_sheet.Name = sheet_name
                    
                    # Create pivot table
                    account_pivot_table = pivot_cache.CreatePivotTable(
                        TableDestination=account_pivot_sheet.Range("A4"),
                        TableName=f"Pivot_{safe_account_name}"
                    )
                    
                    # Add row fields (Service -> Engine -> Version hierarchy)
                    account_pivot_table.PivotFields("Service").Orientation = 1  # xlRowField
                    account_pivot_table.PivotFields("Service").Position = 1
                    
                    account_pivot_table.PivotFields("Engine").Orientation = 1  # xlRowField
                    account_pivot_table.PivotFields("Engine").Position = 2
                    
                    account_pivot_table.PivotFields("Version").Orientation = 1  # xlRowField
                    account_pivot_table.PivotFields("Version").Position = 3
                    
                    # Add data field (count of resources)
                    account_data_field = account_pivot_table.PivotFields("Resource Name")
                    account_data_field.Orientation = 4  # xlDataField
                    account_data_field.Function = -4112  # xlCount
                    account_data_field.Name = "Resources"
                    
                    # Add page filter for Account and set to this account
                    account_field = account_pivot_table.PivotFields("Account")
                    account_field.Orientation = 3  # xlPageField
                    account_field.CurrentPage = account_name
                    
                    # Add Days to EOS as page filter with threshold filter
                    account_days_field = account_pivot_table.PivotFields("Days to EOS")
                    account_days_field.Orientation = 3  # xlPageField
                    
                    # Apply filter: show only items <= days_threshold
                    try:
                        account_days_field.EnableMultiplePageItems = True
                        for item in account_days_field.PivotItems():
                            try:
                                item_value = item.Value
                                if item_value == "(blank)" or item_value == "" or item_value is None:
                                    item.Visible = False
                                else:
                                    try:
                                        num_value = int(float(str(item_value)))
                                        item.Visible = (num_value <= days_threshold)
                                    except (ValueError, TypeError):
                                        item.Visible = False
                            except:
                                pass
                    except:
                        pass
                    
                    # Apply pivot table style
                    account_pivot_table.TableStyle2 = "PivotStyleMedium2"
            
            # Note: Hyperlinks are not added when using win32com because:
            # 1. Adding 10,000+ hyperlinks via COM is too slow and causes disconnection
            # 2. The pivot table is the priority feature
            # Users who need hyperlinks can use cross-platform mode (no real pivot table)
            
            # Ensure Table of Contents is the first (leftmost) tab
            logger.info("Moving Table of Contents to first position")
            toc_sheet = wb.Sheets("Table of Contents")
            toc_sheet.Move(Before=wb.Sheets(1))
            
            # Log sheet names before save
            sheet_names = [wb.Sheets(i).Name for i in range(1, wb.Sheets.Count + 1)]
            logger.info(f"Sheets before save: {sheet_names}")
            
            logger.info("Saving workbook with pivot tables")
            wb.Save()
            logger.info("Workbook saved successfully")
            
            # Verify pivot sheet exists after save
            pivot_exists = any(wb.Sheets(i).Name == "Pivot" for i in range(1, wb.Sheets.Count + 1))
            logger.info(f"Pivot sheet exists after save: {pivot_exists}")
            
            logger.info("Closing workbook")
            wb.Close(SaveChanges=True)  # Explicitly save on close
            wb = None
            logger.info("Workbook closed")
            
            # Give Excel time to fully release the file
            time.sleep(0.5)
            
            logger.info("Quitting Excel")
            excel.Quit()
            excel = None
            
            # Force garbage collection to release COM objects
            import gc
            gc.collect()
            
            logger.info("Pivot table creation completed successfully")
            
            # Final verification: check file with openpyxl
            time.sleep(0.5)  # Give filesystem time to sync
            try:
                from openpyxl import load_workbook as verify_load
                verify_wb = verify_load(filepath, read_only=True)
                verify_sheets = verify_wb.sheetnames
                logger.info(f"Final verification - sheets in file: {verify_sheets}")
                verify_wb.close()
                if "Pivot" not in verify_sheets:
                    logger.error("CRITICAL: Pivot sheet missing after save!")
            except Exception as verify_error:
                logger.warning(f"Could not verify file: {verify_error}")
            
        except Exception as e:
            logger.error(f"Error creating pivot table: {e}", exc_info=True)
            try:
                if wb:
                    wb.Close(SaveChanges=False)
                if excel:
                    excel.Quit()
            except Exception as cleanup_error:
                logger.warning(f"Error during cleanup: {cleanup_error}")
            # Don't re-raise - allow file to be created without pivot
            logger.warning("Pivot table creation failed, file will be created without pivot sheet")
        finally:
            pythoncom.CoUninitialize()
    
    def _create_pivot_from_template(self, filepath: str, data_row_count: int, template_path: str, col_count: int = None) -> None:
        """Create a real pivot table by copying from a template file.
        
        This method loads a template Excel file that contains a pre-configured
        pivot table, copies the pivot sheet to the output file, and updates
        the pivot cache to reference the new data. The pivot will refresh
        when the file is opened in Excel.
        
        Args:
            filepath: Path to the output Excel file (already contains data).
            data_row_count: Number of data rows in the source sheet.
            template_path: Path to the template file with pre-configured pivot.
            col_count: Number of columns in the data sheet (default: len(self.HEADERS)).
        """
        from copy import copy
        
        # Use provided column count or default to HEADERS length
        actual_col_count = col_count if col_count else len(self.HEADERS)
        
        try:
            # Load the output workbook (with data)
            output_wb = load_workbook(filepath)
            
            # Load the template workbook
            template_wb = load_workbook(template_path)
            
            # Get the pivot sheet from template
            if "Pivot" not in template_wb.sheetnames:
                # Fallback if template doesn't have Pivot sheet
                output_wb.save(filepath)
                return
            
            template_pivot_sheet = template_wb["Pivot"]
            
            # Create a new Pivot sheet in output workbook at position 2 (after TOC and Support Status Report)
            output_pivot_sheet = output_wb.create_sheet("Pivot", 2)
            
            # Copy cell values and styles from template
            for row in template_pivot_sheet.iter_rows():
                for cell in row:
                    new_cell = output_pivot_sheet.cell(row=cell.row, column=cell.column, value=cell.value)
                    if cell.has_style:
                        new_cell.font = copy(cell.font)
                        new_cell.fill = copy(cell.fill)
                        new_cell.border = copy(cell.border)
                        new_cell.alignment = copy(cell.alignment)
                        new_cell.number_format = cell.number_format
            
            # Copy column dimensions
            for col_letter, col_dim in template_pivot_sheet.column_dimensions.items():
                output_pivot_sheet.column_dimensions[col_letter].width = col_dim.width
            
            # Copy row dimensions
            for row_num, row_dim in template_pivot_sheet.row_dimensions.items():
                output_pivot_sheet.row_dimensions[row_num].height = row_dim.height
            
            # Copy pivot tables from template
            if hasattr(template_pivot_sheet, '_pivots') and template_pivot_sheet._pivots:
                for pivot in template_pivot_sheet._pivots:
                    # Update the pivot cache source range to match our data
                    if pivot.cache and pivot.cache.cacheSource:
                        # Update source range to match our data
                        last_col = get_column_letter(actual_col_count)
                        
                        if pivot.cache.cacheSource.worksheetSource:
                            pivot.cache.cacheSource.worksheetSource.ref = f"A1:{last_col}{data_row_count}"
                            pivot.cache.cacheSource.worksheetSource.sheet = "Support Status Report"
                    
                    # Set pivot to refresh when file is opened
                    pivot.cache.refreshOnLoad = True
                    
                    # Add pivot to output sheet
                    output_pivot_sheet._pivots.append(pivot)
            
            # Save the output workbook
            output_wb.save(filepath)
            
        except Exception as e:
            # If template approach fails, the file still has the data sheet
            # Just save without pivot
            print(f"Warning: Could not create pivot from template: {e}")
            pass
    
    def _create_real_pivot_table(self, filepath: str, data_row_count: int) -> None:
        """Create a real Excel PivotTable using win32com.
        
        Args:
            filepath: Path to the Excel file.
            data_row_count: Number of data rows in the source sheet.
        """
        import pythoncom
        pythoncom.CoInitialize()
        
        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            # Open the workbook with absolute path
            abs_path = os.path.abspath(filepath)
            wb = excel.Workbooks.Open(abs_path)
            
            # Get the data sheet
            data_sheet = wb.Sheets("Support Status Report")
            
            # Create a new sheet for the pivot table
            pivot_sheet = wb.Sheets.Add(After=wb.Sheets(wb.Sheets.Count))
            pivot_sheet.Name = "Pivot"
            
            # Define the source data range
            last_col = get_column_letter(len(self.HEADERS))
            source_range = f"'Support Status Report'!A1:{last_col}{data_row_count}"
            
            # Create pivot cache
            pivot_cache = wb.PivotCaches().Create(
                SourceType=1,  # xlDatabase
                SourceData=source_range
            )
            
            # Create pivot table
            pivot_table = pivot_cache.CreatePivotTable(
                TableDestination=pivot_sheet.Range("A4"),
                TableName="SupportStatusPivot"
            )
            
            # Add row fields (Service -> Engine -> Version hierarchy)
            pivot_table.PivotFields("Service").Orientation = 1  # xlRowField
            pivot_table.PivotFields("Service").Position = 1
            
            pivot_table.PivotFields("Engine").Orientation = 1  # xlRowField
            pivot_table.PivotFields("Engine").Position = 2
            
            pivot_table.PivotFields("Version").Orientation = 1  # xlRowField
            pivot_table.PivotFields("Version").Position = 3
            
            # Add data field (count of resources)
            data_field = pivot_table.PivotFields("Resource Name")
            data_field.Orientation = 4  # xlDataField
            data_field.Function = -4112  # xlCount
            data_field.Name = "Resources"
            
            # Add page filters (report filters)
            pivot_table.PivotFields("Days to EOS").Orientation = 3  # xlPageField
            pivot_table.PivotFields("Account").Orientation = 3  # xlPageField
            
            # Apply pivot table style
            pivot_table.TableStyle2 = "PivotStyleMedium2"
            
            # Ensure Table of Contents is the first (leftmost) tab
            toc_sheet = wb.Sheets("Table of Contents")
            toc_sheet.Move(Before=wb.Sheets(1))
            
            # Save and close
            wb.Save()
            wb.Close()
            excel.Quit()
            
        except Exception as e:
            # If pivot creation fails, the file still has the data sheet
            try:
                wb.Close(SaveChanges=False)
                excel.Quit()
            except:
                pass
            raise e
        finally:
            pythoncom.CoUninitialize()
    
    def _resource_to_row(self, resource: Resource) -> List[Any]:
        """Convert a resource to a row of values.
        
        Args:
            resource: Resource to convert.
            
        Returns:
            List of values for the Excel row.
        """
        # Add star (*) to cost if status is Approaching EOS (future cost if not upgraded)
        # Don't show cost for Supported status (no extended support cost applies)
        monthly_cost = ""
        annual_cost = ""
        if resource.status != SupportStatus.SUPPORTED:
            monthly_cost = resource.est_monthly_ext_support_cost or ""
            annual_cost = resource.est_annual_ext_support_cost or ""
            if resource.status == SupportStatus.APPROACHING_EOS and monthly_cost:
                monthly_cost = f"{monthly_cost}*"
                annual_cost = f"{annual_cost}*" if annual_cost else ""
        
        return [
            resource.account,
            resource.service,
            resource.engine or "",
            resource.version,
            resource.resource_name,
            resource.resource_arn,
            resource.region,
            resource.resource_type,
            resource.instance_type or "",
            resource.status.value if resource.status else "",
            resource.days_to_eos if resource.days_to_eos is not None else "",
            resource.end_of_support.isoformat() if resource.end_of_support else resource.end_of_support_raw,
            resource.extended_support_start.isoformat() if resource.extended_support_start else "",
            resource.extended_support_end.isoformat() if resource.extended_support_end else "",
            monthly_cost,
            annual_cost,
            resource.insights,
        ]
    
    def _get_status_fill(self, status: Optional[SupportStatus]) -> Optional[PatternFill]:
        """Get the fill color for a status.
        
        Args:
            status: SupportStatus enum value.
            
        Returns:
            PatternFill for the status, or None if no status.
        """
        if status and status in self.STATUS_COLORS:
            color = self.STATUS_COLORS[status]
            return PatternFill(start_color=color, end_color=color, fill_type="solid")
        return None
    
    def _auto_adjust_columns(self, ws, headers: List[str] = None) -> None:
        """Auto-adjust column widths based on content.
        
        Args:
            ws: Worksheet to adjust.
            headers: List of header names (uses self.HEADERS if not provided).
        """
        if headers is None:
            headers = self.HEADERS
            
        for col_idx, header in enumerate(headers, start=1):
            max_length = len(header)
            column_letter = get_column_letter(col_idx)
            
            for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value:
                        cell_length = len(str(cell.value))
                        max_length = max(max_length, min(cell_length, 50))  # Cap at 50
            
            # Add some padding
            ws.column_dimensions[column_letter].width = max_length + 2
    
    def _collect_service_engine_combinations(self, report: Report) -> Dict[Tuple[str, str], str]:
        """Collect unique Service+Engine combinations and generate sheet names.
        
        Args:
            report: Report object with hierarchical data.
            
        Returns:
            Dictionary mapping (service, engine) tuples to sheet names.
        """
        combinations = set()
        
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                for engine_name, engine_group in service_group.engines.items():
                    combinations.add((service_name, engine_name or ""))
        
        # Generate unique sheet names (Excel limits to 31 chars)
        result = {}
        for service, engine in sorted(combinations):
            # Create a readable sheet name
            if engine and engine != "Unknown":
                base_name = f"{service}_{engine}"
            else:
                base_name = service
            
            # Sanitize for Excel sheet name (remove invalid chars)
            safe_name = base_name.replace("/", "-").replace("\\", "-").replace(":", "-")
            safe_name = safe_name.replace("*", "").replace("?", "").replace("[", "").replace("]", "")
            
            # Truncate to 31 chars (Excel limit)
            if len(safe_name) > 31:
                safe_name = safe_name[:31]
            
            # Ensure uniqueness
            final_name = safe_name
            counter = 1
            while final_name in [v for v in result.values()]:
                suffix = f"_{counter}"
                final_name = safe_name[:31 - len(suffix)] + suffix
                counter += 1
            
            result[(service, engine)] = final_name
        
        return result
    
    def _create_version_detail_sheets(
        self, 
        wb: Workbook, 
        report: Report, 
        service_engine_map: Dict[Tuple[str, str], str]
    ) -> List[Tuple[str, str]]:
        """Create hidden version detail sheets for each Service+Engine combination.
        
        Args:
            wb: Workbook to add sheets to.
            report: Report object with hierarchical data.
            service_engine_map: Mapping of (service, engine) to sheet names.
            
        Returns:
            List of (sheet_name, description) tuples for TOC.
        """
        # Style definitions
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        title_font = Font(bold=True, size=14, color="4472C4")
        back_link_font = Font(color="0563C1", underline="single")
        
        sheet_info = []
        
        # Aggregate data by (service, engine) -> versions -> resources
        aggregated_data: Dict[Tuple[str, str], Dict[str, List[Resource]]] = {}
        
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
        
        # Create a sheet for each Service+Engine combination
        for (service, engine), sheet_name in sorted(service_engine_map.items()):
            ws = wb.create_sheet(sheet_name)
            
            # Title row
            display_name = f"{service} - {engine}" if engine and engine != "Unknown" else service
            title_cell = ws.cell(row=1, column=1, value=display_name)
            title_cell.font = title_font
            ws.merge_cells("A1:F1")
            
            # Back link to main report
            back_cell = ws.cell(row=2, column=1, value="← Back to Support Status Report")
            back_cell.hyperlink = "#'Support Status Report'!A1"
            back_cell.font = back_link_font
            
            # Version detail headers (row 4)
            detail_headers = ["Version", "Resource Count", "End of Support", "Extended Support Start", 
                            "Extended Support End", "Status Summary"]
            for col_idx, header in enumerate(detail_headers, start=1):
                cell = ws.cell(row=4, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
            
            # Get version data for this service+engine
            versions_data = aggregated_data.get((service, engine), {})
            
            # Write version rows
            row_idx = 5
            for version_name in sorted(versions_data.keys()):
                resources = versions_data[version_name]
                
                # Aggregate data for this version
                resource_count = len(resources)
                eos_dates = [r.end_of_support for r in resources if r.end_of_support]
                ext_start_dates = [r.extended_support_start for r in resources if r.extended_support_start]
                ext_end_dates = [r.extended_support_end for r in resources if r.extended_support_end]
                
                # Get earliest/latest dates
                eos_date = min(eos_dates).isoformat() if eos_dates else ""
                ext_start = min(ext_start_dates).isoformat() if ext_start_dates else ""
                ext_end = max(ext_end_dates).isoformat() if ext_end_dates else ""
                
                # Status summary
                status_counts = {}
                for r in resources:
                    if r.status:
                        status_counts[r.status.value] = status_counts.get(r.status.value, 0) + 1
                status_summary = ", ".join([f"{k}: {v}" for k, v in sorted(status_counts.items())])
                
                # Write row
                row_data = [version_name, resource_count, eos_date, ext_start, ext_end, status_summary]
                for col_idx, value in enumerate(row_data, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = thin_border
                
                row_idx += 1
            
            # Auto-adjust column widths
            for col_idx, header in enumerate(detail_headers, start=1):
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = max(len(header) + 2, 15)
            
            # Freeze header row
            ws.freeze_panes = "A5"
            
            # Set tab color to blue (visible tabs)
            ws.sheet_properties.tabColor = "0563C1"
            
            # Add to sheet info
            description = f"Version details for {display_name}"
            sheet_info.append((sheet_name, description))
        
        return sheet_info

    def _reapply_version_detail_hyperlinks(
        self, 
        filepath: str, 
        report: Report, 
        service_engine_map: Dict[Tuple[str, str], str]
    ) -> None:
        """Re-apply hyperlinks in the 'Version Details' column after win32com processing.
        
        Win32com strips openpyxl hyperlinks when it saves the file. This method
        uses win32com to re-apply the hyperlinks to preserve the pivot tables.
        
        Args:
            filepath: Path to the Excel file.
            report: Report object with hierarchical data.
            service_engine_map: Mapping of (service, engine) to sheet names.
        """
        import pythoncom
        pythoncom.CoInitialize()
        
        excel = None
        wb = None
        try:
            logger.info("Re-applying hyperlinks using win32com")
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            abs_path = os.path.abspath(filepath)
            wb = excel.Workbooks.Open(abs_path)
            
            self._add_hyperlinks_win32com_optimized(wb, report, service_engine_map)
            
            wb.Save()
            wb.Close()
            wb = None
            excel.Quit()
            excel = None
            logger.info("Hyperlinks re-applied successfully")
            
        except Exception as e:
            logger.error(f"Error re-applying hyperlinks: {e}", exc_info=True)
            try:
                if wb:
                    wb.Close(SaveChanges=False)
                if excel:
                    excel.Quit()
            except:
                pass
            raise e
        finally:
            pythoncom.CoUninitialize()

    def _add_hyperlinks_win32com(
        self,
        wb,
        report: Report,
        service_engine_map: Dict[Tuple[str, str], str]
    ) -> None:
        """Add hyperlinks to the 'Version Details' column using win32com.
        
        Args:
            wb: Win32com workbook object.
            report: Report object with hierarchical data.
            service_engine_map: Mapping of (service, engine) to sheet names.
        """
        ws = wb.Sheets("Support Status Report")
        
        # Iterate through data rows and add hyperlinks in column 5 (Version Details)
        row_idx = 2  # Start after header
        for account_name, account_group in sorted(report.accounts.items()):
            for service_name, service_group in sorted(account_group.services.items()):
                for engine_name, engine_group in sorted(service_group.engines.items()):
                    for version_name, version_group in sorted(engine_group.versions.items()):
                        for resource in version_group.resources:
                            key = (service_name, engine_name or "")
                            sheet_name = service_engine_map.get(key, "")
                            if sheet_name:
                                cell = ws.Cells(row_idx, 5)
                                # Add hyperlink to the cell
                                ws.Hyperlinks.Add(
                                    Anchor=cell,
                                    Address="",
                                    SubAddress=f"'{sheet_name}'!A1",
                                    TextToDisplay="View Details"
                                )
                            row_idx += 1
        
        logger.info(f"Added hyperlinks to {row_idx - 2} rows")

    def _add_hyperlinks_win32com_optimized(
        self,
        wb,
        report: Report,
        service_engine_map: Dict[Tuple[str, str], str]
    ) -> None:
        """Add hyperlinks using HYPERLINK formula for better performance.
        
        This method uses Excel's HYPERLINK formula instead of actual hyperlinks,
        which is much faster for large datasets.
        
        Args:
            wb: Win32com workbook object.
            report: Report object with hierarchical data.
            service_engine_map: Mapping of (service, engine) to sheet names.
        """
        ws = wb.Sheets("Support Status Report")
        
        # Build a list of formulas to apply
        formulas = []
        row_idx = 2  # Start after header
        for account_name, account_group in sorted(report.accounts.items()):
            for service_name, service_group in sorted(account_group.services.items()):
                for engine_name, engine_group in sorted(service_group.engines.items()):
                    for version_name, version_group in sorted(engine_group.versions.items()):
                        for resource in version_group.resources:
                            key = (service_name, engine_name or "")
                            sheet_name = service_engine_map.get(key, "")
                            if sheet_name:
                                # Use HYPERLINK formula
                                formula = f'=HYPERLINK("#\'{sheet_name}\'!A1","View Details")'
                                formulas.append((row_idx, formula))
                            row_idx += 1
        
        # Apply formulas in batches for better performance
        logger.info(f"Applying {len(formulas)} hyperlink formulas")
        
        # Disable screen updating for performance
        wb.Application.ScreenUpdating = False
        wb.Application.Calculation = -4135  # xlCalculationManual
        
        try:
            for row, formula in formulas:
                ws.Cells(row, 5).Formula = formula
        finally:
            wb.Application.Calculation = -4105  # xlCalculationAutomatic
            wb.Application.ScreenUpdating = True
        
        logger.info(f"Applied hyperlink formulas to {len(formulas)} rows")
