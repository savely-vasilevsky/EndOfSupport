"""AI-powered recommendation summary generator using Amazon Bedrock.

This module generates professional email summaries for end-of-support reports
using Claude on Amazon Bedrock. 

PRIVACY: Only aggregated, anonymized data is sent to the LLM.
No customer-identifiable information (account IDs, resource names, ARNs) is transmitted.
"""

import json
from datetime import date
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Handle imports for both package and frozen executable modes
try:
    from .models import Report, Resource, SupportStatus
except ImportError:
    from models import Report, Resource, SupportStatus

# Optional boto3 import
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class AISummaryGenerator:
    """Generates AI-powered recommendation summaries using Amazon Bedrock.
    
    Privacy safeguards:
    - Only aggregated statistics are sent to the LLM
    - No account IDs, resource names, or ARNs are transmitted
    - Resource details are merged back locally after AI generation
    """
    
    DEFAULT_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    def __init__(
        self, 
        model_id: str = None,
        region_name: str = None,
        profile_name: str = None
    ):
        """Initialize the AI summary generator.
        
        Args:
            model_id: Bedrock model ID (default: Claude 3 Sonnet)
            region_name: AWS region for Bedrock (default: us-east-1)
            profile_name: AWS profile name (optional)
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for AI summary generation")
        
        self.model_id = model_id or self.DEFAULT_MODEL_ID
        self.region_name = region_name or "us-east-1"
        
        # Create Bedrock client
        session_kwargs = {}
        if profile_name:
            session_kwargs['profile_name'] = profile_name
        
        session = boto3.Session(**session_kwargs)
        self.bedrock = session.client(
            'bedrock-runtime',
            region_name=self.region_name
        )
    
    def generate_summary(
        self, 
        report: Report,
        account_name: str = None,
        include_resource_details: bool = True
    ) -> str:
        """Generate an AI-powered recommendation summary.
        
        Args:
            report: The Report object with classified resources
            account_name: Optional account name for the summary header
            include_resource_details: Whether to include specific resource names
                                     (merged locally, not sent to AI)
        
        Returns:
            Formatted recommendation summary string
        """
        # Build privacy-safe context (aggregated, no PII)
        context = self._build_privacy_safe_context(report)
        
        # Generate AI summary
        ai_response = self._call_bedrock(context)
        
        # Optionally enrich with resource details (locally, not sent to AI)
        if include_resource_details:
            ai_response = self._enrich_with_resource_details(ai_response, report)
        
        # Add account header if provided
        if account_name:
            ai_response = f"Account: {account_name}\n\n{ai_response}"
        
        return ai_response
    
    def _build_privacy_safe_context(self, report: Report) -> Dict[str, Any]:
        """Build context with NO customer-identifiable data.
        
        Only aggregated statistics and public AWS version information is included.
        NO account IDs, resource names, or ARNs are sent to the LLM.
        """
        # Aggregate issues by service/engine/version
        issues_by_key: Dict[str, Dict] = {}
        
        # Iterate through the hierarchical report structure
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        for resource in version_group.resources:
                            if resource.status in [
                                SupportStatus.OUT_OF_SUPPORT,
                                SupportStatus.APPROACHING_EOS,
                                SupportStatus.EXTENDED_SUPPORT_YEAR_1,
                                SupportStatus.EXTENDED_SUPPORT_YEAR_2,
                                SupportStatus.EXTENDED_SUPPORT_YEAR_3,
                            ]:
                                key = f"{resource.service}|{resource.engine or 'N/A'}|{resource.version or 'N/A'}"
                                
                                if key not in issues_by_key:
                                    issues_by_key[key] = {
                                        "service": resource.service,
                                        "engine": resource.engine or "N/A",
                                        "version": resource.version or "N/A",
                                        "end_of_support": str(resource.end_of_support) if resource.end_of_support else "Unknown",
                                        "days_to_eos": resource.days_to_eos,
                                        "status": resource.status.value,
                                        "count": 0
                                    }
                                issues_by_key[key]["count"] += 1
        
        # Sort by urgency (days to EOS, then count)
        sorted_issues = sorted(
            issues_by_key.values(),
            key=lambda x: (
                0 if x["status"] == "Out of Support" else 1,
                x["days_to_eos"] if x["days_to_eos"] is not None else 9999,
                -x["count"]
            )
        )
        
        return {
            "report_date": str(date.today()),
            "total_resources": report.total_resources,
            "statistics": {
                "out_of_support": report.total_counts.get(SupportStatus.OUT_OF_SUPPORT, 0),
                "approaching_eos": report.total_counts.get(SupportStatus.APPROACHING_EOS, 0),
                "extended_support_y1": report.total_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_1, 0),
                "extended_support_y2": report.total_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_2, 0),
                "extended_support_y3": report.total_counts.get(SupportStatus.EXTENDED_SUPPORT_YEAR_3, 0),
                "supported": report.total_counts.get(SupportStatus.SUPPORTED, 0)
            },
            "issues_by_version": sorted_issues[:30]  # Limit to avoid token limits
        }
    
    def _call_bedrock(self, context: Dict[str, Any]) -> str:
        """Call Amazon Bedrock to generate the summary."""
        
        prompt = f"""You are an AWS infrastructure specialist helping teams manage end-of-support risks.

