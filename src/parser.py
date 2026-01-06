"""CSV Parser for EndOfSupportTool.

Parses AWS resource inventory CSV files into structured Resource objects.
"""

import csv
import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from .models import Resource


logger = logging.getLogger(__name__)


class CSVParseError(Exception):
    """Exception raised when CSV parsing fails due to structural issues."""
    pass


class DateParseError(Exception):
    """Exception raised when date parsing fails."""
    pass


class CSVParser:
    """Parser for AWS resource inventory CSV files.
    
    Reads CSV files exported from AWS inventory tools and converts
    rows into structured Resource objects.
    """
    
    # Required columns that must be present in the CSV
    REQUIRED_COLUMNS = {
        'Account',
        'Payer ID',
        'Service',
        'Resource Type',
        'Resource ARN',
        'Resource Name',
        'Regions / AZs',
        'Version',
        'End-of-Support',
        'Insights',
    }
    
    # Column name mappings from CSV headers to Resource field names
    COLUMN_MAPPING = {
        'Account': 'account',
        'Payer ID': 'payer_id',
        'Service': 'service',
        'Resource Type': 'resource_type',
        'Resource ARN': 'resource_arn',
        'Resource Name': 'resource_name',
        'Regions / AZs': 'region',
        'Engine': 'engine',
        'Version': 'version',
        'End-of-Support': 'end_of_support_raw',
        'Auto Minor Version Upgrade': 'auto_minor_version_upgrade',
        'Extended Support - Start Date': 'extended_support_start',
        'Extended Support - Year 1 Pricing Start Date': 'extended_support_year1_start',
        'Extended Support - Year 3 Pricing Start Date': 'extended_support_year3_start',
        'Extended Support - End Date': 'extended_support_end',
        'Insights': 'insights',
    }

    def __init__(self, file_path: str):
        """Initialize parser with the CSV file path.
        
        Args:
            file_path: Path to the CSV file to parse.
        """
        self.file_path = Path(file_path)
    
    def parse(self) -> List[Resource]:
        """Parse the CSV file and return a list of Resource objects.
        
        Returns:
            List of Resource objects parsed from the CSV.
            
        Raises:
            FileNotFoundError: If the CSV file does not exist.
            PermissionError: If the CSV file cannot be read.
            CSVParseError: If required columns are missing or file is empty.
        """
        # Check file exists
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")
        
        # Check file is readable
        if not self.file_path.is_file():
            raise CSVParseError(f"Path is not a file: {self.file_path}")
        
        resources: List[Resource] = []
        
        try:
            with open(self.file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                
                # Validate headers
                if reader.fieldnames is None:
                    raise CSVParseError(f"CSV file is empty or contains only headers: {self.file_path}")
                
                headers = set(reader.fieldnames)
                missing_columns = self.REQUIRED_COLUMNS - headers
                
                if missing_columns:
                    raise CSVParseError(f"Missing required columns: {', '.join(sorted(missing_columns))}")
                
                # Parse rows
                row_count = 0
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                    row_count += 1
                    resource = self._parse_row(row, row_num)
                    resources.append(resource)
                
                if row_count == 0:
                    raise CSVParseError(f"CSV file is empty or contains only headers: {self.file_path}")
                    
        except PermissionError:
            raise PermissionError(f"Cannot read CSV file: {self.file_path}")
        
        return resources

    def _parse_row(self, row: dict, row_num: int) -> Resource:
        """Parse a single CSV row into a Resource object.
        
        Args:
            row: Dictionary of column name to value from CSV.
            row_num: Row number for error reporting.
            
        Returns:
            Resource object populated from the row data.
        """
        # Extract basic string fields
        account = row.get('Account', '').strip()
        payer_id = row.get('Payer ID', '').strip()
        service = row.get('Service', '').strip()
        resource_type = row.get('Resource Type', '').strip()
        resource_arn = row.get('Resource ARN', '').strip()
        resource_name = row.get('Resource Name', '').strip()
        region = row.get('Regions / AZs', '').strip()
        engine = row.get('Engine', '').strip() or None
        version = row.get('Version', '').strip()
        end_of_support_raw = row.get('End-of-Support', '').strip()
        insights = row.get('Insights', '').strip()
        
        # Handle engine field - convert "-" to None
        if engine == '-':
            engine = None
        
        # Parse date fields
        end_of_support = self._parse_date(end_of_support_raw, row_num, 'End-of-Support')
        
        extended_support_start = self._parse_date(
            row.get('Extended Support - Start Date', '').strip(),
            row_num, 'Extended Support - Start Date'
        )
        extended_support_year1_start = self._parse_date(
            row.get('Extended Support - Year 1 Pricing Start Date', '').strip(),
            row_num, 'Extended Support - Year 1 Pricing Start Date'
        )
        extended_support_year3_start = self._parse_date(
            row.get('Extended Support - Year 3 Pricing Start Date', '').strip(),
            row_num, 'Extended Support - Year 3 Pricing Start Date'
        )
        extended_support_end = self._parse_date(
            row.get('Extended Support - End Date', '').strip(),
            row_num, 'Extended Support - End Date'
        )
        
        # Parse boolean field
        auto_minor_version_upgrade = self._parse_bool(
            row.get('Auto Minor Version Upgrade', '').strip()
        )
        
        return Resource(
            account=account,
            payer_id=payer_id,
            service=service,
            resource_type=resource_type,
            resource_arn=resource_arn,
            resource_name=resource_name,
            region=region,
            engine=engine,
            version=version,
            end_of_support=end_of_support,
            end_of_support_raw=end_of_support_raw,
            auto_minor_version_upgrade=auto_minor_version_upgrade,
            extended_support_start=extended_support_start,
            extended_support_year1_start=extended_support_year1_start,
            extended_support_year3_start=extended_support_year3_start,
            extended_support_end=extended_support_end,
            insights=insights,
        )

    def _parse_date(self, date_str: str, row_num: int, field_name: str) -> Optional[date]:
        """Parse various date formats from the CSV.
        
        Handles formats:
        - DD-MMM-YY (e.g., "15-Dec-25", "31-Jan-27")
        - MMM-YY (e.g., "Dec-25")
        - Special values: "Deprecated", "Supported", "Not available", "-", ""
        
        Args:
            date_str: The date string to parse.
            row_num: Row number for error reporting.
            field_name: Field name for error reporting.
            
        Returns:
            Parsed date object, or None for non-date values.
        """
        if not date_str:
            return None
        
        # Handle special non-date values
        special_values = {
            'deprecated', 'supported', 'not available', '-', ''
        }
        if date_str.lower() in special_values:
            return None
        
        # Try DD-MMM-YY format (e.g., "15-Dec-25")
        try:
            parsed = datetime.strptime(date_str, '%d-%b-%y')
            return parsed.date()
        except ValueError:
            pass
        
        # Try MMM-YY format (e.g., "Dec-25") - use first day of month
        try:
            parsed = datetime.strptime(date_str, '%b-%y')
            return parsed.date()
        except ValueError:
            pass
        
        # Try D-MMM-YY format (e.g., "5-Mar-20")
        try:
            parsed = datetime.strptime(date_str, '%d-%b-%y')
            return parsed.date()
        except ValueError:
            pass
        
        # Log warning for unparseable dates
        logger.warning(
            f"Invalid date format in row {row_num}, field '{field_name}': {date_str}"
        )
        return None
    
    def _parse_bool(self, value: str) -> Optional[bool]:
        """Parse boolean values from CSV.
        
        Args:
            value: String value to parse.
            
        Returns:
            True, False, or None for empty/unknown values.
        """
        if not value or value == '-':
            return None
        
        return value.upper() in ('TRUE', 'YES', '1')
