"""Report Generator for EndOfSupportTool.

Generates hierarchically grouped reports from classified resources.
Groups resources by: Account -> Service -> Engine -> Version
"""

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional

# Handle imports for both package and frozen executable modes
try:
    from .models import (
        Resource,
        ReportFilters,
        SupportStatus,
        VersionGroup,
        EngineGroup,
        ServiceGroup,
        AccountGroup,
        Report,
    )
    from .classifier import ResourceClassifier
except ImportError:
    from models import (
        Resource,
        ReportFilters,
        SupportStatus,
        VersionGroup,
        EngineGroup,
        ServiceGroup,
        AccountGroup,
        Report,
    )
    from classifier import ResourceClassifier


class ReportGenerator:
    """Generates hierarchically grouped reports from classified resources.
    
    Groups resources by Account -> Service -> Engine -> Version and
    calculates status counts at each level.
    """
    
    def __init__(self, resources: List[Resource], classifier: ResourceClassifier):
        """Initialize with resources and classifier.
        
        Args:
            resources: List of Resource objects to include in the report.
            classifier: ResourceClassifier instance for classifying resources.
        """
        self.resources = resources
        self.classifier = classifier
    
    def generate(self, filters: Optional[ReportFilters] = None) -> Report:
        """Generate a grouped report with optional filtering.
        
        Groups resources by: Account -> Service -> Engine -> Version
        Calculates status counts at each grouping level.
        
        Args:
            filters: Optional ReportFilters to apply before grouping.
            
        Returns:
            Report object with hierarchical grouping and totals.
        """
        # Classify all resources first
        for resource in self.resources:
            self.classifier.classify(resource)
        
        # Apply filters if provided
        filtered_resources = self._apply_filters(self.resources, filters)
        
        # Group resources hierarchically
        accounts = self._group_resources(filtered_resources)
        
        # Calculate total counts
        total_counts = self._calculate_total_counts(filtered_resources)
        
        return Report(
            accounts=accounts,
            total_counts=total_counts,
            total_resources=len(filtered_resources),
            generated_at=date.today(),
        )
    
    def _apply_filters(
        self, 
        resources: List[Resource], 
        filters: Optional[ReportFilters]
    ) -> List[Resource]:
        """Apply status, account, and service filters.
        
        Filters are combined with AND logic - a resource must match
        all specified filters to be included.
        
        Args:
            resources: List of resources to filter.
            filters: Optional filters to apply.
            
        Returns:
            Filtered list of resources.
        """
        if filters is None:
            return resources
        
        result = resources
        
        # Filter by status
        if filters.statuses:
            result = [r for r in result if r.status in filters.statuses]
        
        # Filter by account
        if filters.accounts:
            result = [r for r in result if r.account in filters.accounts]
        
        # Filter by service
        if filters.services:
            result = [r for r in result if r.service in filters.services]
        
        return result
    
    def _group_resources(
        self, 
        resources: List[Resource]
    ) -> Dict[str, AccountGroup]:
        """Create hierarchical grouping structure.
        
        Groups resources by: Account -> Service -> Engine -> Version
        Calculates status counts at each level.
        
        Args:
            resources: List of resources to group.
            
        Returns:
            Dictionary mapping account names to AccountGroup objects.
        """
        accounts: Dict[str, AccountGroup] = {}
        
        for resource in resources:
            # Get or create account group
            account_name = resource.account
            if account_name not in accounts:
                accounts[account_name] = AccountGroup(
                    account=account_name,
                    services={},
                    status_counts=defaultdict(int),
                )
            account_group = accounts[account_name]
            
            # Get or create service group
            service_name = resource.service
            if service_name not in account_group.services:
                account_group.services[service_name] = ServiceGroup(
                    service=service_name,
                    engines={},
                    status_counts=defaultdict(int),
                )
            service_group = account_group.services[service_name]
            
            # Get or create engine group
            engine_name = resource.engine or "Unknown"
            if engine_name not in service_group.engines:
                service_group.engines[engine_name] = EngineGroup(
                    engine=engine_name,
                    versions={},
                    status_counts=defaultdict(int),
                )
            engine_group = service_group.engines[engine_name]
            
            # Get or create version group
            version_name = resource.version
            if version_name not in engine_group.versions:
                engine_group.versions[version_name] = VersionGroup(
                    version=version_name,
                    resources=[],
                    status_counts=defaultdict(int),
                )
            version_group = engine_group.versions[version_name]
            
            # Add resource to version group
            version_group.resources.append(resource)
            
            # Update status counts at all levels
            status = resource.status
            if status:
                version_group.status_counts[status] += 1
                engine_group.status_counts[status] += 1
                service_group.status_counts[status] += 1
                account_group.status_counts[status] += 1
        
        # Convert defaultdicts to regular dicts for cleaner output
        for account_group in accounts.values():
            account_group.status_counts = dict(account_group.status_counts)
            for service_group in account_group.services.values():
                service_group.status_counts = dict(service_group.status_counts)
                for engine_group in service_group.engines.values():
                    engine_group.status_counts = dict(engine_group.status_counts)
                    for version_group in engine_group.versions.values():
                        version_group.status_counts = dict(version_group.status_counts)
        
        return accounts
    
    def _calculate_total_counts(
        self, 
        resources: List[Resource]
    ) -> Dict[SupportStatus, int]:
        """Calculate total status counts across all resources.
        
        Args:
            resources: List of resources to count.
            
        Returns:
            Dictionary mapping SupportStatus to count.
        """
        counts: Dict[SupportStatus, int] = defaultdict(int)
        
        for resource in resources:
            if resource.status:
                counts[resource.status] += 1
        
        return dict(counts)
