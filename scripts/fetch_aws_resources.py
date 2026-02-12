#!/usr/bin/env python3
"""
AWS Resource Inventory Fetcher

Fetches resource inventory from multiple AWS services across all regions
and outputs a CSV compatible with the End-of-Support Tool.

Features:
- Fetches from 10 AWS services (EKS, RDS, Aurora, DocumentDB, Neptune, etc.)
- Enriches with Extended Support dates using hybrid lookup (static + API)
- Calculates estimated Extended Support costs per resource
- Parallel fetching across regions for performance

Services supported:
- Elastic Kubernetes Service (EKS)
- Relational Database Service (RDS)
- Aurora
- DocumentDB
- Neptune
- ElastiCache
- OpenSearch
- Lambda
- Managed Streaming for Apache Kafka (MSK)
- Amazon MQ

Usage:
    python fetch_aws_resources.py [--profile PROFILE] [--regions REGION1,REGION2] [--output FILE]

Requirements:
    pip install boto3
"""

import argparse
import csv
import json
import sys
import os
from datetime import datetime, date
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    print("Error: boto3 is required. Install with: pip install boto3")
    sys.exit(1)

# Import the extended support lookup module
try:
    from extended_support_lookup import ExtendedSupportLookup
except ImportError:
    # Try relative import
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from extended_support_lookup import ExtendedSupportLookup


# End-of-support dates for various runtimes/versions (approximate)
EOS_DATES = {
    # Lambda runtimes
    "nodejs14.x": "2024-11-30",
    "nodejs16.x": "2024-06-12",
    "nodejs18.x": "2025-04-30",
    "nodejs20.x": "2026-04-30",
    "python3.7": "2023-12-04",
    "python3.8": "2024-10-14",
    "python3.9": "2025-10-01",
    "python3.10": "2026-10-01",
    "python3.11": "2027-10-01",
    "python3.12": "2028-10-01",
    "python3.13": "2029-06-30",
    "java8": "2024-01-08",
    "java8.al2": "2025-01-08",
    "java11": "2026-09-01",
    "java17": "2028-09-01",
    "java21": "2030-09-01",
    "dotnet6": "2024-11-12",
    "dotnet8": "2026-11-10",
    "ruby3.2": "2026-03-31",
    "ruby3.3": "2027-03-31",
    # EKS versions
    "1.24": "2024-01-31",
    "1.25": "2024-05-01",
    "1.26": "2024-06-11",
    "1.27": "2024-07-24",
    "1.28": "2024-11-26",
    "1.29": "2025-03-23",
    "1.30": "2025-07-23",
    "1.31": "2025-11-23",
    "1.32": "2026-03-23",
}


