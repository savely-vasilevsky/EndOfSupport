#!/usr/bin/env python3
"""
Compare Extended Support Date Sources

This script compares three different approaches to get Extended Support dates:
1. AWS Health API - Planned lifecycle events
2. Static Lookup Table - Hardcoded dates from AWS documentation
3. RDS/Aurora API - describe-db-major-engine-versions

Usage:
    python compare_extended_support_sources.py [--profile PROFILE]

Requirements:
    pip install boto3
"""

import argparse
import json
import sys
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Error: boto3 is required. Install with: pip install boto3")
    sys.exit(1)


@dataclass
class ExtendedSupportDates:
    """Extended support date information for a service/engine/version."""
    service: str
    engine: str
    version: str
    standard_support_end: Optional[date] = None
    extended_support_start: Optional[date] = None
    extended_support_year1_start: Optional[date] = None
    extended_support_year3_start: Optional[date] = None
    extended_support_end: Optional[date] = None
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "engine": self.engine,
            "version": self.version,
            "standard_support_end": str(self.standard_support_end) if self.standard_support_end else None,
            "extended_support_start": str(self.extended_support_start) if self.extended_support_start else None,
            "extended_support_year1_start": str(self.extended_support_year1_start) if self.extended_support_year1_start else None,
            "extended_support_year3_start": str(self.extended_support_year3_start) if self.extended_support_year3_start else None,
            "extended_support_end": str(self.extended_support_end) if self.extended_support_end else None,
            "source": self.source,
        }


# =============================================================================
# OPTION 2: Static Lookup Table (from AWS Documentation)
# =============================================================================

# Extended Support dates from AWS documentation
# Sources:
# - https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/MySQL.Concepts.VersionMgmt.html
# - https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-release-calendar.html
# - https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.VersionPolicy.MajorVersions.html
# - https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html

STATIC_EXTENDED_SUPPORT_DATES = {
    # RDS MySQL
    ("RDS", "mysql", "5.7"): {
        "standard_support_end": "2024-02-29",
        "extended_support_start": "2024-03-01",
        "extended_support_year1_start": "2024-03-01",
        "extended_support_year3_start": "2026-03-01",
        "extended_support_end": "2027-02-28",
    },
    ("RDS", "mysql", "8.0"): {
        "standard_support_end": "2026-04-30",
        "extended_support_start": "2026-05-01",
        "extended_support_year1_start": "2026-05-01",
        "extended_support_year3_start": "2028-05-01",
        "extended_support_end": "2029-04-30",
    },
    # RDS PostgreSQL
    ("RDS", "postgres", "11"): {
        "standard_support_end": "2024-02-29",
        "extended_support_start": "2024-03-01",
        "extended_support_year1_start": "2024-03-01",
        "extended_support_year3_start": "2026-03-01",
        "extended_support_end": "2027-02-28",
    },
    ("RDS", "postgres", "12"): {
        "standard_support_end": "2025-02-28",
        "extended_support_start": "2025-03-01",
        "extended_support_year1_start": "2025-03-01",
        "extended_support_year3_start": "2027-03-01",
        "extended_support_end": "2028-02-29",
    },
    ("RDS", "postgres", "13"): {
        "standard_support_end": "2026-02-28",
        "extended_support_start": "2026-03-01",
        "extended_support_year1_start": "2026-03-01",
        "extended_support_year3_start": "2028-03-01",
        "extended_support_end": "2029-02-28",
    },
    ("RDS", "postgres", "14"): {
        "standard_support_end": "2027-02-28",
        "extended_support_start": "2027-03-01",
        "extended_support_year1_start": "2027-03-01",
        "extended_support_year3_start": "2029-03-01",
        "extended_support_end": "2030-02-28",
    },
    # Aurora MySQL
    ("Aurora", "aurora-mysql", "5.7"): {
        "standard_support_end": "2024-10-31",
        "extended_support_start": "2024-11-01",
        "extended_support_year1_start": "2024-11-01",
        "extended_support_year3_start": "2026-11-01",
        "extended_support_end": "2027-10-31",
    },
    ("Aurora", "aurora-mysql", "8.0"): {
        "standard_support_end": "2027-04-30",
        "extended_support_start": "2027-05-01",
        "extended_support_year1_start": "2027-05-01",
        "extended_support_year3_start": "2029-05-01",
        "extended_support_end": "2030-04-30",
    },
    # Aurora PostgreSQL
    ("Aurora", "aurora-postgresql", "11"): {
        "standard_support_end": "2024-02-29",
        "extended_support_start": "2024-03-01",
        "extended_support_year1_start": "2024-03-01",
        "extended_support_year3_start": "2026-03-01",
        "extended_support_end": "2027-02-28",
    },
    ("Aurora", "aurora-postgresql", "12"): {
        "standard_support_end": "2025-02-28",
        "extended_support_start": "2025-03-01",
        "extended_support_year1_start": "2025-03-01",
        "extended_support_year3_start": "2027-03-01",
        "extended_support_end": "2028-02-29",
    },
    ("Aurora", "aurora-postgresql", "13"): {
        "standard_support_end": "2026-02-28",
        "extended_support_start": "2026-03-01",
        "extended_support_year1_start": "2026-03-01",
        "extended_support_year3_start": "2028-03-01",
        "extended_support_end": "2029-02-28",
    },
    ("Aurora", "aurora-postgresql", "14"): {
        "standard_support_end": "2027-02-28",
        "extended_support_start": "2027-03-01",
        "extended_support_year1_start": "2027-03-01",
        "extended_support_year3_start": "2029-03-01",
        "extended_support_end": "2030-02-28",
    },
    # DocumentDB (MongoDB compatible)
    ("DocumentDB", "docdb", "4.0"): {
        "standard_support_end": "2024-04-30",
        "extended_support_start": "2024-05-01",
        "extended_support_year1_start": "2024-05-01",
        "extended_support_year3_start": "2026-05-01",
        "extended_support_end": "2027-04-30",
    },
    # ElastiCache Redis
    ("ElastiCache", "redis", "6.0"): {
        "standard_support_end": "2025-04-30",
        "extended_support_start": None,  # No extended support for ElastiCache
        "extended_support_year1_start": None,
        "extended_support_year3_start": None,
        "extended_support_end": None,
    },
}


