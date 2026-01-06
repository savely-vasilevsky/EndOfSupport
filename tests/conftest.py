"""Shared fixtures and generators for property-based testing."""

import csv
import os
import tempfile
from datetime import date, timedelta
from typing import List, Optional

import pytest
from hypothesis import strategies as st

from src.models import Resource, SupportStatus


# Date strategies
@st.composite
def valid_date_strategy(draw):
    """Generate valid dates within a reasonable range."""
    # Generate dates between 2019 and 2030
    start_date = date(2019, 1, 1)
    end_date = date(2030, 12, 31)
    days_range = (end_date - start_date).days
    offset = draw(st.integers(min_value=0, max_value=days_range))
    return start_date + timedelta(days=offset)


@st.composite
def date_string_dd_mmm_yy_strategy(draw):
    """Generate date strings in DD-MMM-YY format."""
    d = draw(valid_date_strategy())
    return d.strftime('%d-%b-%y'), d


# Safe text strategy that avoids control characters and newlines
safe_text_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters=' -_().',
        blacklist_characters='\r\n\t'
    ),
    min_size=1, max_size=50
).filter(lambda x: x.strip()).map(lambda x: x[:50])

# Resource field strategies
account_strategy = safe_text_strategy

service_strategy = st.sampled_from(['Lambda', 'RDS', 'ElastiCache', 'MSK'])

engine_strategy = st.one_of(
    st.none(),
    st.sampled_from(['python3.9', 'nodejs18.x', 'redis', 'aurora-postgresql', 'Kafka'])
)

version_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=('L', 'N'),
        whitelist_characters='.-_',
        blacklist_characters='\r\n\t'
    ),
    min_size=1, max_size=20
).filter(lambda x: x.strip()).map(lambda x: x[:20])

region_strategy = st.sampled_from([
    'us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-southeast-1'
])

insights_strategy = st.sampled_from([
    'Out of support.',
    'Supported',
    'Version is not planned for deprecation yet.',
    '398 days to end-of-support.',
    'No information related to this version is found in the documentations.'
])


@st.composite
def resource_strategy(draw):
    """Generate random Resource objects for property testing."""
    account = draw(account_strategy)
    service = draw(service_strategy)
    engine = draw(engine_strategy)
    version = draw(version_strategy)
    region = draw(region_strategy)
    insights = draw(insights_strategy)
    
    # Generate dates
    eos_date = draw(st.one_of(st.none(), valid_date_strategy()))
    eos_raw = eos_date.strftime('%d-%b-%y') if eos_date else draw(
        st.sampled_from(['Deprecated', 'Supported', 'Not available', '-'])
    )
    
    return Resource(
        account=account,
        payer_id=draw(safe_text_strategy),
        service=service,
        resource_type=draw(st.sampled_from(['Function', 'Cluster', 'Instance'])),
        resource_arn=f'arn:aws:{service.lower()}:{region}:123456789:{draw(safe_text_strategy)}',
        resource_name=draw(safe_text_strategy),
        region=region,
        engine=engine,
        version=version,
        end_of_support=eos_date,
        end_of_support_raw=eos_raw,
        auto_minor_version_upgrade=draw(st.one_of(st.none(), st.booleans())),
        extended_support_start=draw(st.one_of(st.none(), valid_date_strategy())),
        extended_support_year1_start=draw(st.one_of(st.none(), valid_date_strategy())),
        extended_support_year3_start=draw(st.one_of(st.none(), valid_date_strategy())),
        extended_support_end=draw(st.one_of(st.none(), valid_date_strategy())),
        insights=insights,
    )


@st.composite
def csv_row_strategy(draw):
    """Generate random CSV row data for parsing tests."""
    resource = draw(resource_strategy())
    
    # Convert resource to CSV row dict
    return {
        'Account': resource.account,
        'Payer ID': resource.payer_id,
        'Service': resource.service,
        'Resource Type': resource.resource_type,
        'Resource ARN': resource.resource_arn,
        'Resource Name': resource.resource_name,
        'Regions / AZs': resource.region,
        'Engine': resource.engine if resource.engine else '-',
        'Version': resource.version,
        'End-of-Support': resource.end_of_support_raw,
        'Auto Minor Version Upgrade': 'TRUE' if resource.auto_minor_version_upgrade else '-',
        'Extended Support - Start Date': resource.extended_support_start.strftime('%d-%b-%y') if resource.extended_support_start else '-',
        'Extended Support - Year 1 Pricing Start Date': resource.extended_support_year1_start.strftime('%d-%b-%y') if resource.extended_support_year1_start else '-',
        'Extended Support - Year 3 Pricing Start Date': resource.extended_support_year3_start.strftime('%d-%b-%y') if resource.extended_support_year3_start else '-',
        'Extended Support - End Date': resource.extended_support_end.strftime('%d-%b-%y') if resource.extended_support_end else '-',
        'Insights': resource.insights,
    }, resource


@st.composite
def csv_rows_strategy(draw, min_rows=1, max_rows=20):
    """Generate a list of CSV rows."""
    num_rows = draw(st.integers(min_value=min_rows, max_value=max_rows))
    rows = []
    for _ in range(num_rows):
        row_data, _ = draw(csv_row_strategy())
        rows.append(row_data)
    return rows


# Fixture for creating temporary CSV files
@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing."""
    files_to_cleanup = []
    
    def _create_csv(rows: List[dict]) -> str:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            temp_path = f.name
            files_to_cleanup.append(temp_path)
            return temp_path
    
    yield _create_csv
    
    # Cleanup
    for path in files_to_cleanup:
        if os.path.exists(path):
            os.unlink(path)