class AWSResourceFetcher:
    """Fetches AWS resources across multiple services and regions."""
    
    def __init__(self, profile: Optional[str] = None, regions: Optional[List[str]] = None,
                 include_costs: bool = True):
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.regions = regions or self._get_all_regions()
        self.resources: List[Dict] = []
        self.account_id = self._get_account_id()
        self.account_alias = self._get_account_alias()
        self.include_costs = include_costs
        
        # Initialize the extended support lookup (hybrid approach)
        self.ext_support_lookup = ExtendedSupportLookup(self.session)
        
    def _get_account_id(self) -> str:
        """Get the current AWS account ID."""
        try:
            sts = self.session.client('sts')
            return sts.get_caller_identity()['Account']
        except Exception as e:
            print(f"Warning: Could not get account ID: {e}")
            return "Unknown"
    
    def _get_account_alias(self) -> str:
        """Get the account alias if set."""
        try:
            iam = self.session.client('iam')
            aliases = iam.list_account_aliases()['AccountAliases']
            return aliases[0] if aliases else self.account_id
        except Exception:
            return self.account_id
    
    def _get_all_regions(self) -> List[str]:
        """Get all available AWS regions."""
        try:
            ec2 = self.session.client('ec2', region_name='us-east-1')
            regions = ec2.describe_regions(AllRegions=False)['Regions']
            return [r['RegionName'] for r in regions]
        except Exception as e:
            print(f"Warning: Could not fetch regions, using defaults: {e}")
            return ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-southeast-1']
    
    def _get_eos_date(self, version: str) -> str:
        """Get end-of-support date for a version."""
        return EOS_DATES.get(version, "")
    
    def _get_insights(self, eos_date: str) -> str:
        """Generate insights based on EOS date."""
        if not eos_date:
            return "End-of-support date not available"
        try:
            eos = datetime.strptime(eos_date, "%Y-%m-%d")
            today = datetime.now()
            days = (eos - today).days
            if days < 0:
                return "Out of support."
            elif days <= 90:
                return f"{days} days to end-of-support."
            else:
                return f"{days} days to end-of-support."
        except:
            return ""

    def _enrich_with_extended_support(self, engine: str, version: str, 
                                       instance_type: Optional[str] = None) -> Dict:
        """Enrich resource with extended support dates and cost estimates.
        
        Uses the hybrid lookup approach:
        1. Static lookup table (has Year 1/Year 3 pricing dates)
        2. RDS API for real-time updates
        
        Args:
            engine: Engine name (e.g., "mysql", "aurora-postgresql")
            version: Engine version
            instance_type: Instance type for cost calculation
            
        Returns:
            Dict with extended support dates and cost estimates.
        """
        result = {
            "ext_support_start": "",
            "ext_support_y1": "",
            "ext_support_y3": "",
            "ext_support_end": "",
            "ext_support_year": "",
            "est_monthly_cost": "",
            "est_annual_cost": "",
        }
        
        # Get extended support dates
        dates = self.ext_support_lookup.get_extended_support_dates(engine, version)
        
        if dates:
            if dates.extended_support_start:
                result["ext_support_start"] = dates.extended_support_start.strftime("%Y-%m-%d")
            if dates.extended_support_year1_start:
                result["ext_support_y1"] = dates.extended_support_year1_start.strftime("%Y-%m-%d")
            if dates.extended_support_year3_start:
                result["ext_support_y3"] = dates.extended_support_year3_start.strftime("%Y-%m-%d")
            if dates.extended_support_end:
                result["ext_support_end"] = dates.extended_support_end.strftime("%Y-%m-%d")
            
            # Get current year
            current_year = dates.get_current_year()
            if current_year:
                result["ext_support_year"] = f"Year {current_year}"
        
        # Get cost estimates if enabled
        if self.include_costs:
            cost = self.ext_support_lookup.estimate_monthly_cost(
                engine, version, instance_type
            )
            if cost["pricing_available"]:
                if cost["in_extended_support"]:
                    result["est_monthly_cost"] = f"${cost['current_monthly_cost']:.2f}"
                    result["est_annual_cost"] = f"${cost['current_annual_cost']:.2f}"
                else:
                    # Show Year 1 cost as estimate for future
                    result["est_monthly_cost"] = f"${cost['monthly_cost_year1']:.2f} (Y1)"
                    result["est_annual_cost"] = f"${cost['annual_cost_year1']:.2f} (Y1)"
        
        return result

    def _add_resource(self, service: str, resource_type: str, arn: str, name: str,
                      region: str, engine: Optional[str], version: str,
                      auto_upgrade: Optional[bool] = None,
                      instance_type: Optional[str] = None,
                      ext_support_start: str = "", ext_support_y1: str = "",
                      ext_support_y3: str = "", ext_support_end: str = ""):
        """Add a resource to the collection with extended support enrichment."""
        eos_date = self._get_eos_date(version)
        
        # Enrich with extended support dates and costs
        ext_data = self._enrich_with_extended_support(
            engine or "", version, instance_type
        )
        
        # Use provided dates if available, otherwise use enriched data
        self.resources.append({
            "Account": f"{self.account_id} ({self.account_alias})",
            "Payer ID": self.account_id,
            "Service": service,
            "Resource Type": resource_type,
            "Resource ARN": arn,
            "Resource Name": name,
            "Regions / AZs": region,
            "Engine": engine or "-",
            "Version": version,
            "Instance Type": instance_type or "-",
            "End-of-Support": eos_date,
            "Auto Minor Version Upgrade": "TRUE" if auto_upgrade else "-" if auto_upgrade is None else "FALSE",
            "Extended Support - Start Date": ext_support_start or ext_data["ext_support_start"],
            "Extended Support - Year 1 Pricing Start Date": ext_support_y1 or ext_data["ext_support_y1"],
            "Extended Support - Year 3 Pricing Start Date": ext_support_y3 or ext_data["ext_support_y3"],
            "Extended Support - End Date": ext_support_end or ext_data["ext_support_end"],
            "Extended Support Year": ext_data["ext_support_year"],
            "Est. Monthly Ext Support Cost": ext_data["est_monthly_cost"],
            "Est. Annual Ext Support Cost": ext_data["est_annual_cost"],
            "Insights": self._get_insights(eos_date),
        })

    def fetch_lambda(self, region: str):
        """Fetch Lambda functions."""
        try:
            client = self.session.client('lambda', region_name=region)
            paginator = client.get_paginator('list_functions')
            
            for page in paginator.paginate():
                for func in page.get('Functions', []):
                    self._add_resource(
                        service="Lambda",
                        resource_type="Function",
                        arn=func['FunctionArn'],
                        name=func['FunctionName'],
                        region=region,
                        engine="-",
                        version=func.get('Runtime', 'Unknown'),
                    )
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  Lambda error in {region}: {e}")
    
    def fetch_eks(self, region: str):
        """Fetch EKS clusters."""
        try:
            client = self.session.client('eks', region_name=region)
            paginator = client.get_paginator('list_clusters')
            
            for page in paginator.paginate():
                for cluster_name in page.get('clusters', []):
                    try:
                        cluster = client.describe_cluster(name=cluster_name)['cluster']
                        self._add_resource(
                            service="Elastic Kubernetes Service (EKS)",
                            resource_type="Cluster",
                            arn=cluster['arn'],
                            name=cluster_name,
                            region=region,
                            engine="Kubernetes",
                            version=cluster.get('version', 'Unknown'),
                        )
                    except ClientError:
                        pass
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  EKS error in {region}: {e}")
    
    def fetch_rds(self, region: str):
        """Fetch RDS instances and clusters (including Aurora)."""
        try:
            client = self.session.client('rds', region_name=region)
            
            # Fetch DB instances
            paginator = client.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for db in page.get('DBInstances', []):
                    engine = db.get('Engine', '')
                    service = "Aurora" if 'aurora' in engine.lower() else "Relational Database Service (RDS)"
                    self._add_resource(
                        service=service,
                        resource_type="DB Instance",
                        arn=db['DBInstanceArn'],
                        name=db['DBInstanceIdentifier'],
                        region=region,
                        engine=engine,
                        version=db.get('EngineVersion', 'Unknown'),
                        auto_upgrade=db.get('AutoMinorVersionUpgrade'),
                        instance_type=db.get('DBInstanceClass'),
                    )
            
            # Fetch DB clusters (Aurora)
            paginator = client.get_paginator('describe_db_clusters')
            for page in paginator.paginate():
                for cluster in page.get('DBClusters', []):
                    engine = cluster.get('Engine', '')
                    if 'aurora' in engine.lower():
                        self._add_resource(
                            service="Aurora",
                            resource_type="DB Cluster",
                            arn=cluster['DBClusterArn'],
                            name=cluster['DBClusterIdentifier'],
                            region=region,
                            engine=engine,
                            version=cluster.get('EngineVersion', 'Unknown'),
                            auto_upgrade=cluster.get('AutoMinorVersionUpgrade'),
                        )
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  RDS error in {region}: {e}")
    
    def fetch_documentdb(self, region: str):
        """Fetch DocumentDB clusters and instances."""
        try:
            client = self.session.client('docdb', region_name=region)
            
            # Fetch clusters
            paginator = client.get_paginator('describe_db_clusters')
            for page in paginator.paginate():
                for cluster in page.get('DBClusters', []):
                    if cluster.get('Engine') == 'docdb':
                        self._add_resource(
                            service="DocumentDB",
                            resource_type="DB Cluster",
                            arn=cluster['DBClusterArn'],
                            name=cluster['DBClusterIdentifier'],
                            region=region,
                            engine="docdb",
                            version=cluster.get('EngineVersion', 'Unknown'),
                        )
            
            # Fetch instances
            paginator = client.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for db in page.get('DBInstances', []):
                    if db.get('Engine') == 'docdb':
                        self._add_resource(
                            service="DocumentDB",
                            resource_type="DB Instance",
                            arn=db['DBInstanceArn'],
                            name=db['DBInstanceIdentifier'],
                            region=region,
                            engine="docdb",
                            version=db.get('EngineVersion', 'Unknown'),
                            auto_upgrade=db.get('AutoMinorVersionUpgrade'),
                            instance_type=db.get('DBInstanceClass'),
                        )
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  DocumentDB error in {region}: {e}")

    def fetch_neptune(self, region: str):
        """Fetch Neptune clusters and instances."""
        try:
            client = self.session.client('neptune', region_name=region)
            
            # Fetch clusters
            paginator = client.get_paginator('describe_db_clusters')
            for page in paginator.paginate():
                for cluster in page.get('DBClusters', []):
                    if cluster.get('Engine') == 'neptune':
                        self._add_resource(
                            service="Neptune",
                            resource_type="DB Cluster",
                            arn=cluster['DBClusterArn'],
                            name=cluster['DBClusterIdentifier'],
                            region=region,
                            engine="neptune",
                            version=cluster.get('EngineVersion', 'Unknown'),
                        )
            
            # Fetch instances
            paginator = client.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for db in page.get('DBInstances', []):
                    if db.get('Engine') == 'neptune':
                        self._add_resource(
                            service="Neptune",
                            resource_type="DB Instance",
                            arn=db['DBInstanceArn'],
                            name=db['DBInstanceIdentifier'],
                            region=region,
                            engine="neptune",
                            version=db.get('EngineVersion', 'Unknown'),
                            auto_upgrade=db.get('AutoMinorVersionUpgrade'),
                            instance_type=db.get('DBInstanceClass'),
                        )
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  Neptune error in {region}: {e}")
    
    def fetch_elasticache(self, region: str):
        """Fetch ElastiCache clusters."""
        try:
            client = self.session.client('elasticache', region_name=region)
            
            # Fetch cache clusters
            paginator = client.get_paginator('describe_cache_clusters')
            for page in paginator.paginate(ShowCacheNodeInfo=True):
                for cluster in page.get('CacheClusters', []):
                    self._add_resource(
                        service="ElastiCache",
                        resource_type="Cache Cluster",
                        arn=cluster.get('ARN', f"arn:aws:elasticache:{region}:{self.account_id}:cluster:{cluster['CacheClusterId']}"),
                        name=cluster['CacheClusterId'],
                        region=region,
                        engine=cluster.get('Engine', 'Unknown'),
                        version=cluster.get('EngineVersion', 'Unknown'),
                        auto_upgrade=cluster.get('AutoMinorVersionUpgrade'),
                        instance_type=cluster.get('CacheNodeType'),
                    )
            
            # Fetch replication groups (Redis)
            paginator = client.get_paginator('describe_replication_groups')
            for page in paginator.paginate():
                for rg in page.get('ReplicationGroups', []):
                    member_clusters = rg.get('MemberClusters', [])
                    version = 'Unknown'
                    engine = 'redis'
                    node_type = None
                    if member_clusters:
                        try:
                            cluster_info = client.describe_cache_clusters(
                                CacheClusterId=member_clusters[0]
                            )['CacheClusters'][0]
                            version = cluster_info.get('EngineVersion', 'Unknown')
                            engine = cluster_info.get('Engine', 'redis')
                            node_type = cluster_info.get('CacheNodeType')
                        except:
                            pass
                    
                    self._add_resource(
                        service="ElastiCache",
                        resource_type="Replication Group",
                        arn=rg.get('ARN', f"arn:aws:elasticache:{region}:{self.account_id}:replicationgroup:{rg['ReplicationGroupId']}"),
                        name=rg['ReplicationGroupId'],
                        region=region,
                        engine=engine,
                        version=version,
                        instance_type=node_type,
                    )
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  ElastiCache error in {region}: {e}")
    
    def fetch_opensearch(self, region: str):
        """Fetch OpenSearch domains."""
        try:
            client = self.session.client('opensearch', region_name=region)
            
            domains = client.list_domain_names().get('DomainNames', [])
            for domain_info in domains:
                domain_name = domain_info['DomainName']
                try:
                    domain = client.describe_domain(DomainName=domain_name)['DomainStatus']
                    engine_version = domain.get('EngineVersion', 'Unknown')
                    if '_' in engine_version:
                        engine, version = engine_version.split('_', 1)
                    else:
                        engine = "OpenSearch"
                        version = engine_version
                    
                    # Get instance type from cluster config
                    cluster_config = domain.get('ClusterConfig', {})
                    instance_type = cluster_config.get('InstanceType')
                    
                    self._add_resource(
                        service="OpenSearch Service",
                        resource_type="Domain",
                        arn=domain['ARN'],
                        name=domain_name,
                        region=region,
                        engine=engine,
                        version=version,
                        auto_upgrade=domain.get('AutoSoftwareUpdateEnabled'),
                        instance_type=instance_type,
                    )
                except ClientError:
                    pass
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  OpenSearch error in {region}: {e}")

    def fetch_msk(self, region: str):
        """Fetch MSK (Managed Streaming for Apache Kafka) clusters."""
        try:
            client = self.session.client('kafka', region_name=region)
            
            paginator = client.get_paginator('list_clusters_v2')
            for page in paginator.paginate():
                for cluster in page.get('ClusterInfoList', []):
                    cluster_type = cluster.get('ClusterType', 'PROVISIONED')
                    instance_type = None
                    
                    if cluster_type == 'PROVISIONED':
                        provisioned = cluster.get('Provisioned', {})
                        version = provisioned.get('CurrentBrokerSoftwareInfo', {}).get('KafkaVersion', 'Unknown')
                        broker_info = provisioned.get('BrokerNodeGroupInfo', {})
                        instance_type = broker_info.get('InstanceType')
                    elif cluster_type == 'SERVERLESS':
                        version = 'Serverless'
                    else:
                        version = 'Unknown'
                    
                    self._add_resource(
                        service="Managed Streaming for Apache Kafka (MSK)",
                        resource_type=f"Cluster ({cluster_type})",
                        arn=cluster['ClusterArn'],
                        name=cluster['ClusterName'],
                        region=region,
                        engine="Apache Kafka",
                        version=version,
                        instance_type=instance_type,
                    )
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  MSK error in {region}: {e}")
    
    def fetch_mq(self, region: str):
        """Fetch Amazon MQ brokers."""
        try:
            client = self.session.client('mq', region_name=region)
            
            paginator = client.get_paginator('list_brokers')
            for page in paginator.paginate():
                for broker_summary in page.get('BrokerSummaries', []):
                    broker_id = broker_summary['BrokerId']
                    try:
                        broker = client.describe_broker(BrokerId=broker_id)
                        self._add_resource(
                            service="Amazon MQ",
                            resource_type=f"Broker ({broker.get('EngineType', 'Unknown')})",
                            arn=broker['BrokerArn'],
                            name=broker['BrokerName'],
                            region=region,
                            engine=broker.get('EngineType', 'Unknown'),
                            version=broker.get('EngineVersion', 'Unknown'),
                            auto_upgrade=broker.get('AutoMinorVersionUpgrade'),
                            instance_type=broker.get('HostInstanceType'),
                        )
                    except ClientError:
                        pass
        except ClientError as e:
            if e.response['Error']['Code'] != 'AccessDeniedException':
                print(f"  Amazon MQ error in {region}: {e}")
    
    def fetch_all_in_region(self, region: str):
        """Fetch all resources in a single region."""
        print(f"  Fetching resources in {region}...")
        
        self.fetch_lambda(region)
        self.fetch_eks(region)
        self.fetch_rds(region)
        self.fetch_documentdb(region)
        self.fetch_neptune(region)
        self.fetch_elasticache(region)
        self.fetch_opensearch(region)
        self.fetch_msk(region)
        self.fetch_mq(region)
    
    def fetch_all(self, max_workers: int = 10):
        """Fetch all resources across all regions using parallel execution."""
        print(f"Fetching resources from {len(self.regions)} regions...")
        print(f"Account: {self.account_id} ({self.account_alias})")
        print()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.fetch_all_in_region, region): region 
                      for region in self.regions}
            
            for future in as_completed(futures):
                region = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"  Error in {region}: {e}")
        
        print()
        print(f"Total resources found: {len(self.resources)}")
        
        # Print cost summary if costs are included
        if self.include_costs:
            self._print_cost_summary()

    def _print_cost_summary(self):
        """Print a summary of estimated extended support costs."""
        total_monthly = 0.0
        total_annual = 0.0
        resources_with_cost = 0
        
        for resource in self.resources:
            monthly_cost = resource.get("Est. Monthly Ext Support Cost", "")
            if monthly_cost and monthly_cost != "-":
                try:
                    # Extract numeric value from string like "$146.00" or "$146.00 (Y1)"
                    cost_str = monthly_cost.replace("$", "").split()[0]
                    cost = float(cost_str)
                    total_monthly += cost
                    total_annual += cost * 12
                    resources_with_cost += 1
                except:
                    pass
        
        if resources_with_cost > 0:
            print()
            print("=" * 60)
            print("EXTENDED SUPPORT COST ESTIMATE SUMMARY")
            print("=" * 60)
            print(f"Resources with cost estimates: {resources_with_cost}")
            print(f"Estimated Monthly Cost: ${total_monthly:,.2f}")
            print(f"Estimated Annual Cost: ${total_annual:,.2f}")
            print()
            print("Note: Costs are estimates based on vCPU-hour pricing.")
            print("Actual costs may vary based on usage and region.")
    
    def to_csv(self, output_file: str):
        """Export resources to CSV file."""
        if not self.resources:
            print("No resources to export.")
            return
        
        fieldnames = [
            "Account", "Payer ID", "Service", "Resource Type", "Resource ARN",
            "Resource Name", "Regions / AZs", "Engine", "Version", "Instance Type",
            "End-of-Support", "Auto Minor Version Upgrade", 
            "Extended Support - Start Date",
            "Extended Support - Year 1 Pricing Start Date",
            "Extended Support - Year 3 Pricing Start Date",
            "Extended Support - End Date",
            "Extended Support Year",
            "Est. Monthly Ext Support Cost",
            "Est. Annual Ext Support Cost",
            "Insights"
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.resources)
        
        print(f"Exported {len(self.resources)} resources to {output_file}")
    
    def to_json(self, output_file: str):
        """Export resources to JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.resources, f, indent=2, default=str)
        
        print(f"Exported {len(self.resources)} resources to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch AWS resource inventory for End-of-Support analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch from all regions using default credentials
  python fetch_aws_resources.py
  
  # Use a specific AWS profile
  python fetch_aws_resources.py --profile production
  
  # Fetch from specific regions only
  python fetch_aws_resources.py --regions us-east-1,eu-west-1
  
  # Save to a specific file
  python fetch_aws_resources.py --output my_inventory.csv
  
  # Export as JSON
  python fetch_aws_resources.py --format json --output inventory.json
  
  # Disable cost estimation
  python fetch_aws_resources.py --no-costs
"""
    )
    
    parser.add_argument('--profile', '-p', help='AWS profile name')
    parser.add_argument('--regions', '-r', help='Comma-separated list of regions (default: all)')
    parser.add_argument('--output', '-o', default='aws_inventory.csv', help='Output file path')
    parser.add_argument('--format', '-f', choices=['csv', 'json'], default='csv', help='Output format')
    parser.add_argument('--workers', '-w', type=int, default=10, help='Number of parallel workers')
    parser.add_argument('--no-costs', action='store_true', help='Disable cost estimation')
    
    args = parser.parse_args()
    
    regions = args.regions.split(',') if args.regions else None
    
    try:
        fetcher = AWSResourceFetcher(
            profile=args.profile, 
            regions=regions,
            include_costs=not args.no_costs
        )
        fetcher.fetch_all(max_workers=args.workers)
        
        if args.format == 'json':
            fetcher.to_json(args.output)
        else:
            fetcher.to_csv(args.output)
            
    except NoCredentialsError:
        print("Error: AWS credentials not found.")
        print("Configure credentials using: aws configure")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
