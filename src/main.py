"""CLI entry point for EndOfSupportTool.

Provides command-line interface for analyzing AWS resource inventory CSV files
and generating support status reports.
"""

import argparse
import sys
from typing import List, Optional

from .classifier import ResourceClassifier
from .formatters import TextFormatter, CSVFormatter, JSONFormatter, ExcelFormatter, EXCEL_AVAILABLE
from .generator import ReportGenerator
from .models import ReportFilters, SupportStatus
from .parser import CSVParser, CSVParseError


# Valid output formats
OUTPUT_FORMATS = ["text", "csv", "json", "excel"]

# Valid status filter values (case-insensitive matching)
STATUS_CHOICES = {
    "supported": SupportStatus.SUPPORTED,
    "approaching": SupportStatus.APPROACHING_EOS,
    "approaching-eos": SupportStatus.APPROACHING_EOS,
    "extended": SupportStatus.EXTENDED_SUPPORT,
    "extended-support": SupportStatus.EXTENDED_SUPPORT,
    "out-of-support": SupportStatus.OUT_OF_SUPPORT,
    "oos": SupportStatus.OUT_OF_SUPPORT,
}


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="eos-tool",
        description="Analyze AWS resource support status from inventory CSV files. "
                    "Generates reports grouped by Account, Service, Engine, and Version.",
        epilog="Examples:\n"
               "  eos-tool inventory.csv\n"
               "  eos-tool inventory.csv --output-format json --output-file report.json\n"
               "  eos-tool inventory.csv --status out-of-support --status approaching\n"
               "  eos-tool inventory.csv --account prod-account --service Lambda\n"
               "  eos-tool inventory.csv --days-threshold 60",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    # Required positional argument
    parser.add_argument(
        "input_file",
        help="Path to the input CSV file containing AWS resource inventory",
    )
    
    # Output format options
    parser.add_argument(
        "--output-format",
        choices=OUTPUT_FORMATS,
        default="text",
        help="Output format for the report (default: text)",
    )
    
    parser.add_argument(
        "--output-file",
        "-o",
        help="Output file path. If not specified, prints to stdout",
    )
    
    # Filter options
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        metavar="STATUS",
        help="Filter by support status. Can be specified multiple times. "
             "Valid values: supported, approaching, extended, out-of-support, oos",
    )
    
    parser.add_argument(
        "--account",
        action="append",
        dest="accounts",
        metavar="ACCOUNT",
        help="Filter by account name. Can be specified multiple times",
    )
    
    parser.add_argument(
        "--service",
        action="append",
        dest="services",
        metavar="SERVICE",
        help="Filter by service type (e.g., Lambda, RDS). Can be specified multiple times",
    )
    
    # Configuration options
    parser.add_argument(
        "--days-threshold",
        type=int,
        default=90,
        metavar="DAYS",
        help="Number of days to consider as 'approaching' end-of-support (default: 90)",
    )
    
    return parser


def parse_status_filters(status_args: Optional[List[str]]) -> Optional[List[SupportStatus]]:
    """Parse status filter arguments into SupportStatus enum values.
    
    Args:
        status_args: List of status strings from command line.
        
    Returns:
        List of SupportStatus values, or None if no filters specified.
        
    Raises:
        ValueError: If an invalid status value is provided.
    """
    if not status_args:
        return None
    
    statuses = []
    for status_str in status_args:
        status_lower = status_str.lower().strip()
        if status_lower not in STATUS_CHOICES:
            valid_options = ", ".join(sorted(STATUS_CHOICES.keys()))
            raise ValueError(
                f"Invalid status filter: '{status_str}'. "
                f"Valid options: {valid_options}"
            )
        statuses.append(STATUS_CHOICES[status_lower])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_statuses = []
    for s in statuses:
        if s not in seen:
            seen.add(s)
            unique_statuses.append(s)
    
    return unique_statuses


def get_formatter(output_format: str):
    """Get the appropriate formatter for the output format.
    
    Args:
        output_format: One of 'text', 'csv', 'json', or 'excel'.
        
    Returns:
        Formatter instance.
        
    Raises:
        ValueError: If invalid output format is specified.
        ImportError: If Excel format requested but openpyxl not installed.
    """
    if output_format == "excel":
        if not EXCEL_AVAILABLE:
            raise ImportError(
                "Excel output requires openpyxl. Install with: pip install openpyxl"
            )
        return ExcelFormatter()
    
    formatters = {
        "text": TextFormatter,
        "csv": CSVFormatter,
        "json": JSONFormatter,
    }
    
    if output_format not in formatters:
        raise ValueError(f"Invalid output format: {output_format}. Valid options: {', '.join(OUTPUT_FORMATS)}")
    
    return formatters[output_format]()


