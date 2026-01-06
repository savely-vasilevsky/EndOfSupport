"""Tests for CSV Parser.

Tests cover error handling and basic parsing functionality.
"""

import csv
import os
import tempfile
from datetime import date

import pytest

from src.parser import CSVParser, CSVParseError


class TestCSVParserErrorHandling:
    """Tests for CSV parser error handling (Requirements 1.3, 1.4)."""
    
    def test_file_not_found_raises_error(self):
        """Test that FileNotFoundError is raised for missing files."""
        parser = CSVParser('nonexistent_file.csv')
        
        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse()
        
        assert 'nonexistent_file.csv' in str(exc_info.value)
    
    def test_missing_required_columns_raises_error(self):
        """Test that CSVParseError is raised when required columns are missing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['Account', 'Service'])  # Missing many required columns
            writer.writerow(['TestAccount', 'Lambda'])
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            
            with pytest.raises(CSVParseError) as exc_info:
                parser.parse()
            
            error_msg = str(exc_info.value)
            assert 'Missing required columns' in error_msg
            # Check that some missing columns are mentioned
            assert 'Resource ARN' in error_msg or 'Version' in error_msg
        finally:
            os.unlink(temp_path)
    
    def test_empty_file_raises_error(self):
        """Test that CSVParseError is raised for empty files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            # Write only headers, no data rows
            writer = csv.writer(f)
            writer.writerow([
                'Account', 'Payer ID', 'Service', 'Resource Type', 
                'Resource ARN', 'Resource Name', 'Regions / AZs',
                'Version', 'End-of-Support', 'Insights'
            ])
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            
            with pytest.raises(CSVParseError) as exc_info:
                parser.parse()
            
            assert 'empty' in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)


class TestCSVParserDateParsing:
    """Tests for date parsing functionality (Requirement 1.5)."""
    
    def test_parse_dd_mmm_yy_format(self):
        """Test parsing DD-MMM-YY date format."""
        parser = CSVParser('dummy.csv')
        
        result = parser._parse_date('15-Dec-25', 1, 'test')
        assert result == date(2025, 12, 15)
        
        result = parser._parse_date('31-Jan-27', 1, 'test')
        assert result == date(2027, 1, 31)
        
        result = parser._parse_date('5-Mar-20', 1, 'test')
        assert result == date(2020, 3, 5)
    
    def test_parse_special_values_return_none(self):
        """Test that special values return None."""
        parser = CSVParser('dummy.csv')
        
        assert parser._parse_date('Deprecated', 1, 'test') is None
        assert parser._parse_date('Supported', 1, 'test') is None
        assert parser._parse_date('Not available', 1, 'test') is None
        assert parser._parse_date('-', 1, 'test') is None
        assert parser._parse_date('', 1, 'test') is None
    
    def test_parse_invalid_date_returns_none_with_warning(self, caplog):
        """Test that invalid dates return None and log a warning."""
        import logging
        
        parser = CSVParser('dummy.csv')
        
        with caplog.at_level(logging.WARNING):
            result = parser._parse_date('invalid-date', 5, 'End-of-Support')
        
        assert result is None
        assert 'Invalid date format' in caplog.text
        assert 'row 5' in caplog.text


class TestCSVParserBasicParsing:
    """Tests for basic CSV parsing functionality (Requirements 1.1, 1.2)."""
    
    def test_parse_valid_csv_returns_resources(self):
        """Test that a valid CSV file is parsed into Resource objects."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Account', 'Payer ID', 'Service', 'Resource Type', 
                'Resource ARN', 'Resource Name', 'Regions / AZs',
                'Engine', 'Version', 'End-of-Support', 
                'Auto Minor Version Upgrade',
                'Extended Support - Start Date',
                'Extended Support - Year 1 Pricing Start Date',
                'Extended Support - Year 3 Pricing Start Date',
                'Extended Support - End Date',
                'Insights'
            ])
            writer.writerow([
                'TestAccount (Test)', '123456789', 'Lambda', 'Function',
                'arn:aws:lambda:us-east-1:123456789:function:test',
                'test-function', 'us-east-1',
                '-', 'python3.9', '15-Dec-25',
                '-', '-', '-', '-', '-',
                'Out of support.'
            ])
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            resources = parser.parse()
            
            assert len(resources) == 1
            resource = resources[0]
            assert resource.account == 'TestAccount (Test)'
            assert resource.service == 'Lambda'
            assert resource.resource_name == 'test-function'
            assert resource.version == 'python3.9'
            assert resource.end_of_support == date(2025, 12, 15)
            assert resource.end_of_support_raw == '15-Dec-25'
            assert resource.insights == 'Out of support.'
            assert resource.engine is None  # '-' should be converted to None
        finally:
            os.unlink(temp_path)
    
    def test_parse_preserves_row_count(self):
        """Test that parsing preserves the number of data rows."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Account', 'Payer ID', 'Service', 'Resource Type', 
                'Resource ARN', 'Resource Name', 'Regions / AZs',
                'Version', 'End-of-Support', 'Insights'
            ])
            # Write 5 data rows
            for i in range(5):
                writer.writerow([
                    f'Account{i}', f'{i}', 'Lambda', 'Function',
                    f'arn:aws:lambda:us-east-1:{i}:function:test{i}',
                    f'test-function-{i}', 'us-east-1',
                    'python3.9', '15-Dec-25', 'Out of support.'
                ])
            temp_path = f.name
        
        try:
            parser = CSVParser(temp_path)
            resources = parser.parse()
            
            assert len(resources) == 5
        finally:
            os.unlink(temp_path)



