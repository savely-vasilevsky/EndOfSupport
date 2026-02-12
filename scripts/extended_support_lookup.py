#!/usr/bin/env python3
"""
Extended Support Lookup Module (Hybrid Approach)

Provides extended support dates using a hybrid approach:
1. Static lookup table with Year 1/Year 3 pricing dates
2. RDS API for real-time updates (when available)

Also calculates estimated extended support costs based on AWS pricing.

Usage:
    from extended_support_lookup import ExtendedSupportLookup
    
    lookup = ExtendedSupportLookup(session)
    dates = lookup.get_extended_support_dates("aurora-mysql", "5.7")
    cost = lookup.estimate_monthly_cost("aurora-mysql", "5.7", instance_type="db.r5.large")
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None


@dataclass
class ExtendedSupportDates:
    """Extended support date information."""
    engine: str
    version: str
    standard_support_end: Optional[date] = None
    extended_support_start: Optional[date] = None
    extended_support_year1_start: Optional[date] = None
    extended_support_year2_start: Optional[date] = None  # Calculated: Year1 + 1 year
    extended_support_year3_start: Optional[date] = None
    extended_support_end: Optional[date] = None
    source: str = "unknown"
    
    def get_current_year(self, reference_date: Optional[date] = None) -> Optional[int]:
        """Get the current extended support year (1, 2, or 3) or None if not in extended support."""
        today = reference_date or date.today()
        
        if self.extended_support_end and today > self.extended_support_end:
            return None  # Past extended support
        
        if self.extended_support_year3_start and today >= self.extended_support_year3_start:
            return 3
        
        # Calculate Year 2 start if not set
        year2_start = self.extended_support_year2_start
        if not year2_start and self.extended_support_year1_start:
            y1 = self.extended_support_year1_start
            year2_start = date(y1.year + 1, y1.month, y1.day)
        
        if year2_start and today >= year2_start:
            return 2
        
        year1_start = self.extended_support_year1_start or self.extended_support_start
        if year1_start and today >= year1_start:
            return 1
        
        return None  # Not yet in extended support


# =============================================================================
# Extended Support Pricing
# Source: https://aws.amazon.com/rds/aurora/pricing/ and RDS pricing pages
# EKS: https://aws.amazon.com/eks/pricing/
# =============================================================================

# Pricing per vCPU-hour for extended support (databases)
# EKS uses per-cluster-hour pricing instead
EXTENDED_SUPPORT_PRICING = {
    # Aurora MySQL/PostgreSQL pricing per vCPU-hour
    "aurora-mysql": {
        "year1": 0.100,  # $0.100 per vCPU-hour
        "year2": 0.200,  # $0.200 per vCPU-hour
        "year3": 0.300,  # $0.300 per vCPU-hour (estimated)
    },
    "aurora-postgresql": {
        "year1": 0.100,
        "year2": 0.200,
        "year3": 0.300,
    },
    # RDS MySQL/PostgreSQL pricing per vCPU-hour
    "mysql": {
        "year1": 0.100,
        "year2": 0.200,
        "year3": 0.300,
    },
    "postgres": {
        "year1": 0.100,
        "year2": 0.200,
        "year3": 0.300,
    },
    # DocumentDB (estimated based on similar pricing)
    "docdb": {
        "year1": 0.100,
        "year2": 0.200,
        "year3": 0.300,
    },
}

# EKS Extended Support Pricing (per cluster per hour)
# Standard support: $0.10/cluster/hour
# Extended support: $0.60/cluster/hour (includes $0.50 additional charge)
EKS_EXTENDED_SUPPORT_PRICING = {
    "standard": 0.10,   # $0.10 per cluster per hour
    "extended": 0.60,   # $0.60 per cluster per hour (total)
}

# vCPU counts for common instance types
INSTANCE_VCPU_MAP = {
    # T3 instances
    "db.t3.micro": 2, "db.t3.small": 2, "db.t3.medium": 2, "db.t3.large": 2,
    "db.t3.xlarge": 4, "db.t3.2xlarge": 8,
    # T4g instances
    "db.t4g.micro": 2, "db.t4g.small": 2, "db.t4g.medium": 2, "db.t4g.large": 2,
    "db.t4g.xlarge": 4, "db.t4g.2xlarge": 8,
    # R5 instances
    "db.r5.large": 2, "db.r5.xlarge": 4, "db.r5.2xlarge": 8, "db.r5.4xlarge": 16,
    "db.r5.8xlarge": 32, "db.r5.12xlarge": 48, "db.r5.16xlarge": 64, "db.r5.24xlarge": 96,
    # R6g instances
    "db.r6g.large": 2, "db.r6g.xlarge": 4, "db.r6g.2xlarge": 8, "db.r6g.4xlarge": 16,
    "db.r6g.8xlarge": 32, "db.r6g.12xlarge": 48, "db.r6g.16xlarge": 64,
    # R6i instances
    "db.r6i.large": 2, "db.r6i.xlarge": 4, "db.r6i.2xlarge": 8, "db.r6i.4xlarge": 16,
    "db.r6i.8xlarge": 32, "db.r6i.12xlarge": 48, "db.r6i.16xlarge": 64, "db.r6i.24xlarge": 96,
    # R7g instances
    "db.r7g.large": 2, "db.r7g.xlarge": 4, "db.r7g.2xlarge": 8, "db.r7g.4xlarge": 16,
    "db.r7g.8xlarge": 32, "db.r7g.12xlarge": 48, "db.r7g.16xlarge": 64,
    # M5 instances
    "db.m5.large": 2, "db.m5.xlarge": 4, "db.m5.2xlarge": 8, "db.m5.4xlarge": 16,
    "db.m5.8xlarge": 32, "db.m5.12xlarge": 48, "db.m5.16xlarge": 64, "db.m5.24xlarge": 96,
    # M6g instances
    "db.m6g.large": 2, "db.m6g.xlarge": 4, "db.m6g.2xlarge": 8, "db.m6g.4xlarge": 16,
    "db.m6g.8xlarge": 32, "db.m6g.12xlarge": 48, "db.m6g.16xlarge": 64,
    # Serverless
    "db.serverless": 0,  # ACU-based, different pricing
}


# =============================================================================
# Static Lookup Table (from AWS Documentation)
# =============================================================================

STATIC_EXTENDED_SUPPORT_DATES: Dict[Tuple[str, str], Dict[str, str]] = {
    # RDS MySQL
    ("mysql", "5.7"): {
        "standard_support_end": "2024-02-29",
        "extended_support_start": "2024-03-01",
        "extended_support_year1_start": "2024-03-01",
        "extended_support_year3_start": "2026-03-01",
        "extended_support_end": "2027-02-28",
    },
    ("mysql", "8.0"): {
        "standard_support_end": "2026-07-31",
        "extended_support_start": "2026-08-01",
        "extended_support_year1_start": "2026-08-01",
        "extended_support_year3_start": "2028-08-01",
        "extended_support_end": "2029-07-31",
    },
    ("mysql", "8.4"): {
        "standard_support_end": "2029-07-31",
        "extended_support_start": "2029-08-01",
        "extended_support_year1_start": "2029-08-01",
        "extended_support_year3_start": "2031-08-01",
        "extended_support_end": "2032-07-31",
    },
    # RDS PostgreSQL
    ("postgres", "11"): {
        "standard_support_end": "2024-02-29",
        "extended_support_start": "2024-03-01",
        "extended_support_year1_start": "2024-03-01",
        "extended_support_year3_start": "2026-03-01",
        "extended_support_end": "2027-03-31",
    },
    ("postgres", "12"): {
        "standard_support_end": "2025-02-28",
        "extended_support_start": "2025-03-01",
        "extended_support_year1_start": "2025-03-01",
        "extended_support_year3_start": "2027-03-01",
        "extended_support_end": "2028-02-29",
    },
    ("postgres", "13"): {
        "standard_support_end": "2026-02-28",
        "extended_support_start": "2026-03-01",
        "extended_support_year1_start": "2026-03-01",
        "extended_support_year3_start": "2028-03-01",
        "extended_support_end": "2029-02-28",
    },
    ("postgres", "14"): {
        "standard_support_end": "2027-02-28",
        "extended_support_start": "2027-03-01",
        "extended_support_year1_start": "2027-03-01",
        "extended_support_year3_start": "2029-03-01",
        "extended_support_end": "2030-02-28",
    },
    ("postgres", "15"): {
        "standard_support_end": "2028-02-29",
        "extended_support_start": "2028-03-01",
        "extended_support_year1_start": "2028-03-01",
        "extended_support_year3_start": "2030-03-01",
        "extended_support_end": "2031-02-28",
    },
    ("postgres", "16"): {
        "standard_support_end": "2029-02-28",
        "extended_support_start": "2029-03-01",
        "extended_support_year1_start": "2029-03-01",
        "extended_support_year3_start": "2031-03-01",
        "extended_support_end": "2032-02-29",
    },
    ("postgres", "17"): {
        "standard_support_end": "2030-02-28",
        "extended_support_start": "2030-03-01",
        "extended_support_year1_start": "2030-03-01",
        "extended_support_year3_start": "2032-03-01",
        "extended_support_end": "2033-02-28",
    },
    # Aurora MySQL
    ("aurora-mysql", "5.7"): {
        "standard_support_end": "2024-10-31",
        "extended_support_start": "2024-11-01",
        "extended_support_year1_start": "2024-11-01",
        "extended_support_year3_start": "2026-11-01",
        "extended_support_end": "2027-02-28",
    },
    ("aurora-mysql", "8.0"): {
        "standard_support_end": "2028-04-30",
        "extended_support_start": "2028-05-01",
        "extended_support_year1_start": "2028-05-01",
        "extended_support_year3_start": "2030-05-01",
        "extended_support_end": "2029-07-31",
    },
    # Aurora PostgreSQL
    ("aurora-postgresql", "11"): {
        "standard_support_end": "2024-02-29",
        "extended_support_start": "2024-03-01",
        "extended_support_year1_start": "2024-03-01",
        "extended_support_year3_start": "2026-03-01",
        "extended_support_end": "2027-03-31",
    },
    ("aurora-postgresql", "12"): {
        "standard_support_end": "2025-02-28",
        "extended_support_start": "2025-03-01",
        "extended_support_year1_start": "2025-03-01",
        "extended_support_year3_start": "2027-03-01",
        "extended_support_end": "2028-02-29",
    },
    ("aurora-postgresql", "13"): {
        "standard_support_end": "2026-02-28",
        "extended_support_start": "2026-03-01",
        "extended_support_year1_start": "2026-03-01",
        "extended_support_year3_start": "2028-03-01",
        "extended_support_end": "2029-02-28",
    },
    ("aurora-postgresql", "14"): {
        "standard_support_end": "2027-02-28",
        "extended_support_start": "2027-03-01",
        "extended_support_year1_start": "2027-03-01",
        "extended_support_year3_start": "2029-03-01",
        "extended_support_end": "2030-02-28",
    },
    ("aurora-postgresql", "15"): {
        "standard_support_end": "2028-02-29",
        "extended_support_start": "2028-03-01",
        "extended_support_year1_start": "2028-03-01",
        "extended_support_year3_start": "2030-03-01",
        "extended_support_end": "2031-02-28",
    },
    ("aurora-postgresql", "16"): {
        "standard_support_end": "2029-02-28",
        "extended_support_start": "2029-03-01",
        "extended_support_year1_start": "2029-03-01",
        "extended_support_year3_start": "2031-03-01",
        "extended_support_end": "2032-02-29",
    },
    ("aurora-postgresql", "17"): {
        "standard_support_end": "2030-02-28",
        "extended_support_start": "2030-03-01",
        "extended_support_year1_start": "2030-03-01",
        "extended_support_year3_start": "2032-03-01",
        "extended_support_end": "2033-02-28",
    },
    # DocumentDB
    ("docdb", "4.0"): {
        "standard_support_end": "2024-04-30",
        "extended_support_start": "2024-05-01",
        "extended_support_year1_start": "2024-05-01",
        "extended_support_year3_start": "2026-05-01",
        "extended_support_end": "2027-04-30",
    },
    ("docdb", "5.0"): {
        "standard_support_end": "2026-10-31",
        "extended_support_start": "2026-11-01",
        "extended_support_year1_start": "2026-11-01",
        "extended_support_year3_start": "2028-11-01",
        "extended_support_end": "2029-10-31",
    },
    # EKS (Elastic Kubernetes Service)
    # Source: https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html
    # EKS has 14 months standard support + 12 months extended support (26 total)
    # Note: EKS extended support is flat rate, no Year 1/2/3 tiers
    ("eks", "1.29"): {
        "standard_support_end": "2025-03-23",
        "extended_support_start": "2025-03-23",
        "extended_support_year1_start": "2025-03-23",
        "extended_support_year3_start": None,  # EKS only has 12 months extended
        "extended_support_end": "2026-03-23",
    },
    ("eks", "1.30"): {
        "standard_support_end": "2025-07-23",
        "extended_support_start": "2025-07-23",
        "extended_support_year1_start": "2025-07-23",
        "extended_support_year3_start": None,
        "extended_support_end": "2026-07-23",
    },
    ("eks", "1.31"): {
        "standard_support_end": "2025-11-26",
        "extended_support_start": "2025-11-26",
        "extended_support_year1_start": "2025-11-26",
        "extended_support_year3_start": None,
        "extended_support_end": "2026-11-26",
    },
    ("eks", "1.32"): {
        "standard_support_end": "2026-03-23",
        "extended_support_start": "2026-03-23",
        "extended_support_year1_start": "2026-03-23",
        "extended_support_year3_start": None,
        "extended_support_end": "2027-03-23",
    },
    ("eks", "1.33"): {
        "standard_support_end": "2026-07-29",
        "extended_support_start": "2026-07-29",
        "extended_support_year1_start": "2026-07-29",
        "extended_support_year3_start": None,
        "extended_support_end": "2027-07-29",
    },
    ("eks", "1.34"): {
        "standard_support_end": "2026-12-02",
        "extended_support_start": "2026-12-02",
        "extended_support_year1_start": "2026-12-02",
        "extended_support_year3_start": None,
        "extended_support_end": "2027-12-02",
    },
    ("eks", "1.35"): {
        "standard_support_end": "2027-03-27",
        "extended_support_start": "2027-03-27",
        "extended_support_year1_start": "2027-03-27",
        "extended_support_year3_start": None,
        "extended_support_end": "2028-03-27",
    },
}


class ExtendedSupportLookup:
    """Hybrid extended support lookup using static table + RDS API."""
    
    def __init__(self, session: Optional[Any] = None):
        """Initialize the lookup.
        
        Args:
            session: Optional boto3 Session for RDS API calls.
        """
        self.session = session
        self._api_cache: Dict[Tuple[str, str], ExtendedSupportDates] = {}
        self._api_loaded = False
    
    def _load_from_api(self) -> None:
        """Load extended support dates from RDS API."""
        if self._api_loaded or not self.session or not boto3:
            return
        
        try:
            rds = self.session.client('rds', region_name='us-east-1')
            response = rds.describe_db_major_engine_versions()
            
            for version_info in response.get('DBMajorEngineVersions', []):
                engine = version_info.get('Engine', '')
                major_version = version_info.get('MajorEngineVersion', '')
                lifecycles = version_info.get('SupportedEngineLifecycles', [])
                
                if not lifecycles:
                    continue
                
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
                
                def parse_dt(dt):
                    if dt is None:
                        return None
                    if isinstance(dt, datetime):
                        return dt.date()
                    return datetime.fromisoformat(str(dt).replace('Z', '+00:00')).date()
                
                self._api_cache[(engine, major_version)] = ExtendedSupportDates(
                    engine=engine,
                    version=major_version,
                    standard_support_end=parse_dt(standard_end),
                    extended_support_start=parse_dt(ext_start),
                    extended_support_end=parse_dt(ext_end),
                    source="RDS API",
                )
            
            self._api_loaded = True
        except Exception as e:
            print(f"Warning: Could not load from RDS API: {e}")
    
    def get_extended_support_dates(self, engine: str, version: str) -> Optional[ExtendedSupportDates]:
        """Get extended support dates for an engine/version.
        
        Uses hybrid approach:
        1. First check static lookup table (has Year 1/Year 3 dates)
        2. Supplement with RDS API data if available
        
        Args:
            engine: Engine name (e.g., "mysql", "aurora-postgresql", "eks")
            version: Major version (e.g., "5.7", "14", "1.31")
            
        Returns:
            ExtendedSupportDates or None if not found.
        """
        # Normalize engine name
        engine_lower = engine.lower()
        # Handle EKS variations
        if engine_lower in ('kubernetes', 'elastic kubernetes service (eks)', 'elastic kubernetes service'):
            engine_lower = 'eks'
        
        # Extract major version
        major_version = version.split('.')[0] if '.' in version else version
        # For MySQL/PostgreSQL/DocumentDB/EKS, keep major.minor (e.g., "5.7", "8.0", "4.0", "1.31")
        if engine_lower in ('mysql', 'aurora-mysql', 'docdb', 'eks') and '.' in version:
            parts = version.split('.')
            if len(parts) >= 2:
                major_version = f"{parts[0]}.{parts[1]}"
        
        # Check static lookup first (has Year 1/Year 3 pricing dates)
        static_key = (engine_lower, major_version)
        if static_key in STATIC_EXTENDED_SUPPORT_DATES:
            static_data = STATIC_EXTENDED_SUPPORT_DATES[static_key]
            
            def parse_date(d):
                return datetime.strptime(d, "%Y-%m-%d").date() if d else None
            
            return ExtendedSupportDates(
                engine=engine_lower,
                version=major_version,
                standard_support_end=parse_date(static_data.get("standard_support_end")),
                extended_support_start=parse_date(static_data.get("extended_support_start")),
                extended_support_year1_start=parse_date(static_data.get("extended_support_year1_start")),
                extended_support_year3_start=parse_date(static_data.get("extended_support_year3_start")),
                extended_support_end=parse_date(static_data.get("extended_support_end")),
                source="Static Lookup + Year Pricing",
            )
        
        # Try RDS API as fallback
        self._load_from_api()
        api_key = (engine_lower, major_version)
        if api_key in self._api_cache:
            return self._api_cache[api_key]
        
        return None
    
    def estimate_monthly_cost(
        self,
        engine: str,
        version: str,
        instance_type: Optional[str] = None,
        vcpu_count: Optional[int] = None,
        cluster_count: int = 1,
        hours_per_month: int = 730,
        reference_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Estimate monthly extended support cost for a resource.
        
        Args:
            engine: Engine name
            version: Engine version
            instance_type: Instance type (e.g., "db.r5.large") - for databases
            vcpu_count: Override vCPU count (if instance_type not provided) - for databases
            cluster_count: Number of clusters (for EKS)
            hours_per_month: Hours per month (default 730 for 24/7)
            reference_date: Date to calculate current year
            
        Returns:
            Dict with cost estimates and details.
        """
        dates = self.get_extended_support_dates(engine, version)
        
        # Normalize engine name
        engine_lower = engine.lower()
        if engine_lower in ('kubernetes', 'elastic kubernetes service (eks)', 'elastic kubernetes service'):
            engine_lower = 'eks'
        
        result = {
            "engine": engine,
            "version": version,
            "instance_type": instance_type,
            "vcpu_count": 0,
            "cluster_count": cluster_count if engine_lower == 'eks' else 0,
            "current_year": None,
            "in_extended_support": False,
            "monthly_cost_year1": 0.0,
            "monthly_cost_year2": 0.0,
            "monthly_cost_year3": 0.0,
            "current_monthly_cost": 0.0,
            "annual_cost_year1": 0.0,
            "annual_cost_year2": 0.0,
            "annual_cost_year3": 0.0,
            "current_annual_cost": 0.0,
            "pricing_available": False,
            "pricing_model": "per_vcpu" if engine_lower != 'eks' else "per_cluster",
        }
        
        # EKS uses per-cluster pricing (flat rate)
        if engine_lower == 'eks':
            result["pricing_available"] = True
            
            # EKS extended support is flat rate: $0.60/cluster/hour (no Year 1/2/3 tiers)
            # Standard support is $0.10/cluster/hour
            extended_hourly = EKS_EXTENDED_SUPPORT_PRICING["extended"]
            monthly_cost = cluster_count * extended_hourly * hours_per_month
            
            # EKS has same rate for all extended support period (no year tiers)
            result["monthly_cost_year1"] = monthly_cost
            result["monthly_cost_year2"] = monthly_cost  # Same rate
            result["monthly_cost_year3"] = monthly_cost  # Same rate (though EKS only has 12 months)
            
            result["annual_cost_year1"] = monthly_cost * 12
            result["annual_cost_year2"] = monthly_cost * 12
            result["annual_cost_year3"] = monthly_cost * 12
        else:
            # Database engines use per-vCPU pricing
            # Get vCPU count
            if vcpu_count:
                result["vcpu_count"] = vcpu_count
            elif instance_type:
                result["vcpu_count"] = INSTANCE_VCPU_MAP.get(instance_type.lower(), 2)
            else:
                result["vcpu_count"] = 2  # Default assumption
            
            vcpus = result["vcpu_count"]
            
            # Get pricing for this engine
            pricing = EXTENDED_SUPPORT_PRICING.get(engine_lower)
            
            if pricing and vcpus > 0:
                result["pricing_available"] = True
                
                # Calculate costs per year
                result["monthly_cost_year1"] = vcpus * pricing["year1"] * hours_per_month
                result["monthly_cost_year2"] = vcpus * pricing["year2"] * hours_per_month
                result["monthly_cost_year3"] = vcpus * pricing["year3"] * hours_per_month
                
                result["annual_cost_year1"] = result["monthly_cost_year1"] * 12
                result["annual_cost_year2"] = result["monthly_cost_year2"] * 12
                result["annual_cost_year3"] = result["monthly_cost_year3"] * 12
        
        # Determine current year and cost
        if dates:
            current_year = dates.get_current_year(reference_date)
            result["current_year"] = current_year
            result["in_extended_support"] = current_year is not None
            
            if current_year == 1:
                result["current_monthly_cost"] = result["monthly_cost_year1"]
                result["current_annual_cost"] = result["annual_cost_year1"]
            elif current_year == 2:
                result["current_monthly_cost"] = result["monthly_cost_year2"]
                result["current_annual_cost"] = result["annual_cost_year2"]
            elif current_year == 3:
                result["current_monthly_cost"] = result["monthly_cost_year3"]
                result["current_annual_cost"] = result["annual_cost_year3"]
        
        return result
    
    def get_all_static_entries(self) -> List[ExtendedSupportDates]:
        """Get all entries from the static lookup table."""
        results = []
        for (engine, version), data in STATIC_EXTENDED_SUPPORT_DATES.items():
            def parse_date(d):
                return datetime.strptime(d, "%Y-%m-%d").date() if d else None
            
            results.append(ExtendedSupportDates(
                engine=engine,
                version=version,
                standard_support_end=parse_date(data.get("standard_support_end")),
                extended_support_start=parse_date(data.get("extended_support_start")),
                extended_support_year1_start=parse_date(data.get("extended_support_year1_start")),
                extended_support_year3_start=parse_date(data.get("extended_support_year3_start")),
                extended_support_end=parse_date(data.get("extended_support_end")),
                source="Static Lookup",
            ))
        return results