def print_status(message: str, verbose: bool = True) -> None:
    """Print a status message to stderr.
    
    Args:
        message: The message to print.
        verbose: Whether to print the message (for future --quiet flag support).
    """
    if verbose:
        print(message, file=sys.stderr)


def print_summary(report) -> None:
    """Print a summary of the report to stderr.
    
    Args:
        report: The generated Report object.
    """
    print_status("")
    print_status("=" * 50)
    print_status("REPORT SUMMARY")
    print_status("=" * 50)
    print_status(f"Total resources analyzed: {report.total_resources}")
    print_status("")
    
    # Print status breakdown
    for status in SupportStatus:
        count = report.total_counts.get(status, 0)
        if count > 0:
            print_status(f"  {status.value}: {count}")
    
    print_status("=" * 50)
    print_status("")


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.
    
    Args:
        args: Command line arguments. If None, uses sys.argv.
        
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    try:
        # Parse status filters
        status_filters = parse_status_filters(parsed_args.statuses)
        
        # Create filters object
        filters = None
        if status_filters or parsed_args.accounts or parsed_args.services:
            filters = ReportFilters(
                statuses=status_filters,
                accounts=parsed_args.accounts,
                services=parsed_args.services,
            )
            
            # Show active filters
            print_status("Active filters:")
            if status_filters:
                status_names = [s.value for s in status_filters]
                print_status(f"  Status: {', '.join(status_names)}")
            if parsed_args.accounts:
                print_status(f"  Accounts: {', '.join(parsed_args.accounts)}")
            if parsed_args.services:
                print_status(f"  Services: {', '.join(parsed_args.services)}")
            print_status("")
        
        # Parse CSV file
        print_status(f"Reading CSV file: {parsed_args.input_file}")
        csv_parser = CSVParser(parsed_args.input_file)
        resources = csv_parser.parse()
        print_status(f"Parsed {len(resources)} resources")
        
        # Show threshold info
        print_status(f"Days threshold for 'Approaching EOS': {parsed_args.days_threshold} days")
        
        # Classify and generate report
        classifier = ResourceClassifier(days_threshold=parsed_args.days_threshold)
        generator = ReportGenerator(resources, classifier)
        
        print_status("Classifying resources and generating report...")
        report = generator.generate(filters=filters)
        
        # Print summary to stderr
        print_summary(report)
        
        # Format and write output
        formatter = get_formatter(parsed_args.output_format)
        
        # Excel format requires file output and writes directly
        if parsed_args.output_format == "excel":
            if not parsed_args.output_file:
                print("Error: Excel format requires --output-file to be specified", file=sys.stderr)
                return 1
            try:
                formatter.format_to_file(report, parsed_args.output_file)
                print_status(f"Report written to: {parsed_args.output_file}")
            except IOError as e:
                print(f"Error: Cannot write to output file: {parsed_args.output_file}", file=sys.stderr)
                print(f"  Reason: {e}", file=sys.stderr)
                return 1
        else:
            # Text-based formats
            output = formatter.format(report)
            
            # Write output
            if parsed_args.output_file:
                try:
                    with open(parsed_args.output_file, 'w', encoding='utf-8') as f:
                        f.write(output)
                    print_status(f"Report written to: {parsed_args.output_file}")
                except IOError as e:
                    print(f"Error: Cannot write to output file: {parsed_args.output_file}", file=sys.stderr)
                    print(f"  Reason: {e}", file=sys.stderr)
                    return 1
            else:
                print(output)
        
        print_status("Done!")
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Please check that the file path is correct and the file exists.", file=sys.stderr)
        return 1
        
    except PermissionError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Please check that you have read permissions for the file.", file=sys.stderr)
        return 1
        
    except CSVParseError as e:
        print(f"CSV Parse Error: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Please ensure the CSV file has the required columns:", file=sys.stderr)
        print("  Account, Payer ID, Service, Resource Type, Resource ARN,", file=sys.stderr)
        print("  Resource Name, Regions / AZs, Version, End-of-Support, Insights", file=sys.stderr)
        return 1
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
    except KeyboardInterrupt:
        print("", file=sys.stderr)
        print("Operation cancelled by user.", file=sys.stderr)
        return 130
        
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        print("", file=sys.stderr)
        print("If this problem persists, please report it with the error message above.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
