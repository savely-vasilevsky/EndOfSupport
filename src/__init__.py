"""EndOfSupportTool - AWS resource support status analyzer."""

__version__ = "2.5.0"

from .models import (
    SupportStatus,
    Resource,
    ReportFilters,
    VersionGroup,
    EngineGroup,
    ServiceGroup,
    AccountGroup,
    Report,
)
from .parser import CSVParser, CSVParseError, DateParseError
from .classifier import ResourceClassifier
from .generator import ReportGenerator
from .ai_summary import AISummaryGenerator, generate_ai_summary

__all__ = [
    'SupportStatus',
    'Resource',
    'ReportFilters',
    'VersionGroup',
    'EngineGroup',
    'ServiceGroup',
    'AccountGroup',
    'Report',
    'CSVParser',
    'CSVParseError',
    'DateParseError',
    'ResourceClassifier',
    'ReportGenerator',
    'AISummaryGenerator',
    'generate_ai_summary',
]
