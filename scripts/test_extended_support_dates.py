#!/usr/bin/env python3
"""
Test Extended Support Date Fetching for All Services

This script tests the extended support date lookup functionality
for all supported services and versions.
"""

import sys
import os
from datetime import date, timedelta
from typing import Dict, List, Tuple

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extended_support_lookup import (
    ExtendedSupportLookup,
    ExtendedSupportDates,
    STATIC_EXTENDED_SUPPORT_DATES,
    EXTENDED_SUPPORT_PRICING,
    INSTANCE_VCPU_MAP,
)


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_subheader(title: str):
    """Print a formatted subheader."""
    print(f"\n--- {title} ---")


def test_static_lookup_coverage():
    """Test that all expected engine/version combinations are in static lookup."""
    print_header("TEST 1: Static Lookup Table Coverage")
    
    expected_engines = {
        "mysql": ["5.7", "8.0", "8.4"],
        "postgres": ["11", "12", "13", "14", "15", "16", "17"],
        "aurora-mysql": ["5.7", "8.0"],
        "aurora-postgresql": ["11", "12", "13", "14", "15", "16", "17"],
        "docdb": ["4.0", "5.0"],
    }
    
    missing = []
    found = []
    
    for engine, versions in expected_engines.items():
        for version in versions:
            key = (engine, version)
            if key in STATIC_EXTENDED_SUPPORT_DATES:
                found.append(key)
            else:
                missing.append(key)
    
    print(f"\nFound {len(found)} engine/version combinations in static lookup:")
    for engine, version in sorted(found):
        print(f"  ✓ {engine} {version}")
    
    if missing:
        print(f"\n⚠ Missing {len(missing)} expected combinations:")
        for engine, version in sorted(missing):
            print(f"  ✗ {engine} {version}")
        return False
    
    print("\n✓ All expected engine/version combinations found!")
    return True


def test_date_validity():
    """Test that all dates in static lookup are valid and logical."""
    print_header("TEST 2: Date Validity and Logic")
    
    errors = []
    warnings = []
    
    for (engine, version), data in STATIC_EXTENDED_SUPPORT_DATES.items():
        from datetime import datetime
        
        def parse_date(d):
            return datetime.strptime(d, "%Y-%m-%d").date() if d else None
        
        std_end = parse_date(data.get("standard_support_end"))
        ext_start = parse_date(data.get("extended_support_start"))
        y1_start = parse_date(data.get("extended_support_year1_start"))
        y3_start = parse_date(data.get("extended_support_year3_start"))
        ext_end = parse_date(data.get("extended_support_end"))
        
        prefix = f"{engine} {version}"
        
        # Check all required dates exist
        if not std_end:
            errors.append(f"{prefix}: Missing standard_support_end")
        if not ext_start:
            errors.append(f"{prefix}: Missing extended_support_start")
        if not ext_end:
            errors.append(f"{prefix}: Missing extended_support_end")
        
        # Check date order
        if std_end and ext_start and ext_start < std_end:
            errors.append(f"{prefix}: extended_support_start ({ext_start}) before standard_support_end ({std_end})")
        
        if ext_start and ext_end and ext_end < ext_start:
            errors.append(f"{prefix}: extended_support_end ({ext_end}) before extended_support_start ({ext_start})")
        
        if y1_start and y3_start and y3_start < y1_start:
            errors.append(f"{prefix}: year3_start ({y3_start}) before year1_start ({y1_start})")
        
        # Check Year 1 and Year 3 are ~2 years apart
        if y1_start and y3_start:
            diff = (y3_start - y1_start).days
            if diff < 700 or diff > 750:  # Should be ~730 days (2 years)
                warnings.append(f"{prefix}: Year 1 to Year 3 gap is {diff} days (expected ~730)")
        
        # Check extended support period is ~3 years
        if ext_start and ext_end:
            diff = (ext_end - ext_start).days
            if diff < 1000 or diff > 1200:  # Should be ~1095 days (3 years)
                warnings.append(f"{prefix}: Extended support period is {diff} days (expected ~1095)")
    
    if errors:
        print(f"\n✗ Found {len(errors)} errors:")
        for err in errors:
            print(f"  ERROR: {err}")
    else:
        print("\n✓ All dates are valid and logically ordered!")
    
    if warnings:
        print(f"\n⚠ Found {len(warnings)} warnings:")
        for warn in warnings:
            print(f"  WARNING: {warn}")
    
    return len(errors) == 0


