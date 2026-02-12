"""
Extended Support Lookup Module

Provides extended support dates from a static lookup table based on AWS documentation.
Used to enrich resources with extended support dates when they're missing from CSV input.
"""

from datetime import date, datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


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


# Static Lookup Table (from AWS Documentation)
# Sources:
# - RDS: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/extended-support-versions.html
# - Aurora: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/extended-support-versions.html
# - EKS: https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html
# - DocumentDB: https://docs.aws.amazon.com/documentdb/latest/developerguide/extended-support.html

STATIC_EXTENDED_SUPPORT_DATES: Dict[Tuple[str, str], Dict[str, Optional[str]]] = {
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
    # EKS has 14 months standard support + 12 months extended support
    # Note: EKS extended support is flat rate, no Year 1/2/3 tiers
    ("eks", "1.29"): {
        "standard_support_end": "2025-03-23",
        "extended_support_start": "2025-03-23",
        "extended_support_year1_start": "2025-03-23",
        "extended_support_year3_start": None,
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

# Engine name normalization mapping
ENGINE_ALIASES = {
    # EKS variations
    'kubernetes': 'eks',
    'elastic kubernetes service (eks)': 'eks',
    'elastic kubernetes service': 'eks',
    # DocumentDB variations  
    'documentdb': 'docdb',
    'amazon documentdb': 'docdb',
    # Aurora variations
    'aurora mysql': 'aurora-mysql',
    'aurora postgresql': 'aurora-postgresql',
    'aurora-postgres': 'aurora-postgresql',
    # RDS variations
    'postgresql': 'postgres',
    'rds mysql': 'mysql',
    'rds postgresql': 'postgres',
    'rds postgres': 'postgres',
}


def _normalize_engine(engine: str) -> str:
    """Normalize engine name to match lookup table keys."""
    if not engine:
        return ''
    engine_lower = engine.lower().strip()
    return ENGINE_ALIASES.get(engine_lower, engine_lower)


def _normalize_version(engine: str, version: str) -> str:
    """Normalize version to match lookup table keys.
    
    For MySQL/Aurora MySQL/DocumentDB/EKS: keep major.minor (e.g., "5.7", "8.0", "4.0", "1.31")
    For PostgreSQL/Aurora PostgreSQL: keep major only (e.g., "11", "12", "13")
    """
    if not version:
        return ''
    
    engine_lower = _normalize_engine(engine)
    parts = version.split('.')
    
    # For these engines, keep major.minor format
    if engine_lower in ('mysql', 'aurora-mysql', 'docdb', 'eks'):
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
        return parts[0]
    
    # For PostgreSQL engines, keep major version only
    return parts[0]


def get_extended_support_dates(engine: str, version: str) -> Optional[ExtendedSupportDates]:
    """Get extended support dates for an engine/version from static lookup.
    
    Args:
        engine: Engine name (e.g., "mysql", "aurora-postgresql", "Kubernetes", "EKS")
        version: Version string (e.g., "5.7", "14", "1.31", "13.15")
        
    Returns:
        ExtendedSupportDates or None if not found.
    """
    normalized_engine = _normalize_engine(engine)
    normalized_version = _normalize_version(engine, version)
    
    lookup_key = (normalized_engine, normalized_version)
    
    if lookup_key not in STATIC_EXTENDED_SUPPORT_DATES:
        return None
    
    static_data = STATIC_EXTENDED_SUPPORT_DATES[lookup_key]
    
    def parse_date(d: Optional[str]) -> Optional[date]:
        if not d:
            return None
        return datetime.strptime(d, "%Y-%m-%d").date()
    
    return ExtendedSupportDates(
        engine=normalized_engine,
        version=normalized_version,
        standard_support_end=parse_date(static_data.get("standard_support_end")),
        extended_support_start=parse_date(static_data.get("extended_support_start")),
        extended_support_year1_start=parse_date(static_data.get("extended_support_year1_start")),
        extended_support_year3_start=parse_date(static_data.get("extended_support_year3_start")),
        extended_support_end=parse_date(static_data.get("extended_support_end")),
        source="Static Lookup",
    )