def get_static_lookup_dates() -> List[ExtendedSupportDates]:
    """Get extended support dates from static lookup table."""
    results = []
    for (service, engine, version), dates in STATIC_EXTENDED_SUPPORT_DATES.items():
        def parse_date(d):
            return datetime.strptime(d, "%Y-%m-%d").date() if d else None
        
        results.append(ExtendedSupportDates(
            service=service,
            engine=engine,
            version=version,
            standard_support_end=parse_date(dates.get("standard_support_end")),
            extended_support_start=parse_date(dates.get("extended_support_start")),
            extended_support_year1_start=parse_date(dates.get("extended_support_year1_start")),
            extended_support_year3_start=parse_date(dates.get("extended_support_year3_start")),
            extended_support_end=parse_date(dates.get("extended_support_end")),
            source="Static Lookup Table",
        ))
    return results


# =============================================================================
# OPTION 1: AWS Health API
# =============================================================================

def get_health_api_dates(session: boto3.Session) -> List[ExtendedSupportDates]:
    """Get extended support dates from AWS Health API planned lifecycle events."""
    results = []
    
    try:
        # AWS Health API is only available in us-east-1
        health = session.client('health', region_name='us-east-1')
        
        # Get planned lifecycle events
        paginator = health.get_paginator('describe_events')
        
        # Filter for planned lifecycle events
        event_filter = {
            'eventTypeCategories': ['scheduledChange'],
            'eventStatusCodes': ['open', 'upcoming'],
        }
        
        events_found = []
        for page in paginator.paginate(filter=event_filter):
            for event in page.get('events', []):
                event_type = event.get('eventTypeCode', '')
                # Look for planned lifecycle events
                if 'PLANNED_LIFECYCLE' in event_type or 'END_OF_SUPPORT' in event_type.upper():
                    events_found.append(event)
        
        print(f"\n[AWS Health API] Found {len(events_found)} planned lifecycle events")
        
        # Get details for each event
        for event in events_found:
            event_arn = event['arn']
            service = event.get('service', 'Unknown')
            
            # Get event details
            try:
                details = health.describe_event_details(eventArns=[event_arn])
                for detail in details.get('successfulSet', []):
                    event_desc = detail.get('eventDescription', {}).get('latestDescription', '')
                    
                    # Get affected entities
                    entities = health.describe_affected_entities(
                        filter={'eventArns': [event_arn]}
                    )
                    
                    entity_count = len(entities.get('entities', []))
                    
                    print(f"  - {event.get('eventTypeCode')}: {entity_count} affected entities")
                    print(f"    Start: {event.get('startTime')}, End: {event.get('endTime')}")
                    
                    # Parse dates from event
                    start_time = event.get('startTime')
                    end_time = event.get('endTime')
                    
                    results.append(ExtendedSupportDates(
                        service=service,
                        engine=event.get('eventTypeCode', ''),
                        version="See event details",
                        standard_support_end=start_time.date() if start_time else None,
                        extended_support_start=start_time.date() if start_time else None,
                        extended_support_end=end_time.date() if end_time else None,
                        source="AWS Health API",
                    ))
            except ClientError as e:
                print(f"  Error getting details for {event_arn}: {e}")
                
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'SubscriptionRequiredException':
            print("\n[AWS Health API] ERROR: Requires Business, Enterprise On-Ramp, or Enterprise Support plan")
            print("  The AWS Health API is only available with paid support plans.")
        else:
            print(f"\n[AWS Health API] ERROR: {e}")
    except Exception as e:
        print(f"\n[AWS Health API] ERROR: {e}")
    
    return results


