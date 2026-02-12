"""
EKS Upgrade Insights Fetcher

Fetches upgrade insights from EKS API for clusters to show pre-upgrade checks.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EKSInsight:
    """Represents an EKS upgrade insight."""
    name: str
    status: str  # PASSING, WARNING, ERROR, UNKNOWN
    description: str
    recommendation: str
    last_refresh_time: Optional[str] = None
    last_transition_time: Optional[str] = None
    category: str = "UPGRADE_READINESS"


@dataclass 
class ClusterInsights:
    """Collection of insights for an EKS cluster."""
    cluster_name: str
    cluster_arn: str
    region: str
    insights: List[EKSInsight]
    error: Optional[str] = None


def fetch_eks_insights(cluster_arn: str, region: str, profile: Optional[str] = None) -> ClusterInsights:
    """Fetch upgrade insights for an EKS cluster.
    
    Args:
        cluster_arn: ARN of the EKS cluster
        region: AWS region
        profile: Optional AWS profile name
        
    Returns:
        ClusterInsights with list of insights or error message
    """
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        return ClusterInsights(
            cluster_name=cluster_arn.split('/')[-1],
            cluster_arn=cluster_arn,
            region=region,
            insights=[],
            error="boto3 not installed. Run: pip install boto3"
        )
    
    cluster_name = cluster_arn.split('/')[-1]
    
    try:
        # Create EKS client
        config = Config(region_name=region)
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        eks_client = session.client('eks', config=config)
        
        # List insights for the cluster
        insights_list = []
        try:
            response = eks_client.list_insights(clusterName=cluster_name)
            insight_summaries = response.get('insights', [])
            
            # Get detailed info for each insight
            for summary in insight_summaries:
                insight_id = summary.get('id')
                if insight_id:
                    try:
                        detail_response = eks_client.describe_insight(
                            clusterName=cluster_name,
                            id=insight_id
                        )
                        insight_detail = detail_response.get('insight', {})
                        
                        insights_list.append(EKSInsight(
                            name=insight_detail.get('name', summary.get('name', 'Unknown')),
                            status=insight_detail.get('insightStatus', {}).get('status', 'UNKNOWN'),
                            description=insight_detail.get('description', ''),
                            recommendation=insight_detail.get('recommendation', ''),
                            last_refresh_time=str(insight_detail.get('lastRefreshTime', '')),
                            last_transition_time=str(insight_detail.get('lastTransitionTime', '')),
                            category=insight_detail.get('category', 'UPGRADE_READINESS')
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to get insight detail {insight_id}: {e}")
                        # Use summary info
                        insights_list.append(EKSInsight(
                            name=summary.get('name', 'Unknown'),
                            status=summary.get('insightStatus', {}).get('status', 'UNKNOWN'),
                            description='',
                            recommendation='',
                            category=summary.get('category', 'UPGRADE_READINESS')
                        ))
        except eks_client.exceptions.ResourceNotFoundException:
            return ClusterInsights(
                cluster_name=cluster_name,
                cluster_arn=cluster_arn,
                region=region,
                insights=[],
                error=f"Cluster '{cluster_name}' not found"
            )
        except Exception as e:
            logger.warning(f"Failed to list insights for {cluster_name}: {e}")
            return ClusterInsights(
                cluster_name=cluster_name,
                cluster_arn=cluster_arn,
                region=region,
                insights=[],
                error=str(e)
            )
        
        return ClusterInsights(
            cluster_name=cluster_name,
            cluster_arn=cluster_arn,
            region=region,
            insights=insights_list
        )
        
    except Exception as e:
        logger.error(f"Error fetching EKS insights for {cluster_name}: {e}")
        return ClusterInsights(
            cluster_name=cluster_name,
            cluster_arn=cluster_arn,
            region=region,
            insights=[],
            error=str(e)
        )


def format_insights_html(cluster_insights: ClusterInsights) -> str:
    """Format cluster insights as HTML for display in a modal/popup.
    
    Args:
        cluster_insights: ClusterInsights object
        
    Returns:
        HTML string
    """
    if cluster_insights.error:
        return f'''
        <div style="padding: 20px;">
            <h3 style="color: #d32f2f;">Error fetching insights</h3>
            <p>{cluster_insights.error}</p>
        </div>
        '''
    
    if not cluster_insights.insights:
        return f'''
        <div style="padding: 20px;">
            <h3>No upgrade insights available</h3>
            <p>No insights found for cluster <strong>{cluster_insights.cluster_name}</strong>.</p>
            <p>This may mean the cluster doesn't have upgrade insights enabled or there are no checks to display.</p>
        </div>
        '''
    
    # Count by status
    status_counts = {'PASSING': 0, 'WARNING': 0, 'ERROR': 0, 'UNKNOWN': 0}
    for insight in cluster_insights.insights:
        status_counts[insight.status] = status_counts.get(insight.status, 0) + 1
    
    # Build HTML
    html = f'''
    <div style="padding: 15px;">
        <h3 style="margin-bottom: 15px;">Upgrade Insights for {cluster_insights.cluster_name}</h3>
        <div style="display: flex; gap: 15px; margin-bottom: 20px;">
            <div style="padding: 8px 16px; background: #c8e6c9; border-radius: 4px;">
                <strong style="color: #1b5e20;">✓ Passing:</strong> {status_counts['PASSING']}
            </div>
            <div style="padding: 8px 16px; background: #fff9c4; border-radius: 4px;">
                <strong style="color: #f57f17;">⚠ Warning:</strong> {status_counts['WARNING']}
            </div>
            <div style="padding: 8px 16px; background: #ffcdd2; border-radius: 4px;">
                <strong style="color: #b71c1c;">✗ Error:</strong> {status_counts['ERROR']}
            </div>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
            <thead>
                <tr style="background: #f5f5f5;">
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Status</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Check</th>
                    <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Description</th>
                </tr>
            </thead>
            <tbody>
    '''
    
    # Sort insights: ERROR first, then WARNING, then PASSING
    status_order = {'ERROR': 0, 'WARNING': 1, 'UNKNOWN': 2, 'PASSING': 3}
    sorted_insights = sorted(cluster_insights.insights, key=lambda x: status_order.get(x.status, 4))
    
    for insight in sorted_insights:
        status_style = {
            'PASSING': 'background: #c8e6c9; color: #1b5e20;',
            'WARNING': 'background: #fff9c4; color: #f57f17;',
            'ERROR': 'background: #ffcdd2; color: #b71c1c;',
            'UNKNOWN': 'background: #e0e0e0; color: #666;'
        }.get(insight.status, 'background: #e0e0e0; color: #666;')
        
        status_icon = {
            'PASSING': '✓',
            'WARNING': '⚠',
            'ERROR': '✗',
            'UNKNOWN': '?'
        }.get(insight.status, '?')
        
        html += f'''
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px;">
                    <span style="padding: 4px 10px; border-radius: 12px; font-weight: 600; {status_style}">
                        {status_icon} {insight.status}
                    </span>
                </td>
                <td style="padding: 10px; font-weight: 500;">{insight.name}</td>
                <td style="padding: 10px; color: #666;">{insight.description or 'No description available'}</td>
            </tr>
        '''
    
    html += '''
            </tbody>
        </table>
    </div>
    '''
    
    return html
