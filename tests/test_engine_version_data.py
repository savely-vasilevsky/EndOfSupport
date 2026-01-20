"""Unit tests for EngineVersionData dataclass."""

from datetime import date

import pytest

from src.formatters import EngineVersionData


class TestEngineVersionDataDisplayName:
    """Tests for the display_name property of EngineVersionData.
    
    Validates Requirements 2.2 and 2.3:
    - 2.2: Format as "{engine} {version}" when engine is present
    - 2.3: Display only version when engine is blank or "Unknown"
    """
    
    def test_display_name_with_engine(self):
        """Test display_name returns '{engine} {version}' when engine is present."""
        data = EngineVersionData(
            engine="python",
            version="3.9",
            end_of_support=date(2025, 10, 1),
            extended_support_start=None,
            extended_support_end=None,
            resource_count=5
        )
        assert data.display_name == "python 3.9"
    
    def test_display_name_with_different_engine(self):
        """Test display_name with different engine values."""
        data = EngineVersionData(
            engine="redis",
            version="6.0",
            end_of_support=date(2024, 6, 15),
            extended_support_start=date(2024, 6, 16),
            extended_support_end=date(2025, 6, 15),
            resource_count=3
        )
        assert data.display_name == "redis 6.0"
    
    def test_display_name_with_empty_engine(self):
        """Test display_name returns only version when engine is empty string."""
        data = EngineVersionData(
            engine="",
            version="18.x",
            end_of_support=None,
            extended_support_start=None,
            extended_support_end=None,
            resource_count=2
        )
        assert data.display_name == "18.x"
    
    def test_display_name_with_unknown_engine(self):
        """Test display_name returns only version when engine is 'Unknown'."""
        data = EngineVersionData(
            engine="Unknown",
            version="2.0.1",
            end_of_support=date(2024, 12, 31),
            extended_support_start=None,
            extended_support_end=None,
            resource_count=1
        )
        assert data.display_name == "2.0.1"
    
    def test_display_name_with_none_dates(self):
        """Test display_name works correctly when all dates are None."""
        data = EngineVersionData(
            engine="mysql",
            version="8.0",
            end_of_support=None,
            extended_support_start=None,
            extended_support_end=None,
            resource_count=0
        )
        assert data.display_name == "mysql 8.0"


class TestEngineVersionDataFields:
    """Tests for EngineVersionData dataclass fields."""
    
    def test_all_fields_populated(self):
        """Test that all fields are correctly stored."""
        eos = date(2025, 1, 15)
        ext_start = date(2025, 1, 16)
        ext_end = date(2026, 1, 15)
        
        data = EngineVersionData(
            engine="postgres",
            version="14.0",
            end_of_support=eos,
            extended_support_start=ext_start,
            extended_support_end=ext_end,
            resource_count=10
        )
        
        assert data.engine == "postgres"
        assert data.version == "14.0"
        assert data.end_of_support == eos
        assert data.extended_support_start == ext_start
        assert data.extended_support_end == ext_end
        assert data.resource_count == 10
    
    def test_optional_dates_can_be_none(self):
        """Test that optional date fields can be None."""
        data = EngineVersionData(
            engine="nodejs",
            version="20.x",
            end_of_support=None,
            extended_support_start=None,
            extended_support_end=None,
            resource_count=7
        )
        
        assert data.end_of_support is None
        assert data.extended_support_start is None
        assert data.extended_support_end is None
