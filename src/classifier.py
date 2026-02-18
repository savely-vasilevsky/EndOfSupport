"""Resource Classifier for EndOfSupportTool.

Classifies resources based on their support status using date comparisons
and insight text analysis.
"""

from datetime import date
from typing import Optional

# Handle imports for both package and frozen executable modes
try:
    from .models import Resource, SupportStatus
    from .extended_support_lookup import get_extended_support_dates
except ImportError:
    from models import Resource, SupportStatus
    from extended_support_lookup import get_extended_support_dates


class ResourceClassifier:
    """Classifies resources based on their support lifecycle status.
    
    Classification logic follows this precedence order:
    1. If End-of-Support is "Deprecated" -> OUT_OF_SUPPORT
    2. If Extended Support End Date is in the past -> OUT_OF_SUPPORT
    3. If Extended Support Year 3 Start Date is past/present (and ext end is future/none) -> EXTENDED_SUPPORT_YEAR_3
    4. If Extended Support Year 2 Start Date is past/present (and year 3 not started) -> EXTENDED_SUPPORT_YEAR_2
    5. If Extended Support Start/Year 1 Start Date is past/present (and year 2 not started) -> EXTENDED_SUPPORT_YEAR_1
    6. If Insights contains "Out of support" (and not in extended support) -> OUT_OF_SUPPORT
    7. If no extended support dates AND End-of-Support date is in the past -> OUT_OF_SUPPORT
    8. If End-of-Support date is within days_threshold -> APPROACHING_EOS
    9. Otherwise -> SUPPORTED
    
    Note: Resources are automatically enriched with extended support dates from
    the static lookup table if they're missing from the CSV input.
    """
    
    DEFAULT_DAYS_THRESHOLD = 90
    
    def __init__(self, days_threshold: int = DEFAULT_DAYS_THRESHOLD):
        """Initialize classifier with configurable threshold.
        
        Args:
            days_threshold: Number of days to consider as "approaching" 
                          end-of-support. Default is 90 days.
        """
        self.days_threshold = days_threshold
    
    def _enrich_extended_support_dates(self, resource: Resource) -> None:
        """Enrich resource with extended support dates from static lookup if missing.
        
        This allows resources loaded from CSV (which may not have extended support
        dates populated) to be correctly classified based on the static lookup table.
        
        Important: Only enriches if the lookup table's standard_support_end matches
        the resource's end_of_support date (within a reasonable tolerance), to avoid
        applying incorrect dates when the CSV has different EOS dates.
        
        Args:
            resource: The Resource object to enrich.
        """
        # Only enrich if extended support dates are missing
        if (resource.extended_support_start is not None or 
            resource.extended_support_year1_start is not None or
            resource.extended_support_end is not None):
            return
        
        # Look up dates based on engine and version
        engine = resource.engine or ''
        version = resource.version or ''
        
        if not engine or not version:
            return
        
        dates = get_extended_support_dates(engine, version)
        if dates is None:
            return
        
        # Only enrich if the lookup's standard_support_end matches the resource's end_of_support
        # This prevents applying incorrect extended support dates when the CSV has different EOS dates
        if dates.standard_support_end is not None and resource.end_of_support is not None:
            # Allow up to 7 days tolerance for date matching
            days_diff = abs((dates.standard_support_end - resource.end_of_support).days)
            if days_diff > 7:
                # Dates don't match - don't enrich with potentially incorrect data
                return
        
        # Enrich the resource with lookup dates
        resource.extended_support_start = dates.extended_support_start
        resource.extended_support_year1_start = dates.extended_support_year1_start
        resource.extended_support_year3_start = dates.extended_support_year3_start
        resource.extended_support_end = dates.extended_support_end
    
    def classify(self, resource: Resource, reference_date: Optional[date] = None) -> SupportStatus:
        """Determine the support status of a resource.
        
        Applies classification logic in precedence order and also
        calculates days_to_eos for the resource.
        
        Args:
            resource: The Resource object to classify.
            reference_date: Date to use for comparisons. Defaults to today.
            
        Returns:
            SupportStatus enum value indicating the resource's status.
        """
        today = reference_date or date.today()
        
        # Enrich resource with extended support dates from static lookup if missing
        self._enrich_extended_support_dates(resource)
        
        # Calculate days to EOS if we have a valid end_of_support date
        if resource.end_of_support is not None:
            resource.days_to_eos = (resource.end_of_support - today).days
        else:
            resource.days_to_eos = None
        
        # 1. Check if End-of-Support raw value is "Deprecated"
        if self._is_deprecated(resource.end_of_support_raw):
            resource.status = SupportStatus.OUT_OF_SUPPORT
            return SupportStatus.OUT_OF_SUPPORT
        
        # 2. Check if Extended Support End Date is in the past
        if resource.extended_support_end is not None and resource.extended_support_end < today:
            resource.status = SupportStatus.OUT_OF_SUPPORT
            return SupportStatus.OUT_OF_SUPPORT
        
        # 3. Check if in Extended Support Year 3
        if self._is_in_extended_support_year_3(resource, today):
            resource.status = SupportStatus.EXTENDED_SUPPORT_YEAR_3
            return SupportStatus.EXTENDED_SUPPORT_YEAR_3
        
        # 4. Check if in Extended Support Year 2
        if self._is_in_extended_support_year_2(resource, today):
            resource.status = SupportStatus.EXTENDED_SUPPORT_YEAR_2
            return SupportStatus.EXTENDED_SUPPORT_YEAR_2
        
        # 5. Check if in Extended Support Year 1
        if self._is_in_extended_support_year_1(resource, today):
            resource.status = SupportStatus.EXTENDED_SUPPORT_YEAR_1
            return SupportStatus.EXTENDED_SUPPORT_YEAR_1
        
        # 6. Check if Extended Support Start Date is in the future - resource is still SUPPORTED
        # This handles the case where end_of_support is past but extended support hasn't started yet
        if self._is_before_extended_support(resource, today):
            resource.status = SupportStatus.SUPPORTED
            return SupportStatus.SUPPORTED
        
        # 7. Check if Insights contains "Out of support" (only if not in extended support)
        if self._insights_indicate_out_of_support(resource.insights):
            resource.status = SupportStatus.OUT_OF_SUPPORT
            return SupportStatus.OUT_OF_SUPPORT
        
        # 8. Check if no extended support dates AND End-of-Support date is in the past
        if not self._has_extended_support_dates(resource):
            if resource.end_of_support is not None and resource.end_of_support < today:
                resource.status = SupportStatus.OUT_OF_SUPPORT
                return SupportStatus.OUT_OF_SUPPORT
        
        # 9. Check if End-of-Support date is within threshold
        if self._is_approaching_eos(resource, today):
            resource.status = SupportStatus.APPROACHING_EOS
            return SupportStatus.APPROACHING_EOS
        
        # 10. Check if Insights indicate supported status
        if self._insights_indicate_supported(resource.insights):
            resource.status = SupportStatus.SUPPORTED
            return SupportStatus.SUPPORTED
        
        # Default: SUPPORTED
        resource.status = SupportStatus.SUPPORTED
        return SupportStatus.SUPPORTED
    
    def _is_before_extended_support(self, resource: Resource, today: date) -> bool:
        """Check if resource is before extended support period starts.
        
        If extended support start date is defined and in the future,
        AND the end_of_support date is in the past, the resource is in the
        "gap" period between standard support ending and extended support starting.
        This is still considered SUPPORTED status.
        
        Note: If end_of_support is in the future (approaching), we should NOT
        return True here - let the APPROACHING_EOS check handle it instead.
        
        Args:
            resource: The Resource to check.
            today: Reference date for comparison.
            
        Returns:
            True if in the gap between EOS (past) and extended support start (future).
        """
        # Only applies if end_of_support is in the past
        # If end_of_support is in the future, let APPROACHING_EOS check handle it
        if resource.end_of_support is not None and resource.end_of_support >= today:
            return False
        
        # Check extended_support_start (general start date)
        if resource.extended_support_start is not None:
            if resource.extended_support_start > today:
                return True
        
        # Check extended_support_year1_start as fallback
        if resource.extended_support_year1_start is not None:
            if resource.extended_support_year1_start > today:
                return True
        
        return False
    
    def _insights_indicate_out_of_support(self, insights: str) -> bool:
        """Check if insights text indicates out of support status.
        
        Args:
            insights: The insights string from the resource.
            
        Returns:
            True if insights indicate out of support.
        """
        if not insights:
            return False
        return "out of support" in insights.lower()
    
    def _is_deprecated(self, end_of_support_raw: str) -> bool:
        """Check if the raw end-of-support value indicates deprecated.
        
        Args:
            end_of_support_raw: The raw string value from CSV.
            
        Returns:
            True if the value is "Deprecated".
        """
        if not end_of_support_raw:
            return False
        return end_of_support_raw.lower().strip() == "deprecated"
    
    def _has_extended_support_dates(self, resource: Resource) -> bool:
        """Check if resource has any extended support dates defined.
        
        Args:
            resource: The Resource to check.
            
        Returns:
            True if any extended support date is set.
        """
        return any([
            resource.extended_support_start is not None,
            resource.extended_support_year1_start is not None,
            resource.extended_support_year2_start is not None,
            resource.extended_support_year3_start is not None,
            resource.extended_support_end is not None,
        ])
    
    def _is_in_extended_support_year_3(self, resource: Resource, today: date) -> bool:
        """Check if resource is currently in Extended Support Year 3.
        
        A resource is in Year 3 if:
        - Extended Support Year 3 Start Date is in the past or present, AND
        - Extended Support End Date is in the future or not set
        
        Args:
            resource: The Resource to check.
            today: Reference date for comparison.
            
        Returns:
            True if resource is in Extended Support Year 3.
        """
        # Must have Year 3 start date
        if resource.extended_support_year3_start is None:
            return False
        
        # Year 3 must have started (start date <= today)
        if resource.extended_support_year3_start > today:
            return False
        
        # If there's an end date, it must be in the future or today
        if resource.extended_support_end is not None:
            if resource.extended_support_end < today:
                return False
        
        return True
    
    def _is_in_extended_support_year_2(self, resource: Resource, today: date) -> bool:
        """Check if resource is currently in Extended Support Year 2.
        
        A resource is in Year 2 if:
        - Year 1 has started (extended_support_start or year1_start is past), AND
        - Year 3 has NOT started yet (year3_start is in the future), AND
        - We're past the first year of extended support
        
        Since there's no explicit Year 2 start date in the CSV, Year 2 is calculated as:
        - 1 year after Year 1 start date, until Year 3 starts
        
        Args:
            resource: The Resource to check.
            today: Reference date for comparison.
            
        Returns:
            True if resource is in Extended Support Year 2.
        """
        # If there's an explicit Year 2 start date, use it
        if resource.extended_support_year2_start is not None:
            if resource.extended_support_year2_start > today:
                return False
            # Year 3 must not have started yet (if defined)
            if resource.extended_support_year3_start is not None:
                if resource.extended_support_year3_start <= today:
                    return False
            return True
        
        # Calculate Year 2 based on Year 1 start + 1 year
        year1_start = resource.extended_support_year1_start or resource.extended_support_start
        if year1_start is None:
            return False
        
        # Year 2 starts 1 year after Year 1
        from datetime import timedelta
        year2_start = date(year1_start.year + 1, year1_start.month, year1_start.day)
        
        # Must be in Year 2 period (after year2_start)
        if today < year2_start:
            return False
        
        # Year 3 must not have started yet
        if resource.extended_support_year3_start is not None:
            if resource.extended_support_year3_start <= today:
                return False
        else:
            # If no Year 3 defined, Year 2 lasts for 1 year
            year3_start = date(year2_start.year + 1, year2_start.month, year2_start.day)
            if today >= year3_start:
                return False
        
        return True
    
    def _is_in_extended_support_year_1(self, resource: Resource, today: date) -> bool:
        """Check if resource is currently in Extended Support Year 1.
        
        A resource is in Year 1 if:
        - Extended Support Start Date OR Year 1 Start Date is in the past or present, AND
        - We're still within the first year of extended support (before Year 2 starts)
        
        Args:
            resource: The Resource to check.
            today: Reference date for comparison.
            
        Returns:
            True if resource is in Extended Support Year 1.
        """
        # Check if extended support has started (either via start date or year 1 start)
        year1_start = resource.extended_support_year1_start or resource.extended_support_start
        
        if year1_start is None:
            return False
        
        # Year 1 must have started
        if year1_start > today:
            return False
        
        # Check if Year 2 has started (explicit or calculated)
        if resource.extended_support_year2_start is not None:
            if resource.extended_support_year2_start <= today:
                return False
        else:
            # Year 2 starts 1 year after Year 1
            year2_start = date(year1_start.year + 1, year1_start.month, year1_start.day)
            if today >= year2_start:
                return False
        
        # Also check Year 3 hasn't started
        if resource.extended_support_year3_start is not None:
            if resource.extended_support_year3_start <= today:
                return False
        
        return True
    
    def _is_approaching_eos(self, resource: Resource, today: date) -> bool:
        """Check if resource is approaching end-of-support.
        
        A resource is approaching EOS if:
        - End-of-Support date is set
        - End-of-Support date is in the future
        - End-of-Support date is within days_threshold days
        
        Args:
            resource: The Resource to check.
            today: Reference date for comparison.
            
        Returns:
            True if resource is approaching end-of-support.
        """
        if resource.end_of_support is None:
            return False
        
        days_until_eos = (resource.end_of_support - today).days
        
        # Must be in the future and within threshold
        return 0 < days_until_eos <= self.days_threshold
    
    def _insights_indicate_supported(self, insights: str) -> bool:
        """Check if insights text indicates supported status.
        
        Args:
            insights: The insights string from the resource.
            
        Returns:
            True if insights indicate supported status.
        """
        if not insights:
            return False
        
        insights_lower = insights.lower()
        supported_phrases = [
            "supported",
            "version is not planned for deprecation yet"
        ]
        
        return any(phrase in insights_lower for phrase in supported_phrases)