Generate a professional recommendation summary based on the following AGGREGATED end-of-support data.
This data contains NO customer-specific information - only service types, versions, and counts.

IMPORTANT RULES:
1. Use the exact counts provided - do not invent specific resource names
2. Group issues by service type (Lambda, RDS, EKS, etc.)
3. Prioritize by urgency: Out of Support > Approaching EOS > Extended Support
4. For upgrade recommendations:
   - For EKS/Kubernetes: The versions shown are CURRENT versions approaching end-of-support. Recommend upgrading to a NEWER version (higher number). For example, if 1.32 is approaching EOS, recommend upgrading to 1.33 or later when available.
   - For RDS/Aurora PostgreSQL: Recommend upgrading to the next major version (e.g., PostgreSQL 15 -> 16, PostgreSQL 16 -> 17)
   - For Lambda runtimes: Recommend the latest LTS versions (Python 3.12+, Node.js 20.x+, Java 21+)
   - Do NOT recommend downgrading to older versions
5. Keep the tone professional but urgent for critical issues
6. If a resource is "Approaching End-of-Support", the recommendation should be to plan the upgrade before the EOS date

FORMAT RULES:
- Do NOT format this as an email (no subject line, no greeting like "Hi Team", no signature like "Best regards")
- Write it as a report section with clear headings
- Use bullet points for lists
- Be concise and actionable

AGGREGATED REPORT DATA:
{json.dumps(context, indent=2)}

Generate a summary with these sections:
1. Overview (1-2 sentences summarizing the situation)
2. Summary Statistics
3. Critical Issues (grouped by service, use counts like "14 Lambda functions using Python 3.9")
4. Recommended Actions (with specific upgrade paths - always recommend NEWER versions)
5. Priority Timeline (what to address first based on EOS dates)

Do NOT include email-style greetings, signatures, or placeholder text."""

        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2000,
                    "temperature": 0.3,  # Lower temperature for more consistent output
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                })
            )
            
            result = json.loads(response['body'].read())
            return result['content'][0]['text']
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'AccessDeniedException':
                raise PermissionError(
                    "Access denied to Bedrock. Ensure your AWS credentials have "
                    "bedrock:InvokeModel permission and the model is enabled in your region."
                )
            raise
        except NoCredentialsError:
            raise PermissionError(
                "No AWS credentials found. Configure credentials via AWS CLI, "
                "environment variables, or IAM role."
            )
    
    def _enrich_with_resource_details(self, summary: str, report: Report) -> str:
        """Enrich the AI summary with specific resource details.
        
        This happens LOCALLY - resource names are NOT sent to the AI.
        Appends a detailed resource list to the AI-generated summary.
        """
        # Group resources by status and service
        critical_resources: Dict[str, List[Resource]] = defaultdict(list)
        
        # Iterate through the hierarchical report structure
        for account_name, account_group in report.accounts.items():
            for service_name, service_group in account_group.services.items():
                for engine_name, engine_group in service_group.engines.items():
                    for version_name, version_group in engine_group.versions.items():
                        for resource in version_group.resources:
                            if resource.status == SupportStatus.OUT_OF_SUPPORT:
                                critical_resources["Out of Support"].append(resource)
                            elif resource.status == SupportStatus.APPROACHING_EOS:
                                critical_resources["Approaching End-of-Support"].append(resource)
        
        if not critical_resources:
            return summary
        
        # Build detailed appendix
        details = ["\n\n---\nDETAILED RESOURCE LIST (for reference):\n"]
        
        for status_name, resources in critical_resources.items():
            details.append(f"\n{status_name}:")
            
            # Group by service
            by_service: Dict[str, List[Resource]] = defaultdict(list)
            for r in resources:
                by_service[r.service].append(r)
            
            for service, service_resources in sorted(by_service.items()):
                details.append(f"\n  {service}:")
                for r in service_resources[:20]:  # Limit per service
                    eos_info = f"EOS: {r.end_of_support}" if r.end_of_support else ""
                    days_info = f"({r.days_to_eos} days)" if r.days_to_eos is not None else ""
                    details.append(
                        f"    - {r.resource_name} ({r.engine} {r.version}) {eos_info} {days_info}"
                    )
                if len(service_resources) > 20:
                    details.append(f"    ... and {len(service_resources) - 20} more")
        
        return summary + "\n".join(details)


def generate_ai_summary(
    report: Report,
    account_name: str = None,
    region_name: str = None,
    profile_name: str = None,
    include_details: bool = True
) -> str:
    """Convenience function to generate an AI summary.
    
    Args:
        report: The Report object with classified resources
        account_name: Optional account name for the header
        region_name: AWS region for Bedrock
        profile_name: AWS profile name
        include_details: Whether to include resource details appendix
    
    Returns:
        Formatted recommendation summary
    """
    generator = AISummaryGenerator(
        region_name=region_name,
        profile_name=profile_name
    )
    return generator.generate_summary(
        report,
        account_name=account_name,
        include_resource_details=include_details
    )
