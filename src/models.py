"""Data models for EndOfSupportTool."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict


class SupportStatus(Enum):
    """Classification of a resource's support state."""
    SUPPORTED = "Supported"
    APPROACHING_EOS = "Approaching End-of-Support"
    EXTENDED_SUPPORT_YEAR_1 = "Extended Support Y1"
    EXTENDED_SUPPORT_YEAR_2 = "Extended Support Y2"
    EXTENDED_SUPPORT_YEAR_3 = "Extended Support Y3"
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
    extended_support_year2_start: Optional[date]
    extended_support_year3_start: Optional[date]
    extended_support_end: Optional[date]
    insights: str
    status: Optional[SupportStatus] = None
    days_to_eos: Optional[int] = None
    # Cost estimation fields
    instance_type: Optional[str] = None
    est_monthly_ext_support_cost: Optional[str] = None
    est_annual_ext_support_cost: Optional[str] = None


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
class GenerationParameters:
    """Parameters used to generate the report."""
    input_file: str = ""
    output_format: str = ""
    days_threshold: int = 90
    status_filters: Optional[List[str]] = None
    account_filters: Optional[List[str]] = None
    service_filters: Optional[List[str]] = None
    pivot_per_account: bool = False
    include_timeline: bool = True
    
    def to_display_string(self) -> str:
        """Generate a human-readable string of the parameters."""
        parts = []
        
        if self.input_file:
            parts.append(f"Source: {self.input_file}")
        
        parts.append(f"EOS Threshold: {self.days_threshold} days")
        
        if self.status_filters:
            parts.append(f"Status: {', '.join(self.status_filters)}")
        
        if self.account_filters:
            parts.append(f"Accounts: {', '.join(self.account_filters)}")
        
        if self.service_filters:
            parts.append(f"Services: {', '.join(self.service_filters)}")
        
        if self.output_format == "excel":
            if self.pivot_per_account:
                parts.append("Pivot: Per Account")
            if not self.include_timeline:
                parts.append("Timeline: Excluded")
        
        return " | ".join(parts)


@dataclass
class Report:
    """Complete report with hierarchical grouping and totals."""
    accounts: Dict[str, AccountGroup] = field(default_factory=dict)
    total_counts: Dict[SupportStatus, int] = field(default_factory=dict)
    total_resources: int = 0
    generated_at: datetime = field(default_factory=datetime.now)
    generation_params: Optional[GenerationParameters] = None