# Property-Based Tests
import os
import csv
import tempfile
from hypothesis import given, settings, HealthCheck
from tests.conftest import csv_rows_strategy, date_string_dd_mmm_yy_strategy


def create_temp_csv(rows):
    """Create a temporary CSV file from rows."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='', encoding='utf-8') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        return f.name


class TestCSVParserProperties:
    """Property-based tests for CSV Parser.
    
    Feature: end-of-support-tool
    """
    
    @given(rows=csv_rows_strategy(min_rows=1, max_rows=10))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property_1_csv_parsing_preserves_row_count(self, rows):
        """Property 1: CSV Parsing Preserves Row Count
        
        For any valid CSV file with N data rows, parsing the file SHALL 
        produce exactly N Resource objects.
        
        Feature: end-of-support-tool, Property 1: CSV Parsing Preserves Row Count
        Validates: Requirements 1.1
        """
        csv_path = create_temp_csv(rows)
        try:
            parser = CSVParser(csv_path)
            resources = parser.parse()
            
            assert len(resources) == len(rows)
        finally:
            os.unlink(csv_path)
    
    @given(rows=csv_rows_strategy(min_rows=1, max_rows=10))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property_2_csv_field_extraction_round_trip(self, rows):
        """Property 2: CSV Field Extraction Round-Trip
        
        For any Resource object, if we serialize it to CSV format and parse 
        it back, the resulting Resource SHALL have equivalent field values 
        to the original (after stripping whitespace, as the parser does).
        
        Feature: end-of-support-tool, Property 2: CSV Field Extraction Round-Trip
        Validates: Requirements 1.2
        """
        csv_path = create_temp_csv(rows)
        try:
            parser = CSVParser(csv_path)
            resources = parser.parse()
            
            for i, (row, resource) in enumerate(zip(rows, resources)):
                # Check key fields match (parser strips whitespace)
                assert resource.account == row['Account'].strip(), f"Row {i}: account mismatch"
                assert resource.service == row['Service'].strip(), f"Row {i}: service mismatch"
                assert resource.resource_name == row['Resource Name'].strip(), f"Row {i}: resource_name mismatch"
                assert resource.version == row['Version'].strip(), f"Row {i}: version mismatch"
                assert resource.region == row['Regions / AZs'].strip(), f"Row {i}: region mismatch"
                assert resource.insights == row['Insights'].strip(), f"Row {i}: insights mismatch"
                assert resource.end_of_support_raw == row['End-of-Support'].strip(), f"Row {i}: end_of_support_raw mismatch"
                
                # Check engine field (handles '-' -> None conversion)
                engine_val = row['Engine'].strip()
                expected_engine = engine_val if engine_val != '-' else None
                assert resource.engine == expected_engine, f"Row {i}: engine mismatch"
        finally:
            os.unlink(csv_path)
    
    @given(date_tuple=date_string_dd_mmm_yy_strategy())
    @settings(max_examples=100)
    def test_property_3_date_parsing_consistency(self, date_tuple):
        """Property 3: Date Parsing Consistency
        
        For any valid date string in supported formats (DD-MMM-YY), parsing 
        the string SHALL produce a date object that represents the same 
        calendar date.
        
        Feature: end-of-support-tool, Property 3: Date Parsing Consistency
        Validates: Requirements 1.5
        """
        date_str, expected_date = date_tuple
        parser = CSVParser('dummy.csv')
        
        parsed_date = parser._parse_date(date_str, 1, 'test')
        
        assert parsed_date == expected_date, f"Date string '{date_str}' should parse to {expected_date}, got {parsed_date}"
