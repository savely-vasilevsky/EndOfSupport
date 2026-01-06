"""Resource Classifier for EndOfSupportTool.

Classifies resources based on their support status using date comparisons
and insight text analysis.
"""

from datetime import date
from typing import Optional

from .models import Resource, SupportStatus


class ResourceClassifier:
    """Classifies resources based on their support lifecycle status.
    
    Classification logic follows this precedence order:
    1. If Insights contains "Out of support" -> OUT_OF_SUPPORT
    2. If End-of-Support is "Deprecated" -> OUT_OF_SUPPORT
    3. If End-of-Support date is in the past -> OUT_OF_SUPPORT
    4. If Extended Support Start Date is past/present -> EXTENDED_SUPPORT
    5. If End-of-Support date is within days_threshold -> APPROACHING_EOS
    6. Otherwise -> SUPPORTED
    """
    
    DEFAULT_DAYS_THRESHOLD = 90
    
    def __init__(self, days_threshold: int = DEFAULT_DAYS_THRESHOLD):
        """Initialize classifier with configurable threshold.
        
        Args:
            days_threshold: Number of days to consider as "approaching" 
                          end-of-support. Default is 90 days.
        """
        self.days_threshold = days_threshold
    
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
        
        # Calculate days to EOS if we have a valid end_of_support date
        if resource.end_of_support is not None:
            resource.days_to_eos = (resource.end_of_support - today).days
        else:
            resource.days_to_eos = None
        
        # 1. Check if Insights contains "Out of support"
        if self._insights_indicate_out_of_support(resource.insights):
            resource.status = SupportStatus.OUT_OF_SUPPORT
            return SupportStatus.OUT_OF_SUPPORT
        
        # 2. Check if End-of-Support raw value is "Deprecated"
        if self._is_deprecated(resource.end_of_support_raw):
            resource.status = SupportStatus.OUT_OF_SUPPORT
            return SupportStatus.OUT_OF_SUPPORT
        
        # 3. Check if End-of-Support date is in the past
        if resource.end_of_support is not None and resource.end_of_support < today:
            resource.status = SupportStatus.OUT_OF_SUPPORT
            return SupportStatus.OUT_OF_SUPPORT
        
        # 4. Check if resource is in extended support period
        if self._is_in_extended_support(resource, today):
            resource.status = SupportStatus.EXTENDED_SUPPORT
            return SupportStatus.EXTENDED_SUPPORT
        
        # 5. Check if End-of-Support date is within threshold
        if self._is_approaching_eos(resource, today):
            resource.status = SupportStatus.APPROACHING_EOS
            return SupportStatus.APPROACHING_EOS
        
        # 6. Check if Insights indicate supported status
        if self._insights_indicate_supported(resource.insights):
            resource.status = SupportStatus.SUPPORTED
            return SupportStatus.SUPPORTED
        
        # Default: SUPPORTED
        resource.status = SupportStatus.SUPPORTED
        return SupportStatus.SUPPORTED
    
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
    
    def _is_in_extended_support(self, resource: Resource, today: date) -> bool:
        """Check if resource is currently in extended support period.
        
        A resource is in extended support if:
        - Extended Support Start Date is in the past or present, AND
        - Extended Support End Date is in the future or not set
        
        Args:
            resource: The Resource to check.
            today: Reference date for comparison.
            
        Returns:
            True if resource is in extended support period.
        """
        # Must have an extended support start date
        if resource.extended_support_start is None:
            return False
        
        # Extended support must have started (start date <= today)
        if resource.extended_support_start > today:
            return False
        
        # If there's an end date, it must be in the future
        if resource.extended_support_end is not None:
            if resource.extended_support_end < today:
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