def test_lookup_class():
    """Test the ExtendedSupportLookup class functionality."""
    print_header("TEST 3: ExtendedSupportLookup Class")
    
    lookup = ExtendedSupportLookup()
    errors = []
    
    # Test all static entries
    print_subheader("Testing get_extended_support_dates()")
    
    for (engine, version) in STATIC_EXTENDED_SUPPORT_DATES.keys():
        dates = lookup.get_extended_support_dates(engine, version)
        
        if dates is None:
            errors.append(f"{engine} {version}: Returned None")
            continue
        
        if dates.engine != engine:
            errors.append(f"{engine} {version}: Engine mismatch ({dates.engine})")
        
        if dates.standard_support_end is None:
            errors.append(f"{engine} {version}: Missing standard_support_end")
        
        if dates.extended_support_start is None:
            errors.append(f"{engine} {version}: Missing extended_support_start")
        
        if dates.extended_support_end is None:
            errors.append(f"{engine} {version}: Missing extended_support_end")
        
        print(f"  ✓ {engine} {version}: {dates.source}")
    
    # Test version normalization
    print_subheader("Testing version normalization")
    
    test_cases = [
        ("mysql", "5.7.44", "5.7"),  # Should normalize to 5.7
        ("postgres", "14.9", "14"),   # Should normalize to 14
        ("aurora-mysql", "5.7.mysql_aurora.2.11.4", "5.7"),
    ]
    
    for engine, full_version, expected_major in test_cases:
        dates = lookup.get_extended_support_dates(engine, full_version)
        if dates:
            print(f"  ✓ {engine} {full_version} -> {dates.version}")
        else:
            print(f"  ✗ {engine} {full_version} -> None (expected {expected_major})")
            errors.append(f"Version normalization failed: {engine} {full_version}")
    
    if errors:
        print(f"\n✗ Found {len(errors)} errors:")
        for err in errors:
            print(f"  ERROR: {err}")
        return False
    
    print("\n✓ ExtendedSupportLookup class working correctly!")
    return True


def test_year_calculation():
    """Test the current year calculation logic."""
    print_header("TEST 4: Extended Support Year Calculation")
    
    lookup = ExtendedSupportLookup()
    errors = []
    
    # Test with MySQL 5.7 which is currently in extended support
    dates = lookup.get_extended_support_dates("mysql", "5.7")
    
    if dates:
        print(f"\nTesting with MySQL 5.7:")
        print(f"  Year 1 Start: {dates.extended_support_year1_start}")
        print(f"  Year 3 Start: {dates.extended_support_year3_start}")
        print(f"  Extended End: {dates.extended_support_end}")
        
        # Test different reference dates
        test_dates = [
            (date(2024, 2, 15), None, "Before extended support"),
            (date(2024, 3, 15), 1, "Year 1"),
            (date(2025, 3, 15), 2, "Year 2"),
            (date(2026, 3, 15), 3, "Year 3"),
            (date(2027, 3, 15), None, "After extended support"),
        ]
        
        for ref_date, expected_year, description in test_dates:
            actual_year = dates.get_current_year(ref_date)
            status = "✓" if actual_year == expected_year else "✗"
            print(f"  {status} {ref_date}: Year {actual_year} ({description})")
            
            if actual_year != expected_year:
                errors.append(f"Year calculation for {ref_date}: expected {expected_year}, got {actual_year}")
    
    # Test current date
    print_subheader("Current Year for All Engines")
    today = date.today()
    
    for (engine, version) in sorted(STATIC_EXTENDED_SUPPORT_DATES.keys()):
        dates = lookup.get_extended_support_dates(engine, version)
        if dates:
            current_year = dates.get_current_year(today)
            if current_year:
                print(f"  {engine} {version}: Year {current_year}")
            else:
                # Check if before or after
                if dates.extended_support_start and today < dates.extended_support_start:
                    print(f"  {engine} {version}: Not yet in extended support")
                elif dates.extended_support_end and today > dates.extended_support_end:
                    print(f"  {engine} {version}: Past extended support")
                else:
                    print(f"  {engine} {version}: Standard support")
    
    if errors:
        print(f"\n✗ Found {len(errors)} errors:")
        for err in errors:
            print(f"  ERROR: {err}")
        return False
    
    print("\n✓ Year calculation working correctly!")
    return True


