"""Report generator agent for creating comprehensive DevOps reports."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import os

from agents.base_agent import BaseDevOpsAgent, DevOpsAgentPlugin
from semantic_kernel.functions import kernel_function


class ReportGeneratorPlugin(DevOpsAgentPlugin):
    """Plugin for report generation capabilities."""
    
    def __init__(self):
        super().__init__("report_generator")
        self.report_templates = {
            'infrastructure': self._generate_infrastructure_report,
            'cost': self._generate_cost_report,
            'incident': self._generate_incident_report,
            'deployment': self._generate_deployment_report,
            'executive': self._generate_executive_summary,
            'kubernetes': self._generate_kubernetes_report
        }
        
    @kernel_function(name="generate_report", description="Generate a comprehensive DevOps report")
    async def generate_report(self, report_type: str, data: Dict[str, Any], time_period: str = "30d") -> str:
        """Generate a specific type of report using real data from other agents."""
        try:
            self.logger.info(f"Generating {report_type} report for period: {time_period}")
            
            if report_type not in self.report_templates:
                return f"Unknown report type: {report_type}. Available types: {', '.join(self.report_templates.keys())}"
            
            # If no data provided, collect it from other agents
            if not data or all(not v for v in data.values()):
                data = await self._collect_report_data(report_type, time_period)
            
            report_function = self.report_templates[report_type]
            report_content = await report_function(data, time_period)
            
            # Add report header
            report = self._generate_report_header(report_type, time_period)
            report += report_content
            report += self._generate_report_footer()
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            return f"Error generating report: {str(e)}"
    
    async def _collect_report_data(self, report_type: str, time_period: str) -> Dict[str, Any]:
        """Collect data from other agents for report generation."""
        data = {}
        
        try:
            # Access orchestrator through the agent
            if hasattr(self, 'agent') and hasattr(self.agent, 'orchestrator'):
                orchestrator = self.agent.orchestrator
                
                # Collect data based on report type
                if report_type in ['infrastructure', 'executive']:
                    # Get infrastructure data
                    infra_request = {
                        'action': 'check_health',
                        'parameters': {}
                    }
                    infra_result = await orchestrator.agents.get('infrastructure', {}).process_request(infra_request)
                    data['infrastructure'] = self._parse_agent_result(infra_result)
                
                if report_type in ['cost', 'executive']:
                    # Get cost data
                    cost_request = {
                        'action': 'analyze_costs',
                        'parameters': {'time_period': time_period}
                    }
                    cost_result = await orchestrator.agents.get('cost', {}).process_request(cost_request)
                    data['cost'] = self._parse_agent_result(cost_result)
                
                if report_type in ['deployment', 'executive']:
                    # Get deployment data
                    deploy_request = {
                        'action': 'list_deployments',
                        'parameters': {}
                    }
                    deploy_result = await orchestrator.agents.get('deployment', {}).process_request(deploy_request)
                    data['deployments'] = self._parse_agent_result(deploy_result)
                
                if report_type in ['kubernetes', 'executive']:
                    # Get Kubernetes data
                    k8s_request = {
                        'action': 'get_cluster_status',
                        'parameters': {}
                    }
                    k8s_result = await orchestrator.agents.get('kubernetes', {}).process_request(k8s_request)
                    data['kubernetes'] = self._parse_agent_result(k8s_result)
            
        except Exception as e:
            self.logger.warning(f"Could not collect live data: {str(e)}")
        
        return data
    
    def _parse_agent_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Parse agent result to extract data for reports."""
        if result.get('status') == 'success':
            # Parse the text result to extract key metrics
            result_text = result.get('result', '')
            
            # Extract numbers and metrics from the text
            metrics = {}
            
            # Common patterns to extract
            import re
            
            # Total resources
            total_match = re.search(r'Total (?:Resources|VMs|Deployments|Pods): (\d+)', result_text)
            if total_match:
                metrics['total'] = int(total_match.group(1))
            
            # Healthy/Running
            healthy_match = re.search(r'(?:Healthy|Running|Successful|Active): (\d+)', result_text)
            if healthy_match:
                metrics['healthy'] = int(healthy_match.group(1))
            
            # Cost data
            cost_match = re.search(r'Total (?:Cost|Monthly Cost): \$?([\d,]+(?:\.\d{2})?)', result_text)
            if cost_match:
                metrics['total_cost'] = float(cost_match.group(1).replace(',', ''))
            
            # Percentage
            percent_match = re.search(r'(\d+(?:\.\d+)?)\s*%', result_text)
            if percent_match:
                metrics['percentage'] = float(percent_match.group(1))
            
            metrics['raw_result'] = result_text
            return metrics
        
        return {}
    
    async def _generate_infrastructure_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate infrastructure health and performance report."""
        report = "\n=== INFRASTRUCTURE REPORT ===\n\n"
        
        infra_data = data.get('infrastructure', {})
        
        if infra_data.get('raw_result'):
            # Use real data from infrastructure agent
            report += "📊 Real-Time Infrastructure Status:\n\n"
            report += infra_data['raw_result']
        else:
            # Fallback template
            report += "📊 Infrastructure Overview:\n"
            report += f"• Total Resources: {infra_data.get('total', 'N/A')}\n"
            report += f"• Healthy Resources: {infra_data.get('healthy', 'N/A')}\n"
            report += f"• Health Percentage: {infra_data.get('percentage', 'N/A')}%\n\n"
        
        # AI-powered insights
        if hasattr(self, 'agent'):
            insights_prompt = f"""
            Based on the infrastructure data for the past {time_period}:
            {infra_data.get('raw_result', 'No data available')}
            
            Provide:
            1. Key insights about infrastructure health
            2. Potential risks or concerns
            3. Recommendations for improvement
            4. Capacity planning suggestions
            """
            
            insights = await self.agent.invoke_semantic_function(insights_prompt)
            report += f"\n💡 AI-Powered Insights:\n{insights}\n"
        
        return report
    
    async def _generate_cost_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate cost analysis and optimization report."""
        report = "\n=== COST OPTIMIZATION REPORT ===\n\n"
        
        cost_data = data.get('cost', {})
        
        if cost_data.get('raw_result'):
            # Use real data from cost agent
            report += "💰 Real-Time Cost Analysis:\n\n"
            report += cost_data['raw_result']
        else:
            # Fallback template
            report += "💰 Cost Summary:\n"
            report += f"• Total Cost: ${cost_data.get('total_cost', 0):,.2f}\n"
            report += "• No detailed cost data available\n\n"
        
        # AI-powered cost insights
        if hasattr(self, 'agent'):
            cost_prompt = f"""
            Analyze the following cost data for {time_period}:
            {cost_data.get('raw_result', 'No data available')}
            
            Provide:
            1. Cost trends and patterns
            2. Biggest cost drivers
            3. Specific optimization opportunities
            4. Expected savings from recommendations
            5. Priority actions for cost reduction
            """
            
            cost_insights = await self.agent.invoke_semantic_function(cost_prompt)
            report += f"\n📈 Cost Optimization Strategy:\n{cost_insights}\n"
        
        return report
    
    async def _generate_incident_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate incident analysis and resolution report."""
        report = "\n=== INCIDENT ANALYSIS REPORT ===\n\n"
        
        incident_data = data.get('incidents', {})
        
        if not incident_data:
            # Try to get recent incidents from logs
            report += "🚨 Incident Overview:\n"
            report += "No specific incident data provided.\n\n"
            
            # Generate proactive incident prevention report
            if hasattr(self, 'agent'):
                prevention_prompt = f"""
                Create an incident prevention report for the past {time_period} covering:
                1. Common incident patterns in cloud infrastructure
                2. Proactive monitoring recommendations
                3. Incident response best practices
                4. Automation opportunities to prevent incidents
                5. Key metrics to track
                """
                
                prevention_report = await self.agent.invoke_semantic_function(prevention_prompt)
                report += f"🛡️ Incident Prevention Strategy:\n{prevention_report}\n"
        else:
            # Process actual incident data
            report += f"🚨 Incidents in the past {time_period}:\n"
            report += f"• Total Incidents: {incident_data.get('total_incidents', 0)}\n"
            report += f"• Resolved: {incident_data.get('resolved_incidents', 0)}\n"
            report += f"• Open: {incident_data.get('open_incidents', 0)}\n"
            report += f"• Average Resolution Time: {incident_data.get('average_resolution_time', 'N/A')} hours\n\n"
        
        return report
    
    async def _generate_deployment_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate deployment activity and success rate report."""
        report = "\n=== DEPLOYMENT REPORT ===\n\n"
        
        deployment_data = data.get('deployments', {})
        
        if deployment_data.get('raw_result'):
            # Use real deployment data
            report += "🚀 Deployment Activity:\n\n"
            report += deployment_data['raw_result']
        else:
            # Fallback template
            report += "🚀 Deployment Overview:\n"
            report += f"• Total Deployments: {deployment_data.get('total', 0)}\n"
            report += "• No detailed deployment data available\n\n"
        
        # AI-powered deployment insights
        if hasattr(self, 'agent'):
            deployment_prompt = f"""
            Based on deployment data for {time_period}:
            {deployment_data.get('raw_result', 'No data available')}
            
            Provide insights on:
            1. Deployment patterns and frequency
            2. Success rate analysis
            3. Common deployment issues
            4. Recommendations for improving deployment pipeline
            5. Best practices for the team
            """
            
            deployment_insights = await self.agent.invoke_semantic_function(deployment_prompt)
            report += f"\n🎯 Deployment Excellence:\n{deployment_insights}\n"
        
        return report
    
    async def _generate_kubernetes_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate Kubernetes cluster report."""
        report = "\n=== KUBERNETES CLUSTER REPORT ===\n\n"
        
        k8s_data = data.get('kubernetes', {})
        
        if k8s_data.get('raw_result'):
            # Use real Kubernetes data
            report += "☸️ Cluster Status:\n\n"
            report += k8s_data['raw_result']
        else:
            # Fallback template
            report += "☸️ Kubernetes Overview:\n"
            report += "• No Kubernetes data available\n\n"
        
        return report
    
    async def _generate_executive_summary(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate executive summary report using AI."""
        report = "\n=== EXECUTIVE SUMMARY ===\n\n"
        
        # Compile all available data
        all_data = {
            'infrastructure': data.get('infrastructure', {}).get('raw_result', 'No infrastructure data'),
            'cost': data.get('cost', {}).get('raw_result', 'No cost data'),
            'deployments': data.get('deployments', {}).get('raw_result', 'No deployment data'),
            'kubernetes': data.get('kubernetes', {}).get('raw_result', 'No Kubernetes data')
        }
        
        if hasattr(self, 'agent'):
            exec_prompt = f"""
            Create an executive summary for the {time_period} period based on:
            
            Infrastructure Status:
            {all_data['infrastructure'][:500]}
            
            Cost Analysis:
            {all_data['cost'][:500]}
            
            Deployment Activity:
            {all_data['deployments'][:500]}
            
            Kubernetes Status:
            {all_data['kubernetes'][:500]}
            
            Include:
            1. Key highlights and achievements
            2. Critical issues requiring attention
            3. Cost optimization opportunities
            4. Strategic recommendations
            5. Metrics summary (bullet points)
            6. Action items for next period
            
            Keep it concise and focused on business impact.
            """
            
            executive_summary = await self.agent.invoke_semantic_function(exec_prompt)
            report += executive_summary
        else:
            # Fallback summary
            report += f"📋 Period Overview ({time_period}):\n\n"
            report += "• Infrastructure: Monitoring active\n"
            report += "• Cost Management: Analysis in progress\n"
            report += "• Deployments: Tracking enabled\n"
            report += "• Kubernetes: Clusters monitored\n\n"
            report += "For detailed insights, ensure all agents are properly configured.\n"
        
        return report
    
    def _generate_report_header(self, report_type: str, time_period: str) -> str:
        """Generate standard report header."""
        header = f"\n{'='*60}\n"
        header += f"   DevOps Sentinel - {report_type.title()} Report\n"
        header += f"   Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        header += f"   Period: {time_period}\n"
        header += f"   Data Source: Real-time Azure APIs\n"
        header += f"{'='*60}\n"
        return header
    
    def _generate_report_footer(self) -> str:
        """Generate standard report footer."""
        footer = f"\n{'='*60}\n"
        footer += f"Report generated by DevOps Sentinel Multi-Agent System\n"
        footer += f"Powered by Azure OpenAI and Semantic Kernel\n"
        footer += f"For questions or clarifications, contact the DevOps team\n"
        footer += f"{'='*60}\n"
        return footer
    
    @kernel_function(name="create_custom_report", description="Create a custom report based on specific requirements")
    async def create_custom_report(self, requirements: str) -> str:
        """Create a custom report based on user requirements."""
        try:
            if hasattr(self, 'agent'):
                custom_prompt = f"""
                Create a custom DevOps report based on these requirements:
                {requirements}
                
                Structure the report professionally with:
                - Executive summary
                - Detailed findings
                - Data visualizations (describe what charts/graphs would be helpful)
                - Recommendations
                - Next steps
                
                Focus on actionable insights and business value.
                """
                
                custom_report = await self.agent.invoke_semantic_function(custom_prompt)
                
                # Add header and footer
                report = self._generate_report_header("custom", "as requested")
                report += custom_report
                report += self._generate_report_footer()
                
                return report
            else:
                return "Custom report generation requires AI model configuration."
                
        except Exception as e:
            self.logger.error(f"Error creating custom report: {str(e)}")
            return f"Error creating custom report: {str(e)}"


