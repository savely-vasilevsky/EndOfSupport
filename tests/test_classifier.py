"""Tests for ResourceClassifier.

Property-based tests for classification logic.
Feature: end-of-support-tool
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Add tests directory to path for conftest imports
sys.path.insert(0, str(Path(__file__).parent))

from src.classifier import ResourceClassifier
from src.models import Resource, SupportStatus

# Import strategies from conftest
from tests.conftest import resource_strategy, valid_date_strategy, safe_text_strategy


class TestResourceClassifierBasic:
    """Basic unit tests for ResourceClassifier."""
    
    def test_default_threshold(self):
        """Test default days threshold is 90."""
        classifier = ResourceClassifier()
        assert classifier.days_threshold == 90
    
    def test_custom_threshold(self):
        """Test custom days threshold."""
        classifier = ResourceClassifier(days_threshold=30)
        assert classifier.days_threshold == 30
    
    def test_classify_out_of_support_by_insights(self):
        """Test classification when insights indicate out of support."""
        classifier = ResourceClassifier()
        resource = _create_resource(insights="Out of support.")
        
        status = classifier.classify(resource)
        
        assert status == SupportStatus.OUT_OF_SUPPORT
        assert resource.status == SupportStatus.OUT_OF_SUPPORT
    
    def test_classify_out_of_support_by_deprecated(self):
        """Test classification when end_of_support_raw is Deprecated."""
        classifier = ResourceClassifier()
        resource = _create_resource(end_of_support_raw="Deprecated")
        
        status = classifier.classify(resource)
        
        assert status == SupportStatus.OUT_OF_SUPPORT
    
    def test_classify_out_of_support_by_past_date(self):
        """Test classification when end_of_support date is in the past."""
        classifier = ResourceClassifier()
        past_date = date.today() - timedelta(days=30)
        resource = _create_resource(end_of_support=past_date)
        
        status = classifier.classify(resource)
        
        assert status == SupportStatus.OUT_OF_SUPPORT
    
    def test_classify_extended_support(self):
        """Test classification when in extended support period."""
        classifier = ResourceClassifier()
        today = date.today()
        resource = _create_resource(
            extended_support_start=today - timedelta(days=30),
            extended_support_end=today + timedelta(days=365),
            end_of_support=today + timedelta(days=365)
        )
        
        status = classifier.classify(resource)
        
        assert status == SupportStatus.EXTENDED_SUPPORT_YEAR_1
    
    def test_classify_approaching_eos(self):
        """Test classification when approaching end of support."""
        classifier = ResourceClassifier(days_threshold=90)
        today = date.today()
        resource = _create_resource(
            end_of_support=today + timedelta(days=45),
            insights="Supported"
        )
        
        status = classifier.classify(resource)
        
        assert status == SupportStatus.APPROACHING_EOS
    
    def test_classify_supported(self):
        """Test classification when fully supported."""
        classifier = ResourceClassifier(days_threshold=90)
        today = date.today()
        resource = _create_resource(
            end_of_support=today + timedelta(days=365),
            insights="Supported"
        )
        
        status = classifier.classify(resource)
        
        assert status == SupportStatus.SUPPORTED
    
    def test_days_to_eos_calculated(self):
        """Test that days_to_eos is calculated correctly."""
        classifier = ResourceClassifier()
        today = date.today()
        future_date = today + timedelta(days=100)
        resource = _create_resource(end_of_support=future_date)
        
        classifier.classify(resource, reference_date=today)
        
        assert resource.days_to_eos == 100
    
    def test_classify_supported_when_extended_support_start_in_future(self):
        """Test classification when extended support start date is in the future.
        
        Even if end_of_support is in the past, if extended_support_start is in
        the future, the resource should be classified as SUPPORTED because
        extended support hasn't started yet.
        """
        classifier = ResourceClassifier()
        today = date.today()
        
        # Scenario: Aurora PostgreSQL 15.7
        # - End of Support: Nov-25 (past)
        # - Extended Support Start: Mar-28 (future)
        # - Should be SUPPORTED, not OUT_OF_SUPPORT
        resource = _create_resource(
            service="RDS",
            engine="aurora-postgresql",
            version="15.7",
            end_of_support=date(2025, 11, 30),  # Past date
            end_of_support_raw="Nov-25",
            extended_support_start=date(2028, 3, 1),  # Future date
            extended_support_year1_start=date(2028, 3, 1),
            extended_support_year2_start=date(2030, 3, 1),
            extended_support_end=date(2031, 2, 28),
            insights="Out of support."  # Even with this, should be SUPPORTED
        )
        
        # Use a reference date of Feb 2026 (after end_of_support but before extended_support_start)
        reference_date = date(2026, 2, 18)
        status = classifier.classify(resource, reference_date=reference_date)
        
        assert status == SupportStatus.SUPPORTED, (
            f"Resource with extended_support_start in future should be SUPPORTED, got {status}"
        )
    
    def test_classify_extended_year1_when_extended_support_started(self):
        """Test classification when extended support has started.
        
        If extended_support_start is in the past, the resource should be
        in Extended Support Year 1.
        """
        classifier = ResourceClassifier()
        
        resource = _create_resource(
            service="RDS",
            engine="aurora-postgresql",
            version="15.7",
            end_of_support=date(2025, 11, 30),
            extended_support_start=date(2028, 3, 1),
            extended_support_year1_start=date(2028, 3, 1),
            extended_support_year2_start=date(2030, 3, 1),
            extended_support_end=date(2031, 2, 28),
        )
        
        # Use a reference date of Apr 2028 (after extended_support_start)
        reference_date = date(2028, 4, 1)
        status = classifier.classify(resource, reference_date=reference_date)
        
        assert status == SupportStatus.EXTENDED_SUPPORT_YEAR_1, (
            f"Resource with extended_support_start in past should be EXTENDED_SUPPORT_YEAR_1, got {status}"
        )
    
    def test_classify_approaching_eos_with_future_extended_support(self):
        """Test classification when EOS is approaching and extended support starts after EOS.
        
        EKS clusters with:
        - End-of-Support: 22-Mar-26 (future, within 90 days)
        - Extended Support Start: 23-Mar-26 (future, after EOS)
        Should be APPROACHING_EOS, not SUPPORTED.
        """
        classifier = ResourceClassifier(days_threshold=90)
        
        # Scenario: EKS Kubernetes 1.32
        # - End of Support: Mar-22-26 (future, 32 days away)
        # - Extended Support Start: Mar-23-26 (future)
        # - Should be APPROACHING_EOS
        resource = _create_resource(
            service="EKS",
            engine="Kubernetes",
            version="1.32",
            end_of_support=date(2026, 3, 22),  # Future date, within threshold
            end_of_support_raw="22-Mar-26",
            extended_support_start=date(2026, 3, 23),  # Future date, after EOS
            extended_support_year1_start=date(2026, 3, 23),
            extended_support_end=date(2027, 3, 22),
            insights="32 days to end-of-support."
        )
        
        # Use a reference date of Feb 18, 2026 (32 days before EOS)
        reference_date = date(2026, 2, 18)
        status = classifier.classify(resource, reference_date=reference_date)
        
        assert status == SupportStatus.APPROACHING_EOS, (
            f"EKS cluster with EOS in 32 days should be APPROACHING_EOS, got {status}"
        )


class TestResourceClassifierProperties:
    """Property-based tests for ResourceClassifier.
    
    Feature: end-of-support-tool
    """
    
    @given(resource=resource_strategy(), reference_date=valid_date_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_property_4_classification_determinism(self, resource, reference_date):
        """Property 4: Classification Determinism
        
        *For any* Resource with the same field values, the ResourceClassifier 
        SHALL always produce the same SupportStatus classification.
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
        """
        classifier = ResourceClassifier(days_threshold=90)
        
        # Classify the same resource twice
        status1 = classifier.classify(resource, reference_date=reference_date)
        
        # Reset status to ensure fresh classification
        resource.status = None
        resource.days_to_eos = None
        
        status2 = classifier.classify(resource, reference_date=reference_date)
        
        assert status1 == status2, (
            f"Classification not deterministic: {status1} != {status2}"
        )
    
    @given(
        reference_date=valid_date_strategy(),
        days_in_past=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=100)
    def test_property_5_out_of_support_classification_completeness(
        self, reference_date, days_in_past
    ):
        """Property 5: Out-of-Support Classification Completeness
        
        *For any* Resource where either (a) Insights contains "Out of support", 
        (b) End-of-Support is "Deprecated", or (c) End-of-Support date is before 
        today, the classification SHALL be OUT_OF_SUPPORT.
        
        **Validates: Requirements 2.1, 2.2, 2.6**
        """
        classifier = ResourceClassifier()
        
        # Test case (a): Insights contains "Out of support"
        resource_a = _create_resource(insights="Out of support.")
        status_a = classifier.classify(resource_a, reference_date=reference_date)
        assert status_a == SupportStatus.OUT_OF_SUPPORT, (
            "Resource with 'Out of support' in insights should be OUT_OF_SUPPORT"
        )
        
        # Test case (b): End-of-Support is "Deprecated"
        resource_b = _create_resource(end_of_support_raw="Deprecated")
        status_b = classifier.classify(resource_b, reference_date=reference_date)
        assert status_b == SupportStatus.OUT_OF_SUPPORT, (
            "Resource with 'Deprecated' end_of_support_raw should be OUT_OF_SUPPORT"
        )
        
        # Test case (c): End-of-Support date is in the past
        past_date = reference_date - timedelta(days=days_in_past)
        resource_c = _create_resource(
            end_of_support=past_date,
            end_of_support_raw=past_date.strftime('%d-%b-%y'),
            insights="Supported"  # Even with supported insights, past date wins
        )
        status_c = classifier.classify(resource_c, reference_date=reference_date)
        assert status_c == SupportStatus.OUT_OF_SUPPORT, (
            f"Resource with past end_of_support ({past_date}) should be OUT_OF_SUPPORT"
        )
    
    @given(
        reference_date=valid_date_strategy(),
        days_until_eos=st.integers(min_value=1, max_value=89),
        threshold=st.integers(min_value=90, max_value=365)
    )
    @settings(max_examples=100)
    def test_property_6_approaching_eos_threshold_correctness(
        self, reference_date, days_until_eos, threshold
    ):
        """Property 6: Approaching EOS Threshold Correctness
        
        *For any* Resource with an End-of-Support date that is (today + 1) to 
        (today + days_threshold) days in the future, and not in extended support, 
        the classification SHALL be APPROACHING_EOS.
        
        **Validates: Requirements 2.4**
        """
        # Ensure days_until_eos is within threshold
        assume(days_until_eos <= threshold)
        
        classifier = ResourceClassifier(days_threshold=threshold)
        
        eos_date = reference_date + timedelta(days=days_until_eos)
        resource = _create_resource(
            end_of_support=eos_date,
            end_of_support_raw=eos_date.strftime('%d-%b-%y'),
            insights="Supported",
            # Ensure not in extended support
            extended_support_start=None,
            extended_support_end=None
        )
        
        status = classifier.classify(resource, reference_date=reference_date)
        
        assert status == SupportStatus.APPROACHING_EOS, (
            f"Resource with {days_until_eos} days to EOS (threshold={threshold}) "
            f"should be APPROACHING_EOS, got {status}"
        )


def _create_resource(
    account: str = "TestAccount",
    payer_id: str = "123456789",
    service: str = "Lambda",
    resource_type: str = "Function",
    resource_arn: str = "arn:aws:lambda:us-east-1:123456789:function:test",
    resource_name: str = "test-function",
    region: str = "us-east-1",
    engine: str = None,
    version: str = "3.9",
    end_of_support: date = None,
    end_of_support_raw: str = "Supported",
    auto_minor_version_upgrade: bool = None,
    extended_support_start: date = None,
    extended_support_year1_start: date = None,
    extended_support_year2_start: date = None,
    extended_support_year3_start: date = None,
    extended_support_end: date = None,
    insights: str = "Supported"
) -> Resource:
    """Helper to create Resource objects for testing."""
    return Resource(
        account=account,
        payer_id=payer_id,
        service=service,
        resource_type=resource_type,
        resource_arn=resource_arn,
        resource_name=resource_name,
        region=region,
        engine=engine,
        version=version,
        end_of_support=end_of_support,
        end_of_support_raw=end_of_support_raw,
        auto_minor_version_upgrade=auto_minor_version_upgrade,
        extended_support_start=extended_support_start,
        extended_support_year1_start=extended_support_year1_start,
        extended_support_year2_start=extended_support_year2_start,
        extended_support_year3_start=extended_support_year3_start,
        extended_support_end=extended_support_end,
        insights=insights,
    )