# Convenience function for direct use
def get_extended_support_info(
    engine: str,
    version: str,
    instance_type: Optional[str] = None,
    session: Optional[Any] = None,
) -> Dict[str, Any]:
    """Get extended support dates and cost estimate.
    
    Args:
        engine: Engine name
        version: Engine version
        instance_type: Optional instance type for cost calculation
        session: Optional boto3 session
        
    Returns:
        Dict with dates and cost information.
    """
    lookup = ExtendedSupportLookup(session)
    dates = lookup.get_extended_support_dates(engine, version)
    cost = lookup.estimate_monthly_cost(engine, version, instance_type)
    
    return {
        "dates": {
            "standard_support_end": str(dates.standard_support_end) if dates and dates.standard_support_end else None,
            "extended_support_start": str(dates.extended_support_start) if dates and dates.extended_support_start else None,
            "extended_support_year1_start": str(dates.extended_support_year1_start) if dates and dates.extended_support_year1_start else None,
            "extended_support_year3_start": str(dates.extended_support_year3_start) if dates and dates.extended_support_year3_start else None,
            "extended_support_end": str(dates.extended_support_end) if dates and dates.extended_support_end else None,
        } if dates else None,
        "cost": cost,
    }


if __name__ == "__main__":
    # Test the lookup
    import json
    
    print("Extended Support Lookup Test")
    print("=" * 60)
    
    lookup = ExtendedSupportLookup()
    
    # Database test cases
    db_test_cases = [
        ("aurora-mysql", "5.7", "db.r5.large"),
        ("aurora-postgresql", "11", "db.r6g.xlarge"),
        ("mysql", "5.7", "db.t3.medium"),
        ("postgres", "12", "db.m5.large"),
        ("docdb", "4.0", "db.r5.large"),
    ]
    
    print("\n--- Database Extended Support ---")
    for engine, version, instance_type in db_test_cases:
        print(f"\n{engine} {version} ({instance_type}):")
        
        dates = lookup.get_extended_support_dates(engine, version)
        if dates:
            print(f"  Standard End: {dates.standard_support_end}")
            print(f"  Extended Start: {dates.extended_support_start}")
            print(f"  Year 1 Start: {dates.extended_support_year1_start}")
            print(f"  Year 3 Start: {dates.extended_support_year3_start}")
            print(f"  Extended End: {dates.extended_support_end}")
            print(f"  Current Year: {dates.get_current_year()}")
        
        cost = lookup.estimate_monthly_cost(engine, version, instance_type)
        print(f"  In Extended Support: {cost['in_extended_support']}")
        print(f"  Current Monthly Cost: ${cost['current_monthly_cost']:.2f}")
        print(f"  Year 1 Monthly: ${cost['monthly_cost_year1']:.2f}")
        print(f"  Year 2 Monthly: ${cost['monthly_cost_year2']:.2f}")
        print(f"  Year 3 Monthly: ${cost['monthly_cost_year3']:.2f}")
    
    # EKS test cases
    eks_test_cases = [
        ("eks", "1.29", 1),
        ("eks", "1.30", 3),
        ("eks", "1.31", 5),
    ]
    
    print("\n--- EKS Extended Support ---")
    for engine, version, cluster_count in eks_test_cases:
        print(f"\n{engine} {version} ({cluster_count} cluster(s)):")
        
        dates = lookup.get_extended_support_dates(engine, version)
        if dates:
            print(f"  Standard End: {dates.standard_support_end}")
            print(f"  Extended Start: {dates.extended_support_start}")
            print(f"  Extended End: {dates.extended_support_end}")
            print(f"  Current Year: {dates.get_current_year()}")
        
        cost = lookup.estimate_monthly_cost(engine, version, cluster_count=cluster_count)
        print(f"  Pricing Model: {cost['pricing_model']}")
        print(f"  In Extended Support: {cost['in_extended_support']}")
        print(f"  Monthly Cost: ${cost['monthly_cost_year1']:.2f} (flat rate)")
        print(f"  Annual Cost: ${cost['annual_cost_year1']:.2f}")
