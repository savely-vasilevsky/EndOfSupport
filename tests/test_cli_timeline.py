"""Unit tests for CLI timeline arguments.

Tests the --include-timeline and --no-timeline flags in the CLI argument parser.

**Validates: Requirements 6.1, 6.2, 6.3**
"""

import pytest

from src.main import create_parser


class TestCLITimelineArguments:
    """Test CLI timeline argument parsing.
    
    **Validates: Requirements 6.1, 6.2, 6.3**
    """
    
    def test_default_behavior_include_timeline_is_true(self):
        """Test that include_timeline is True by default when no flag is provided.
        
        **Validates: Requirement 6.3**
        THE CLI SHALL include the Timeline_Sheet by default when generating Excel output.
        """
        parser = create_parser()
        args = parser.parse_args(["input.csv"])
        
        assert args.include_timeline is True
    
    def test_include_timeline_flag_sets_true(self):
        """Test that --include-timeline flag sets include_timeline to True.
        
        **Validates: Requirement 6.1**
        WHEN the --include-timeline flag is provided, THE CLI SHALL include 
        the Timeline_Sheet in Excel output.
        """
        parser = create_parser()
        args = parser.parse_args(["input.csv", "--include-timeline"])
        
        assert args.include_timeline is True
    
    def test_no_timeline_flag_sets_false(self):
        """Test that --no-timeline flag sets include_timeline to False.
        
        **Validates: Requirement 6.2**
        WHEN the --no-timeline flag is provided, THE CLI SHALL exclude 
        the Timeline_Sheet from Excel output.
        """
        parser = create_parser()
        args = parser.parse_args(["input.csv", "--no-timeline"])
        
        assert args.include_timeline is False
    
    def test_no_timeline_overrides_include_timeline(self):
        """Test that --no-timeline takes precedence when both flags are provided.
        
        When both flags are provided, the last one should win (argparse behavior).
        """
        parser = create_parser()
        
        # --include-timeline then --no-timeline
        args = parser.parse_args(["input.csv", "--include-timeline", "--no-timeline"])
        assert args.include_timeline is False
        
        # --no-timeline then --include-timeline
        args = parser.parse_args(["input.csv", "--no-timeline", "--include-timeline"])
        assert args.include_timeline is True
    
    def test_timeline_flags_with_other_options(self):
        """Test that timeline flags work correctly with other CLI options."""
        parser = create_parser()
        
        # Test with --no-timeline and other options
        args = parser.parse_args([
            "input.csv",
            "--output-format", "excel",
            "--output-file", "output.xlsx",
            "--no-timeline",
            "--days-threshold", "60"
        ])
        
        assert args.include_timeline is False
        assert args.output_format == "excel"
        assert args.output_file == "output.xlsx"
        assert args.days_threshold == 60
    
    def test_include_timeline_with_excel_format(self):
        """Test --include-timeline with Excel output format."""
        parser = create_parser()
        
        args = parser.parse_args([
            "input.csv",
            "--output-format", "excel",
            "--output-file", "output.xlsx",
            "--include-timeline"
        ])
        
        assert args.include_timeline is True
        assert args.output_format == "excel"
    
    def test_default_with_non_excel_format(self):
        """Test that include_timeline defaults to True even with non-Excel formats.
        
        Note: The flag is still parsed even for non-Excel formats, but it will
        be ignored during output generation (per Requirement 6.4).
        """
        parser = create_parser()
        
        # Test with text format
        args = parser.parse_args(["input.csv", "--output-format", "text"])
        assert args.include_timeline is True
        
        # Test with json format
        args = parser.parse_args(["input.csv", "--output-format", "json"])
        assert args.include_timeline is True
        
        # Test with csv format
        args = parser.parse_args(["input.csv", "--output-format", "csv"])
        assert args.include_timeline is True
