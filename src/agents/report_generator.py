"""Report generator agent for creating DevOps reports."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_agent import BaseDevOpsAgent, DevOpsAgentPlugin


class ReportGeneratorPlugin(DevOpsAgentPlugin):
    """Plugin for report generation capabilities."""
    
    def __init__(self):
        super().__init__("report_generator")
        self.report_templates = {
            'infrastructure': self._generate_infrastructure_report,
            'cost': self._generate_cost_report,
            'incident': self._generate_incident_report,
            'deployment': self._generate_deployment_report,
            'executive': self._generate_executive_summary
        }
        
    async def generate_report(self, report_type: str, data: Dict[str, Any], time_period: str = "30d") -> str:
        """Generate a specific type of report."""
        try:
            self.logger.info(f"Generating {report_type} report for period: {time_period}")
            
            if report_type not in self.report_templates:
                return f"Unknown report type: {report_type}. Available types: {', '.join(self.report_templates.keys())}"
            
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
    
    async def _generate_infrastructure_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate infrastructure health and performance report."""
        report = "\n=== INFRASTRUCTURE REPORT ===\n\n"
        
        # Mock data for demonstration
        infrastructure_data = data.get('infrastructure', {
            'total_resources': 156,
            'healthy_resources': 142,
            'resources_with_issues': 14,
            'uptime_percentage': 99.2,
            'performance_issues': 3,
            'capacity_alerts': 2
        })
        
        report += f"📊 Infrastructure Overview:\n"
        report += f"• Total Resources: {infrastructure_data['total_resources']}\n"
        report += f"• Healthy Resources: {infrastructure_data['healthy_resources']}\n"
        report += f"• Resources with Issues: {infrastructure_data['resources_with_issues']}\n"
        report += f"• Overall Uptime: {infrastructure_data['uptime_percentage']}%\n\n"
        
        report += f"⚠️ Issues Summary:\n"
        report += f"• Performance Issues: {infrastructure_data['performance_issues']}\n"
        report += f"• Capacity Alerts: {infrastructure_data['capacity_alerts']}\n\n"
        
        # Top issues
        top_issues = [
            "High CPU utilization on web-server-01 (avg 85%)",
            "Storage capacity warning on database-server-02 (90% full)",
            "Network latency increase in East US region"
        ]
        
        report += "🔍 Top Issues:\n"
        for i, issue in enumerate(top_issues, 1):
            report += f"{i}. {issue}\n"
        
        report += "\n📈 Recommendations:\n"
        report += "• Scale up web-server-01 or optimize application performance\n"
        report += "• Add additional storage to database-server-02\n"
        report += "• Investigate network configuration in East US region\n\n"
        
        return report
    
    async def _generate_cost_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate cost analysis and optimization report."""
        report = "\n=== COST OPTIMIZATION REPORT ===\n\n"
        
        # Mock cost data
        cost_data = data.get('cost', {
            'current_monthly_cost': 15000.00,
            'projected_monthly_cost': 16200.00,
            'month_over_month_change': 8.0,
            'potential_savings': 3500.00,
            'cost_by_service': {
                'Compute': 8000.00,
                'Storage': 2000.00,
                'Networking': 1500.00,
                'Databases': 2500.00,
                'Other': 1000.00
            }
        })
        
        report += f"💰 Cost Summary:\n"
        report += f"• Current Monthly Cost: ${cost_data['current_monthly_cost']:,.2f}\n"
        report += f"• Projected Monthly Cost: ${cost_data['projected_monthly_cost']:,.2f}\n"
        report += f"• Month-over-Month Change: {cost_data['month_over_month_change']:+.1f}%\n"
        report += f"• Potential Monthly Savings: ${cost_data['potential_savings']:,.2f}\n\n"
        
        report += f"📊 Cost Breakdown by Service:\n"
        for service, cost in cost_data['cost_by_service'].items():
            percentage = (cost / cost_data['current_monthly_cost']) * 100
            report += f"• {service}: ${cost:,.2f} ({percentage:.1f}%)\n"
        
        report += "\n💡 Cost Optimization Opportunities:\n"
        report += f"• Reserved Instance Savings: ${cost_data['potential_savings'] * 0.4:,.2f}/month\n"
        report += f"• Rightsizing VMs: ${cost_data['potential_savings'] * 0.3:,.2f}/month\n"
        report += f"• Storage Optimization: ${cost_data['potential_savings'] * 0.2:,.2f}/month\n"
        report += f"• Unused Resource Cleanup: ${cost_data['potential_savings'] * 0.1:,.2f}/month\n\n"
        
        return report
    
    async def _generate_incident_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate incident analysis and resolution report."""
        report = "\n=== INCIDENT ANALYSIS REPORT ===\n\n"
        
        # Mock incident data
        incident_data = data.get('incidents', {
            'total_incidents': 12,
            'resolved_incidents': 10,
            'open_incidents': 2,
            'average_resolution_time': 2.5,
            'incidents_by_severity': {
                'Critical': 1,
                'High': 3,
                'Medium': 5,
                'Low': 3
            },
            'incidents_by_category': {
                'Performance': 4,
                'Availability': 3,
                'Security': 2,
                'Capacity': 3
            }
        })
        
        report += f"🚨 Incident Overview:\n"
        report += f"• Total Incidents: {incident_data['total_incidents']}\n"
        report += f"• Resolved: {incident_data['resolved_incidents']}\n"
        report += f"• Open: {incident_data['open_incidents']}\n"
        report += f"• Average Resolution Time: {incident_data['average_resolution_time']} hours\n\n"
        
        report += f"📊 Incidents by Severity:\n"
        for severity, count in incident_data['incidents_by_severity'].items():
            report += f"• {severity}: {count}\n"
        
        report += f"\n📊 Incidents by Category:\n"
        for category, count in incident_data['incidents_by_category'].items():
            report += f"• {category}: {count}\n"
        
        report += "\n🔍 Key Insights:\n"
        report += "• Performance incidents are the most common (33%)\n"
        report += "• Average resolution time has improved by 15% this period\n"
        report += "• No critical incidents remained open for more than 4 hours\n\n"
        
        report += "📈 Recommendations:\n"
        report += "• Implement proactive performance monitoring\n"
        report += "• Enhance capacity planning processes\n"
        report += "• Continue security awareness training\n\n"
        
        return report
    
    async def _generate_deployment_report(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate deployment activity and success rate report."""
        report = "\n=== DEPLOYMENT REPORT ===\n\n"
        
        # Mock deployment data
        deployment_data = data.get('deployments', {
            'total_deployments': 28,
            'successful_deployments': 25,
            'failed_deployments': 3,
            'rollbacks': 2,
            'success_rate': 89.3,
            'average_deployment_time': 8.5,
            'deployments_by_environment': {
                'Production': 8,
                'Staging': 12,
                'Development': 8
            }
        })
        
        report += f"🚀 Deployment Overview:\n"
        report += f"• Total Deployments: {deployment_data['total_deployments']}\n"
        report += f"• Successful: {deployment_data['successful_deployments']}\n"
        report += f"• Failed: {deployment_data['failed_deployments']}\n"
        report += f"• Rollbacks: {deployment_data['rollbacks']}\n"
        report += f"• Success Rate: {deployment_data['success_rate']:.1f}%\n"
        report += f"• Average Deployment Time: {deployment_data['average_deployment_time']} minutes\n\n"
        
        report += f"📊 Deployments by Environment:\n"
        for env, count in deployment_data['deployments_by_environment'].items():
            report += f"• {env}: {count}\n"
        
        report += "\n🔍 Analysis:\n"
        report += "• Deployment success rate is within acceptable range (>85%)\n"
        report += "• Most deployments are in staging environment (testing focus)\n"
        report += "• Rollback rate is low, indicating good pre-deployment testing\n\n"
        
        report += "📈 Recommendations:\n"
        report += "• Implement automated deployment testing\n"
        report += "• Consider blue-green deployments for production\n"
        report += "• Enhance rollback automation procedures\n\n"
        
        return report
    
    async def _generate_executive_summary(self, data: Dict[str, Any], time_period: str) -> str:
        """Generate executive summary report."""
        report = "\n=== EXECUTIVE SUMMARY ===\n\n"
        
        report += f"📋 Period Overview ({time_period}):\n\n"
        
        report += "🎯 Key Metrics:\n"
        report += "• Infrastructure Uptime: 99.2%\n"
        report += "• Incident Resolution: 83% within SLA\n"
        report += "• Deployment Success Rate: 89.3%\n"
        report += "• Cost Optimization: $3.5K potential monthly savings identified\n\n"
        
        report += "✅ Achievements:\n"
        report += "• Zero critical incidents with extended downtime\n"
        report += "• Reduced average incident resolution time by 15%\n"
        report += "• Implemented automated monitoring for 95% of resources\n"
        report += "• Identified significant cost optimization opportunities\n\n"
        
        report += "⚠️ Areas for Improvement:\n"
        report += "• Performance monitoring needs enhancement\n"
        report += "• Capacity planning requires attention\n"
        report += "• Deployment automation can be improved\n"
        report += "• Cost optimization recommendations need implementation\n\n"
        
        report += "🎯 Next Period Focus:\n"
        report += "• Implement reserved instance purchases\n"
        report += "• Enhance performance monitoring capabilities\n"
        report += "• Automate more deployment processes\n"
        report += "• Continue infrastructure optimization efforts\n\n"
        
        return report
    
    def _generate_report_header(self, report_type: str, time_period: str) -> str:
        """Generate standard report header."""
        header = f"\n{'='*60}\n"
        header += f"   DevOps Sentinel - {report_type.title()} Report\n"
        header += f"   Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        header += f"   Period: {time_period}\n"
        header += f"{'='*60}\n"
        return header
    
    def _generate_report_footer(self) -> str:
        """Generate standard report footer."""
        footer = f"\n{'='*60}\n"
        footer += f"Report generated by DevOps Sentinel Multi-Agent System\n"
        footer += f"For questions or clarifications, contact the DevOps team\n"
        footer += f"{'='*60}\n"
        return footer


class ReportGeneratorAgent(BaseDevOpsAgent):
    """Agent responsible for generating DevOps reports."""
    
    def __init__(self):
        super().__init__("ReportGenerator", "Generates comprehensive DevOps reports and analytics")
        self.capabilities = [
            "infrastructure_reporting",
            "cost_reporting",
            "incident_reporting",
            "deployment_reporting",
            "executive_summaries"
        ]
        
    async def _setup_plugins(self):
        """Setup report generation plugins."""
        self.report_plugin = ReportGeneratorPlugin()
        self.kernel.add_plugin(
            plugin=self.report_plugin,
            plugin_name="report_generator",
            description="Report generation capabilities"
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
            else:
                result = f"Unknown action: {action}"
                
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