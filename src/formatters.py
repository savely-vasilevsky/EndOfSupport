"""Output formatters for EndOfSupportTool.

Provides TextFormatter, CSVFormatter, JSONFormatter, and ExcelFormatter for generating
reports in different output formats.
"""

import csv
import json
import os
from abc import ABC, abstractmethod
from datetime import date
from io import StringIO
from typing import Any, Dict, List, Optional

from .models import (
    Report,
    Resource,
    SupportStatus,
    AccountGroup,
    ServiceGroup,
    EngineGroup,
    VersionGroup,
)

# Optional Excel support
try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

# Optional win32com support for real pivot tables (Windows only)
try:
    import win32com.client
    WIN32COM_AVAILABLE = True
except ImportError:
    WIN32COM_AVAILABLE = False


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
        lines.append("AWS Resource Support Status Report")
        lines.append(f"Generated: {report.generated_at.isoformat()}")
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
            SupportStatus.EXTENDED_SUPPORT: "EXT",
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
        "Status",
        "Days to EOS",
        "End of Support",
        "Extended Support Start",
        "Extended Support End",
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
        return [
            resource.account,
            resource.service,
            resource.engine or "",
            resource.version,
            resource.resource_name,
            resource.resource_arn,
            resource.region,
            resource.resource_type,
            resource.status.value if resource.status else "",
            str(resource.days_to_eos) if resource.days_to_eos is not None else "",
            resource.end_of_support.isoformat() if resource.end_of_support else resource.end_of_support_raw,
            resource.extended_support_start.isoformat() if resource.extended_support_start else "",
            resource.extended_support_end.isoformat() if resource.extended_support_end else "",
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
        return {
            "generated_at": report.generated_at.isoformat(),
            "total_resources": report.total_resources,
            "total_counts": self._status_counts_to_dict(report.total_counts),
            "accounts": {
                name: self._account_to_dict(group)
                for name, group in sorted(report.accounts.items())
            },
        }
    
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
        "Status",
        "Days to EOS",
        "End of Support",
        "Extended Support Start",
        "Extended Support End",
        "Insights",
    ]
    
    # Status colors (RGB hex)
    STATUS_COLORS = {
        SupportStatus.SUPPORTED: "C6EFCE",        # Light green
        SupportStatus.APPROACHING_EOS: "FFEB9C",  # Light yellow/orange
        SupportStatus.EXTENDED_SUPPORT: "BDD7EE", # Light blue
        SupportStatus.OUT_OF_SUPPORT: "FFC7CE",   # Light red
    }
    
    def __init__(self):
        """Initialize the Excel formatter."""
        if not EXCEL_AVAILABLE:
            raise ImportError(
                "Excel support requires openpyxl. Install with: pip install openpyxl"
            )
    
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
    
    def format_to_file(self, report: Report, filepath: str) -> None:
        """Format report and save directly to Excel file.
        
        Args:
            report: Report object to format.
            filepath: Path to save the Excel file.
        """
        wb = Workbook()
        ws = wb.active
        ws.title = "Support Status Report"
        
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
        for col_idx, header in enumerate(self.HEADERS, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Freeze header row
        ws.freeze_panes = "A2"
        
        # Write data rows
        row_idx = 2
        for account_name, account_group in sorted(report.accounts.items()):
            for service_name, service_group in sorted(account_group.services.items()):
                for engine_name, engine_group in sorted(service_group.engines.items()):
                    for version_name, version_group in sorted(engine_group.versions.items()):
                        for resource in version_group.resources:
                            row_data = self._resource_to_row(resource)
                            status_fill = self._get_status_fill(resource.status)
                            
                            for col_idx, value in enumerate(row_data, start=1):
                                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                                cell.border = thin_border
                                if status_fill:
                                    cell.fill = status_fill
                            
                            row_idx += 1
        
        # Auto-adjust column widths
        self._auto_adjust_columns(ws)
        
        # Add autofilter
        data_row_count = row_idx - 1
        if data_row_count > 1:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(self.HEADERS))}{data_row_count}"
        
        # Save workbook first (without pivot)
        wb.save(filepath)
        
        # Create real pivot table using win32com (Windows only)
        if WIN32COM_AVAILABLE:
            self._create_real_pivot_table(filepath, data_row_count)
    
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
        return [
            resource.account,
            resource.service,
            resource.engine or "",
            resource.version,
            resource.resource_name,
            resource.resource_arn,
            resource.region,
            resource.resource_type,
            resource.status.value if resource.status else "",
            resource.days_to_eos if resource.days_to_eos is not None else "",
            resource.end_of_support.isoformat() if resource.end_of_support else resource.end_of_support_raw,
            resource.extended_support_start.isoformat() if resource.extended_support_start else "",
            resource.extended_support_end.isoformat() if resource.extended_support_end else "",
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
    
    def _auto_adjust_columns(self, ws) -> None:
        """Auto-adjust column widths based on content.
        
        Args:
            ws: Worksheet to adjust.
        """
        for col_idx, header in enumerate(self.HEADERS, start=1):
            max_length = len(header)
            column_letter = get_column_letter(col_idx)
            
            for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx):
                for cell in row:
                    if cell.value:
                        cell_length = len(str(cell.value))
                        max_length = max(max_length, min(cell_length, 50))  # Cap at 50
            
            # Add some padding
            ws.column_dimensions[column_letter].width = max_length + 2