def test_cost_estimation():
    """Test the cost estimation functionality."""
    print_header("TEST 5: Cost Estimation")
    
    lookup = ExtendedSupportLookup()
    errors = []
    
    # Test cost calculation for different instance types
    test_cases = [
        ("aurora-mysql", "5.7", "db.r5.large", 2),    # 2 vCPUs
        ("aurora-mysql", "5.7", "db.r5.xlarge", 4),   # 4 vCPUs
        ("mysql", "5.7", "db.t3.medium", 2),          # 2 vCPUs
        ("postgres", "12", "db.m5.large", 2),         # 2 vCPUs
        ("docdb", "4.0", "db.r5.large", 2),           # 2 vCPUs
    ]
    
    print_subheader("Cost Estimates by Instance Type")
    
    for engine, version, instance_type, expected_vcpus in test_cases:
        cost = lookup.estimate_monthly_cost(engine, version, instance_type)
        
        if cost["vcpu_count"] != expected_vcpus:
            errors.append(f"{instance_type}: Expected {expected_vcpus} vCPUs, got {cost['vcpu_count']}")
        
        print(f"\n  {engine} {version} ({instance_type}):")
        print(f"    vCPUs: {cost['vcpu_count']}")
        print(f"    Year 1: ${cost['monthly_cost_year1']:.2f}/month (${cost['annual_cost_year1']:.2f}/year)")
        print(f"    Year 2: ${cost['monthly_cost_year2']:.2f}/month (${cost['annual_cost_year2']:.2f}/year)")
        print(f"    Year 3: ${cost['monthly_cost_year3']:.2f}/month (${cost['annual_cost_year3']:.2f}/year)")
        
        if cost['in_extended_support']:
            print(f"    Current (Year {cost['current_year']}): ${cost['current_monthly_cost']:.2f}/month")
    
    # Verify pricing increases each year
    print_subheader("Verifying Year-over-Year Price Increase")
    
    for engine, version, instance_type, _ in test_cases:
        cost = lookup.estimate_monthly_cost(engine, version, instance_type)
        
        if cost['monthly_cost_year2'] <= cost['monthly_cost_year1']:
            errors.append(f"{engine} {version}: Year 2 cost not greater than Year 1")
        
        if cost['monthly_cost_year3'] <= cost['monthly_cost_year2']:
            errors.append(f"{engine} {version}: Year 3 cost not greater than Year 2")
        
        print(f"  ✓ {engine} {version}: Y1 < Y2 < Y3")
    
    if errors:
        print(f"\n✗ Found {len(errors)} errors:")
        for err in errors:
            print(f"  ERROR: {err}")
        return False
    
    print("\n✓ Cost estimation working correctly!")
    return True


def test_pricing_coverage():
    """Test that pricing is available for all engines in static lookup."""
    print_header("TEST 6: Pricing Coverage")
    
    engines_in_lookup = set(engine for engine, _ in STATIC_EXTENDED_SUPPORT_DATES.keys())
    engines_with_pricing = set(EXTENDED_SUPPORT_PRICING.keys())
    
    print(f"\nEngines in static lookup: {sorted(engines_in_lookup)}")
    print(f"Engines with pricing: {sorted(engines_with_pricing)}")
    
    missing_pricing = engines_in_lookup - engines_with_pricing
    
    if missing_pricing:
        print(f"\n⚠ Engines without pricing: {sorted(missing_pricing)}")
        return False
    
    print("\n✓ All engines have pricing defined!")
    return True


def test_instance_type_coverage():
    """Test instance type vCPU mapping coverage."""
    print_header("TEST 7: Instance Type Coverage")
    
    # Common instance families
    families = ["t3", "t4g", "r5", "r6g", "r6i", "r7g", "m5", "m6g"]
    sizes = ["large", "xlarge", "2xlarge", "4xlarge"]
    
    missing = []
    found = []
    
    for family in families:
        for size in sizes:
            instance_type = f"db.{family}.{size}"
            if instance_type in INSTANCE_VCPU_MAP:
                found.append(instance_type)
            else:
                missing.append(instance_type)
    
    print(f"\nFound {len(found)} instance types with vCPU mapping")
    print(f"Total instance types in map: {len(INSTANCE_VCPU_MAP)}")
    
    if missing:
        print(f"\n⚠ Missing {len(missing)} common instance types:")
        for it in missing[:10]:  # Show first 10
            print(f"  - {it}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    
    print("\n✓ Instance type coverage check complete!")
    return True


def test_all_static_entries():
    """Display all static entries for verification."""
    print_header("TEST 8: All Static Entries Summary")
    
    lookup = ExtendedSupportLookup()
    entries = lookup.get_all_static_entries()
    
    print(f"\nTotal entries: {len(entries)}")
    
    # Group by engine
    by_engine: Dict[str, List[ExtendedSupportDates]] = {}
    for entry in entries:
        if entry.engine not in by_engine:
            by_engine[entry.engine] = []
        by_engine[entry.engine].append(entry)
    
    for engine in sorted(by_engine.keys()):
        print(f"\n{engine.upper()}:")
        for entry in sorted(by_engine[engine], key=lambda x: x.version):
            current_year = entry.get_current_year()
            status = f"Year {current_year}" if current_year else "Not in ext. support"
            print(f"  {entry.version}: {entry.standard_support_end} -> {entry.extended_support_end} ({status})")
    
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print(" EXTENDED SUPPORT DATE FETCHING TEST SUITE")
    print("=" * 70)
    print(f"\nTest Date: {date.today()}")
    
    results = []
    
    # Run all tests
    results.append(("Static Lookup Coverage", test_static_lookup_coverage()))
    results.append(("Date Validity", test_date_validity()))
    results.append(("Lookup Class", test_lookup_class()))
    results.append(("Year Calculation", test_year_calculation()))
    results.append(("Cost Estimation", test_cost_estimation()))
    results.append(("Pricing Coverage", test_pricing_coverage()))
    results.append(("Instance Type Coverage", test_instance_type_coverage()))
    results.append(("All Static Entries", test_all_static_entries()))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n{'=' * 70}")
    print(f" Results: {passed}/{total} tests passed")
    print(f"{'=' * 70}\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
