"""Data models for EndOfSupportTool."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict


class SupportStatus(Enum):
    """Classification of a resource's support state."""
    SUPPORTED = "Supported"
    APPROACHING_EOS = "Approaching End-of-Support"
    EXTENDED_SUPPORT = "In Extended Support"
    OUT_OF_SUPPORT = "Out of Support"


@dataclass
class Resource:
    """An AWS resource entry from the CSV file."""
    account: str
    payer_id: str
    service: str
    resource_type: str
    resource_arn: str
    resource_name: str
    region: str
    engine: Optional[str]
    version: str
    end_of_support: Optional[date]
    end_of_support_raw: str  # Original string value for display
    auto_minor_version_upgrade: Optional[bool]
    extended_support_start: Optional[date]
    extended_support_year1_start: Optional[date]
    extended_support_year3_start: Optional[date]
    extended_support_end: Optional[date]
    insights: str
    status: Optional[SupportStatus] = None
    days_to_eos: Optional[int] = None


@dataclass
class ReportFilters:
    """Filters to apply when generating reports."""
    statuses: Optional[List[SupportStatus]] = None
    accounts: Optional[List[str]] = None
    services: Optional[List[str]] = None


@dataclass
class VersionGroup:
    """Group of resources with the same version."""
    version: str
    resources: List[Resource] = field(default_factory=list)
    status_counts: Dict[SupportStatus, int] = field(default_factory=dict)


@dataclass
class EngineGroup:
    """Group of resources with the same engine (e.g., python, redis)."""
    engine: str
    versions: Dict[str, VersionGroup] = field(default_factory=dict)
    status_counts: Dict[SupportStatus, int] = field(default_factory=dict)


@dataclass
class ServiceGroup:
    """Group of resources with the same service (e.g., Lambda, RDS)."""
    service: str
    engines: Dict[str, EngineGroup] = field(default_factory=dict)
    status_counts: Dict[SupportStatus, int] = field(default_factory=dict)


@dataclass
class AccountGroup:
    """Group of resources in the same AWS account."""
    account: str
    services: Dict[str, ServiceGroup] = field(default_factory=dict)
    status_counts: Dict[SupportStatus, int] = field(default_factory=dict)


@dataclass
class Report:
    """Complete report with hierarchical grouping and totals."""
    accounts: Dict[str, AccountGroup] = field(default_factory=dict)
    total_counts: Dict[SupportStatus, int] = field(default_factory=dict)
    total_resources: int = 0
    generated_at: datetime = field(default_factory=datetime.now)