class ReportGeneratorAgent(BaseDevOpsAgent):
    """Agent responsible for generating comprehensive DevOps reports."""
    
    def __init__(self):
        super().__init__(
            name="ReportGenerator",
            description="Generates comprehensive DevOps reports and analytics",
            agent_type="report_generator"
        )
        self.capabilities = [
            "infrastructure_reporting",
            "cost_reporting",
            "incident_reporting",
            "deployment_reporting",
            "kubernetes_reporting",
            "executive_summaries",
            "custom_reports",
            "ai_powered_insights"
        ]
        self.orchestrator = None  # Will be set by orchestrator
        
    async def _setup_plugins(self):
        """Setup report generation plugins."""
        self.report_plugin = ReportGeneratorPlugin()
        self.report_plugin.agent = self  # Give plugin access to agent
        
        if self.kernel:
            self.kernel.add_plugin(
                self.report_plugin,
                "ReportGenerator"
            )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process report generation requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'generate_report':
                report_type = params.get('report_type', 'executive')
                data = params.get('data', {})
                time_period = params.get('time_period', '30d')
                result = await self.report_plugin.generate_report(report_type, data, time_period)
                
            elif action == 'custom_report':
                requirements = params.get('requirements', 'Generate a comprehensive DevOps report')
                result = await self.report_plugin.create_custom_report(requirements)
                
            else:
                # Use AI for unknown report requests
                analysis_prompt = f"""
                Analyze this report generation request:
                Action: {action}
                Parameters: {params}
                
                Based on my reporting capabilities: {self.capabilities}
                
                Provide guidance on what type of report would be most valuable.
                """
                result = await self.invoke_semantic_function(analysis_prompt)
                
            return {
                'agent': self.name,
                'action': action,
                'status': 'success',
                'result': result,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {
                'agent': self.name,
                'action': action,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }