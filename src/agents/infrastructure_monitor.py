"""Infrastructure monitoring agent for Azure resources using real Azure APIs."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from azure.monitor.query import MetricAggregationType
from azure.core.exceptions import AzureError

from utils.azure_client import get_azure_client_manager
from agents.base_agent import BaseDevOpsAgent, DevOpsAgentPlugin
from semantic_kernel.functions import kernel_function


class InfrastructureMonitorPlugin(DevOpsAgentPlugin):
    """Plugin for infrastructure monitoring capabilities."""
    
    def __init__(self, subscription_id: str):
        super().__init__("infrastructure_monitor")
        self.subscription_id = subscription_id
        self.azure_clients = get_azure_client_manager(subscription_id)
        
    @kernel_function(name="get_resource_health", description="Get health status of Azure resources")
    async def get_resource_health(self, resource_group: Optional[str] = None) -> str:
        """Get health status of Azure resources using real Azure APIs."""
        try:
            self.logger.info(f"Checking resource health for subscription: {self.subscription_id}")
            
            resource_client = self.azure_clients.get_resource_client()
            monitor_client = self.azure_clients.get_monitor_client()
            
            # Get resources
            if resource_group:
                resources = list(resource_client.resources.list_by_resource_group(resource_group))
            else:
                resources = list(resource_client.resources.list())
            
            total_resources = len(resources)
            healthy_resources = 0
            warning_resources = 0
            critical_resources = 0
            issues = []
            
            # Check each resource
            for resource in resources[:50]:  # Limit to first 50 for performance
                try:
                    # Get resource health using availability status
                    resource_id = resource.id
                    
                    # Check if resource has recent metrics (indicates it's active)
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=1)
                    
                    # Get metrics based on resource type
                    if resource.type.lower().startswith('microsoft.compute/virtualmachines'):
                        metric_names = ["Percentage CPU", "Available Memory Bytes"]
                    elif resource.type.lower().startswith('microsoft.storage/storageaccounts'):
                        metric_names = ["UsedCapacity", "Availability"]
                    elif resource.type.lower().startswith('microsoft.sql/servers/databases'):
                        metric_names = ["cpu_percent", "storage_percent"]
                    else:
                        metric_names = []
                    
                    is_healthy = True
                    
                    if metric_names:
                        for metric_name in metric_names:
                            try:
                                metrics = monitor_client.metrics.list(
                                    resource_id,
                                    timespan=f"{start_time}/{end_time}",
                                    interval="PT5M",
                                    metricnames=metric_name,
                                    aggregation="Average"
                                )
                                
                                for metric in metrics.value:
                                    for timeseries in metric.timeseries:
                                        for data in timeseries.data:
                                            if data.average is not None:
                                                # Check thresholds
                                                if metric_name in ["Percentage CPU", "cpu_percent"]:
                                                    if data.average > 90:
                                                        is_healthy = False
                                                        issues.append(f"{resource.name}: High CPU usage ({data.average:.1f}%)")
                                                elif metric_name == "storage_percent":
                                                    if data.average > 85:
                                                        is_healthy = False
                                                        issues.append(f"{resource.name}: High storage usage ({data.average:.1f}%)")
                            except:
                                # Metric not available for this resource
                                pass
                    
                    if is_healthy:
                        healthy_resources += 1
                    else:
                        warning_resources += 1
                        
                except Exception as e:
                    # Resource health check failed
                    critical_resources += 1
                    issues.append(f"{resource.name}: Health check failed - {str(e)[:50]}")
            
            health_percentage = (healthy_resources / total_resources * 100) if total_resources > 0 else 0
            
            result = f"Infrastructure Health Report (Real Azure Data):\n\n"
            result += f"📊 Overview:\n"
            result += f"• Total Resources: {total_resources}\n"
            result += f"• Healthy Resources: {healthy_resources}\n"
            result += f"• Resources with Warnings: {warning_resources}\n"
            result += f"• Critical Resources: {critical_resources}\n"
            result += f"• Overall Health: {health_percentage:.1f}%\n"
            
            if resource_group:
                result += f"• Resource Group: {resource_group}\n"
            
            if issues:
                result += f"\n⚠️ Issues Found:\n"
                for issue in issues[:10]:  # Show first 10 issues
                    result += f"• {issue}\n"
                if len(issues) > 10:
                    result += f"• ... and {len(issues) - 10} more issues\n"
                    
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking resource health: {str(e)}")
            return f"Error checking resource health: {str(e)}"
    
    @kernel_function(name="get_vm_metrics", description="Get metrics for virtual machines")
    async def get_vm_metrics(self, vm_name: Optional[str] = None, resource_group: Optional[str] = None) -> str:
        """Get metrics for Azure VMs."""
        try:
            compute_client = self.azure_clients.get_compute_client()
            metrics_client = self.azure_clients.get_metrics_query_client()
            
            # Get VMs
            if vm_name and resource_group:
                vms = [compute_client.virtual_machines.get(resource_group, vm_name)]
            elif resource_group:
                vms = list(compute_client.virtual_machines.list(resource_group))
            else:
                vms = list(compute_client.virtual_machines.list_all())
            
            result = f"Virtual Machine Metrics Report:\n\n"
            
            for vm in vms[:10]:  # Limit to 10 VMs
                result += f"\n🖥️ VM: {vm.name}\n"
                result += f"• Location: {vm.location}\n"
                result += f"• Size: {vm.hardware_profile.vm_size}\n"
                result += f"• Status: {vm.provisioning_state}\n"
                
                # Get metrics
                try:
                    end_time = datetime.utcnow()
                    start_time = end_time - timedelta(hours=1)
                    
                    response = await metrics_client.query_resource(
                        resource_uri=vm.id,
                        metric_names=["Percentage CPU", "Network In Total", "Network Out Total", "Disk Read Bytes", "Disk Write Bytes"],
                        timespan=(start_time, end_time),
                        granularity=timedelta(minutes=5),
                        aggregations=[MetricAggregationType.AVERAGE, MetricAggregationType.MAXIMUM]
                    )
                    
                    for metric in response.metrics:
                        if metric.timeseries:
                            for timeseries in metric.timeseries:
                                if timeseries.data:
                                    latest = timeseries.data[-1]
                                    if metric.name == "Percentage CPU" and latest.average is not None:
                                        result += f"• CPU Usage: {latest.average:.1f}% (avg), {latest.maximum:.1f}% (max)\n"
                                    elif metric.name == "Network In Total" and latest.average is not None:
                                        result += f"• Network In: {latest.average / 1024 / 1024:.2f} MB\n"
                                    elif metric.name == "Network Out Total" and latest.average is not None:
                                        result += f"• Network Out: {latest.average / 1024 / 1024:.2f} MB\n"
                                        
                except Exception as e:
                    result += f"• Metrics unavailable: {str(e)[:50]}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting VM metrics: {str(e)}")
            return f"Error getting VM metrics: {str(e)}"
    
    @kernel_function(name="check_alerts", description="Check for active alerts in Azure Monitor")
    async def check_alerts(self) -> str:
        """Check for active alerts using Azure Monitor."""
        try:
            monitor_client = self.azure_clients.get_monitor_client()
            
            # Get alert rules
            alert_rules = list(monitor_client.metric_alerts.list_by_subscription())
            
            # Get activity log alerts
            activity_alerts = list(monitor_client.activity_log_alerts.list_by_subscription_id())
            
            result = f"Azure Monitor Alerts Report:\n\n"
            result += f"📊 Summary:\n"
            result += f"• Total Metric Alert Rules: {len(alert_rules)}\n"
            result += f"• Total Activity Log Alerts: {len(activity_alerts)}\n\n"
            
            # Check metric alerts
            enabled_alerts = 0
            critical_alerts = []
            high_alerts = []
            
            for alert in alert_rules:
                if alert.enabled:
                    enabled_alerts += 1
                    
                    # Check severity
                    severity = alert.severity
                    alert_info = {
                        'name': alert.name,
                        'description': alert.description or 'No description',
                        'severity': severity,
                        'criteria': []
                    }
                    
                    # Get criteria
                    if hasattr(alert, 'criteria') and hasattr(alert.criteria, 'all_of'):
                        for criterion in alert.criteria.all_of:
                            alert_info['criteria'].append(f"{criterion.metric_name} {criterion.operator} {criterion.threshold}")
                    
                    if severity == 0 or severity == 1:  # Critical or Error
                        critical_alerts.append(alert_info)
                    elif severity == 2:  # Warning
                        high_alerts.append(alert_info)
            
            result += f"⚠️ Alert Status:\n"
            result += f"• Enabled Alert Rules: {enabled_alerts}\n"
            result += f"• Critical/Error Alerts: {len(critical_alerts)}\n"
            result += f"• Warning Alerts: {len(high_alerts)}\n\n"
            
            if critical_alerts:
                result += f"🚨 Critical Alerts:\n"
                for alert in critical_alerts[:5]:
                    result += f"• {alert['name']}: {alert['description']}\n"
                    if alert['criteria']:
                        result += f"  Conditions: {', '.join(alert['criteria'][:2])}\n"
            
            # Check recent alert occurrences (activity log)
            try:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=24)
                
                filter_str = f"eventTimestamp ge '{start_time.isoformat()}' and eventTimestamp le '{end_time.isoformat()}' and category eq 'Alert'"
                
                events = monitor_client.activity_logs.list(filter=filter_str)
                recent_alerts = []
                
                for event in events:
                    if hasattr(event, 'category') and event.category.value == 'Alert':
                        recent_alerts.append({
                            'time': event.event_timestamp,
                            'resource': event.resource_id.split('/')[-1] if event.resource_id else 'Unknown',
                            'status': event.status.value if hasattr(event, 'status') else 'Unknown'
                        })
                
                if recent_alerts:
                    result += f"\n📅 Recent Alert Activity (Last 24h):\n"
                    for alert in recent_alerts[:5]:
                        result += f"• {alert['time'].strftime('%Y-%m-%d %H:%M')} - {alert['resource']} ({alert['status']})\n"
                        
            except Exception as e:
                self.logger.warning(f"Could not fetch recent alert activity: {str(e)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking alerts: {str(e)}")
            return f"Error checking alerts: {str(e)}"
    
    @kernel_function(name="get_resource_recommendations", description="Get Azure Advisor recommendations")
    async def get_resource_recommendations(self) -> str:
        """Get recommendations from Azure Advisor."""
        try:
            # Note: Azure Advisor API requires additional setup
            # For now, provide general monitoring recommendations based on metrics
            
            result = f"Infrastructure Recommendations:\n\n"
            
            # Check for common issues
            compute_client = self.azure_clients.get_compute_client()
            
            # Check for stopped VMs
            stopped_vms = []
            oversized_vms = []
            
            for vm in compute_client.virtual_machines.list_all():
                # Get instance view
                try:
                    instance_view = compute_client.virtual_machines.instance_view(
                        vm.id.split('/')[4],  # resource group
                        vm.name
                    )
                    
                    # Check power state
                    for status in instance_view.statuses:
                        if status.code.startswith('PowerState/') and status.code != 'PowerState/running':
                            stopped_vms.append(vm.name)
                            
                except:
                    pass
            
            result += "💡 Recommendations:\n\n"
            
            if stopped_vms:
                result += f"1. **Stopped VMs** ({len(stopped_vms)} found)\n"
                result += f"   Consider deallocating or removing stopped VMs to save costs:\n"
                for vm in stopped_vms[:3]:
                    result += f"   • {vm}\n"
                if len(stopped_vms) > 3:
                    result += f"   • ... and {len(stopped_vms) - 3} more\n"
                result += "\n"
            
            result += "2. **Performance Monitoring**\n"
            result += "   • Enable Azure Monitor for all critical resources\n"
            result += "   • Set up alerts for CPU > 80% and Memory > 85%\n"
            result += "   • Configure auto-scaling for variable workloads\n\n"
            
            result += "3. **Security**\n"
            result += "   • Enable Azure Security Center\n"
            result += "   • Review network security group rules\n"
            result += "   • Enable diagnostic logs for all resources\n\n"
            
            result += "4. **Cost Optimization**\n"
            result += "   • Review and rightsize underutilized VMs\n"
            result += "   • Consider Reserved Instances for stable workloads\n"
            result += "   • Enable auto-shutdown for dev/test resources\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {str(e)}")
            return f"Error getting recommendations: {str(e)}"


class InfrastructureMonitorAgent(BaseDevOpsAgent):
    """Agent responsible for monitoring Azure infrastructure."""
    
    def __init__(self, subscription_id: str):
        super().__init__(
            name="InfrastructureMonitor",
            description="Monitors Azure infrastructure health and metrics",
            agent_type="infrastructure_monitor"
        )
        self.subscription_id = subscription_id
        self.capabilities = [
            "resource_health_monitoring", 
            "metrics_collection", 
            "alert_management",
            "performance_tracking",
            "vm_monitoring",
            "recommendations"
        ]
        
    async def _setup_plugins(self):
        """Setup infrastructure monitoring plugins."""
        self.monitor_plugin = InfrastructureMonitorPlugin(self.subscription_id)
        
        # Add plugin to kernel if available
        if self.kernel:
            self.kernel.add_plugin(
                self.monitor_plugin, 
                "InfrastructureMonitor"
            )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process infrastructure monitoring requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'check_health':
                result = await self.monitor_plugin.get_resource_health(
                    params.get('resource_group')
                )
            elif action == 'get_vm_metrics':
                result = await self.monitor_plugin.get_vm_metrics(
                    params.get('vm_name'),
                    params.get('resource_group')
                )
            elif action == 'check_alerts':
                result = await self.monitor_plugin.check_alerts()
            elif action == 'get_recommendations':
                result = await self.monitor_plugin.get_resource_recommendations()
            else:
                # Use AI to analyze the request
                analysis_prompt = f"""
                Analyze this infrastructure monitoring request:
                Action: {action}
                Parameters: {params}
                
                Based on my capabilities: {self.capabilities}
                
                Provide guidance on how to handle this request.
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