# =============================================================================
# OPTION 3: RDS/Aurora API (describe-db-major-engine-versions)
# =============================================================================

def get_rds_api_dates(session: boto3.Session) -> List[ExtendedSupportDates]:
    """Get extended support dates from RDS API describe-db-major-engine-versions."""
    results = []
    
    try:
        rds = session.client('rds', region_name='us-east-1')
        
        # Get major engine versions for all supported engines
        engines = ['mysql', 'postgres', 'aurora-mysql', 'aurora-postgresql', 'docdb']
        
        print(f"\n[RDS API] Querying describe-db-major-engine-versions...")
        
        for engine in engines:
            try:
                response = rds.describe_db_engine_versions(
                    Engine=engine,
                    IncludeAll=False,
                )
                
                # Group by major version
                major_versions = {}
                for version_info in response.get('DBEngineVersions', []):
                    major = version_info.get('MajorEngineVersion', version_info.get('EngineVersion', '').split('.')[0])
                    if major not in major_versions:
                        major_versions[major] = version_info
                
                print(f"  {engine}: Found {len(major_versions)} major versions")
                
                for major_version, info in major_versions.items():
                    # Check for lifecycle support info
                    lifecycles = info.get('SupportedEngineLifecycles', [])
                    
                    standard_end = None
                    ext_start = None
                    ext_end = None
                    
                    for lifecycle in lifecycles:
                        name = lifecycle.get('LifecycleSupportName', '')
                        if 'standard' in name.lower():
                            standard_end = lifecycle.get('LifecycleSupportEndDate')
                        elif 'extended' in name.lower():
                            ext_start = lifecycle.get('LifecycleSupportStartDate')
                            ext_end = lifecycle.get('LifecycleSupportEndDate')
                    
                    # Determine service name
                    if 'aurora' in engine:
                        service = "Aurora"
                    elif engine == 'docdb':
                        service = "DocumentDB"
                    else:
                        service = "RDS"
                    
                    def parse_datetime(dt):
                        if dt is None:
                            return None
                        if isinstance(dt, datetime):
                            return dt.date()
                        return datetime.fromisoformat(str(dt).replace('Z', '+00:00')).date()
                    
                    results.append(ExtendedSupportDates(
                        service=service,
                        engine=engine,
                        version=major_version,
                        standard_support_end=parse_datetime(standard_end),
                        extended_support_start=parse_datetime(ext_start),
                        extended_support_end=parse_datetime(ext_end),
                        source="RDS API (describe-db-engine-versions)",
                    ))
                    
            except ClientError as e:
                print(f"  {engine}: Error - {e.response['Error']['Message']}")
                
    except Exception as e:
        print(f"\n[RDS API] ERROR: {e}")
    
    # Also try the newer describe-db-major-engine-versions API
    try:
        print(f"\n[RDS API] Trying describe-db-major-engine-versions (newer API)...")
        
        response = rds.describe_db_major_engine_versions()
        
        for version_info in response.get('DBMajorEngineVersions', []):
            engine = version_info.get('Engine', '')
            major_version = version_info.get('MajorEngineVersion', '')
            lifecycles = version_info.get('SupportedEngineLifecycles', [])
            
            standard_end = None
            ext_start = None
            ext_end = None
            
            for lifecycle in lifecycles:
                name = lifecycle.get('LifecycleSupportName', '')
                if 'standard' in name.lower():
                    standard_end = lifecycle.get('LifecycleSupportEndDate')
                elif 'extended' in name.lower():
                    ext_start = lifecycle.get('LifecycleSupportStartDate')
                    ext_end = lifecycle.get('LifecycleSupportEndDate')
            
            if lifecycles:
                print(f"  {engine} {major_version}: standard_end={standard_end}, ext_start={ext_start}, ext_end={ext_end}")
            
            # Determine service name
            if 'aurora' in engine:
                service = "Aurora"
            elif engine == 'docdb':
                service = "DocumentDB"
            else:
                service = "RDS"
            
            def parse_datetime(dt):
                if dt is None:
                    return None
                if isinstance(dt, datetime):
                    return dt.date()
                return datetime.fromisoformat(str(dt).replace('Z', '+00:00')).date()
            
            # Only add if we have lifecycle info
            if lifecycles:
                results.append(ExtendedSupportDates(
                    service=service,
                    engine=engine,
                    version=major_version,
                    standard_support_end=parse_datetime(standard_end),
                    extended_support_start=parse_datetime(ext_start),
                    extended_support_end=parse_datetime(ext_end),
                    source="RDS API (describe-db-major-engine-versions)",
                ))
                
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'InvalidAction':
            print(f"  describe-db-major-engine-versions not available (may require newer SDK)")
        else:
            print(f"  Error: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"  Error: {e}")
    
    return results


# =============================================================================
# Comparison and Output
# =============================================================================

def compare_sources(
    health_results: List[ExtendedSupportDates],
    static_results: List[ExtendedSupportDates],
    rds_results: List[ExtendedSupportDates]
) -> None:
    """Compare results from all three sources."""
    
    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    
    print(f"\n1. AWS Health API: {len(health_results)} results")
    print(f"2. Static Lookup Table: {len(static_results)} results")
    print(f"3. RDS/Aurora API: {len(rds_results)} results")
    
    # Detailed comparison
    print("\n" + "-" * 80)
    print("DETAILED RESULTS BY SOURCE")
    print("-" * 80)
    
    print("\n[1] AWS Health API Results:")
    if health_results:
        for r in health_results:
            print(f"  {r.service}/{r.engine}/{r.version}")
            print(f"    Standard End: {r.standard_support_end}")
            print(f"    Extended Start: {r.extended_support_start}")
            print(f"    Extended End: {r.extended_support_end}")
    else:
        print("  No results (requires Business/Enterprise Support plan)")
    
    print("\n[2] Static Lookup Table Results:")
    for r in static_results:
        print(f"  {r.service}/{r.engine}/{r.version}")
        print(f"    Standard End: {r.standard_support_end}")
        print(f"    Extended Start: {r.extended_support_start}")
        print(f"    Year 1 Start: {r.extended_support_year1_start}")
        print(f"    Year 3 Start: {r.extended_support_year3_start}")
        print(f"    Extended End: {r.extended_support_end}")
    
    print("\n[3] RDS/Aurora API Results:")
    if rds_results:
        for r in rds_results:
            print(f"  {r.service}/{r.engine}/{r.version}")
            print(f"    Standard End: {r.standard_support_end}")
            print(f"    Extended Start: {r.extended_support_start}")
            print(f"    Extended End: {r.extended_support_end}")
    else:
        print("  No results with lifecycle information")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    print("""
Based on the comparison:

1. AWS Health API (Option 1):
   - PROS: Real-time, account-specific, includes affected resources
   - CONS: Requires Business/Enterprise Support plan ($100+/month)
   - BEST FOR: Organizations with paid support plans who need real-time alerts

2. Static Lookup Table (Option 2):
   - PROS: No API calls needed, works offline, includes Year 1/Year 3 pricing dates
   - CONS: Requires manual updates when AWS publishes new dates
   - BEST FOR: Most users - reliable, comprehensive, no dependencies

3. RDS/Aurora API (Option 3):
   - PROS: Official AWS API, always up-to-date for RDS/Aurora
   - CONS: Only covers RDS/Aurora (not EKS, Lambda, etc.), no Year 1/Year 3 dates
   - BEST FOR: RDS/Aurora-focused workloads

RECOMMENDATION: Use a HYBRID approach:
   - Primary: Static Lookup Table (comprehensive, includes pricing tiers)
   - Supplement: RDS API for RDS/Aurora (to catch any updates)
   - Optional: AWS Health API if you have Business/Enterprise Support
""")


def main():
    parser = argparse.ArgumentParser(
        description="Compare Extended Support date sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--profile', '-p', help='AWS profile name')
    parser.add_argument('--output', '-o', help='Output JSON file')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Extended Support Date Sources Comparison")
    print("=" * 80)
    
    # Create session
    session = boto3.Session(profile_name=args.profile) if args.profile else boto3.Session()
    
    # Get results from each source
    print("\nFetching data from all sources...")
    
    # Option 1: AWS Health API
    health_results = get_health_api_dates(session)
    
    # Option 2: Static Lookup Table
    static_results = get_static_lookup_dates()
    print(f"\n[Static Lookup] Loaded {len(static_results)} entries from lookup table")
    
    # Option 3: RDS/Aurora API
    rds_results = get_rds_api_dates(session)
    
    # Compare results
    compare_sources(health_results, static_results, rds_results)
    
    # Output to JSON if requested
    if args.output:
        output = {
            "health_api": [r.to_dict() for r in health_results],
            "static_lookup": [r.to_dict() for r in static_results],
            "rds_api": [r.to_dict() for r in rds_results],
        }
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nResults saved to {args.output}")


if __name__ == '__main__':
    main()
