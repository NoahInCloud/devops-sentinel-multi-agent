"""Infrastructure monitoring agent for Azure resources using Azure MCP."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Use Azure MCP instead of direct SDK imports
from utils.azure_mcp_client import azure_mcp_client
from .base_agent import BaseDevOpsAgent, DevOpsAgentPlugin


class InfrastructureMonitorPlugin(DevOpsAgentPlugin):
    """Plugin for infrastructure monitoring capabilities."""
    
    def __init__(self, subscription_id: Optional[str] = None): # Made subscription_id optional as MCP might not always need it explicitly
        super().__init__("infrastructure_monitor")
        self.subscription_id = subscription_id
        # SDK clients removed, will use azure_mcp_client
        
    async def get_resource_health(self, resource_group: Optional[str] = None) -> str:
        """Get health status of Azure resources using Azure MCP."""
        try:
            self.logger.info(f"Checking resource health via MCP for subscription: {self.subscription_id or 'default'}")
            
            cli_command = "az resource list"
            if resource_group:
                cli_command += f" --resource-group \\\"{resource_group}\\\""
            if self.subscription_id:
                 cli_command += f" --subscription \\\"{self.subscription_id}\\\""

            response = await azure_mcp_client.execute_azure_cli(cli_command)
            
            if response.get('status') == 'error' or 'error' in response or not response.get('stdout'):
                error_message = response.get('error', response.get('stderr', 'Unknown error from MCP'))
                self.logger.error(f"Error from MCP getting resource list: {error_message}")
                return f"Error checking resource health via MCP: {error_message}"

            try:
                resources = json.loads(response['stdout'])
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response from MCP: {str(e)}\\nResponse: {response['stdout']}")
                return f"Error parsing MCP response: {str(e)}"

            healthy_count = 0
            total_count = len(resources)
            issues = []
            
            for resource in resources:
                # Check basic resource status
                if resource.get('provisioningState') == 'Succeeded':
                    healthy_count += 1
                else:
                    issues.append(f"{resource.get('name', 'Unknown Resource')}: {resource.get('provisioningState', 'Unknown')}")
                        
            health_percentage = (healthy_count / total_count * 100) if total_count > 0 else 0
            
            result_str = f"Infrastructure Health Report (via MCP):\\n"
            result_str += f"- Total Resources: {total_count}\\n"
            result_str += f"- Healthy Resources: {healthy_count}\\n"
            result_str += f"- Health Percentage: {health_percentage:.1f}%\\n"
            
            if issues:
                result_str += f"\\nIssues Found:\\n"
                for issue in issues[:5]:  # Limit to first 5 issues
                    result_str += f"- {issue}\\n"
                    
            return result_str
            
        except Exception as e:
            self.logger.error(f"Error checking resource health via MCP: {str(e)}")
            return f"Error checking resource health via MCP: {str(e)}"
    
    async def get_metrics(self, resource_id: str, metric_names: str) -> str: # Changed metric_name to metric_names for az cli
        """Get metrics for a specific Azure resource using Azure MCP."""
        try:
            self.logger.info(f"Getting metrics via MCP for resource: {resource_id}, metrics: {metric_names}")
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            timespan = f"{start_time.isoformat()}/{end_time.isoformat()}"
            
            # Note: `az monitor metrics list` expects metric names separated by spaces.
            cli_command = f"az monitor metrics list --resource \\\"{resource_id}\\\" --metrics {metric_names} --interval PT5M --timespan \\\"{timespan}\\\""
            if self.subscription_id:
                cli_command += f" --subscription \\\"{self.subscription_id}\\\""

            response = await azure_mcp_client.execute_azure_cli(cli_command)

            if response.get('status') == 'error' or 'error' in response or not response.get('stdout'):
                error_message = response.get('error', response.get('stderr', 'Unknown error from MCP'))
                self.logger.error(f"Error from MCP getting metrics: {error_message}")
                return f"Error getting metrics via MCP: {error_message}"

            try:
                metrics_data = json.loads(response['stdout'])
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response from MCP: {str(e)}\\nResponse: {response['stdout']}")
                return f"Error parsing MCP response for metrics: {str(e)}"
            
            result_str = f"Metrics for {metric_names} on {resource_id} (via MCP):\\n"
            if metrics_data and 'value' in metrics_data:
                for metric in metrics_data['value']:
                    result_str += f"Metric: {metric.get('name', {}).get('value', 'Unknown Metric')}\\n"
                    if metric.get('timeseries'):
                        for ts in metric['timeseries']:
                            if ts.get('data'):
                                latest_data = ts['data'][-1] if ts['data'] else None
                                if latest_data:
                                    # Common properties are average, total, minimum, maximum, count
                                    value = latest_data.get('average', latest_data.get('total', latest_data.get('count', 'N/A')))
                                    result_str += f"- Latest Value: {value}\\n"
                                    result_str += f"- Timestamp: {latest_data.get('timeStamp')}\\n"
                    else:
                        result_str += "- No timeseries data available\\n"
            else:
                result_str += "No metrics data returned or data is not in expected format.\\n"
                        
            return result_str
            
        except Exception as e:
            self.logger.error(f"Error getting metrics via MCP: {str(e)}")
            return f"Error getting metrics via MCP: {str(e)}"
    
    async def check_alerts(self) -> str:
        """Check for active alerts in the subscription using Azure MCP."""
        try:
            self.logger.info(f"Checking for active alerts via MCP for subscription: {self.subscription_id or 'default'}")
            
            cli_command = "az monitor alert list" # This lists metric alerts. For activity log alerts: az monitor activity-log alert list
            if self.subscription_id:
                cli_command += f" --subscription \\\"{self.subscription_id}\\\""

            response = await azure_mcp_client.execute_azure_cli(cli_command)

            if response.get('status') == 'error' or 'error' in response or not response.get('stdout'):
                error_message = response.get('error', response.get('stderr', 'Unknown error from MCP'))
                self.logger.error(f"Error from MCP checking alerts: {error_message}")
                return f"Error checking alerts via MCP: {error_message}"

            try:
                alerts = json.loads(response['stdout'])
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response from MCP: {str(e)}\\nResponse: {response['stdout']}")
                return f"Error parsing MCP response for alerts: {str(e)}"

            active_alerts_count = 0
            alert_details = []

            for alert in alerts:
                if alert.get('enabled', False): # 'enabled' might not be the direct field for "active", depends on alert type
                    active_alerts_count +=1
                    alert_details.append({
                        'name': alert.get('name', 'Unknown Alert'),
                        'severity': alert.get('properties', {}).get('severity', 'Unknown'),
                        'resourceGroup': alert.get('resourceGroup', 'N/A'),
                        'condition': alert.get('properties', {}).get('condition', {}).get('allOf', [{}])[0].get('metricName', 'N/A')
                    })
            
            result_str = f"Alert Status (via MCP):\\n"
            result_str += f"- Total Alert Rules Found: {len(alerts)}\\n\" # This is total rules, not necessarily "active" alerts firing
            result_str += f"- Enabled Alert Rules: {active_alerts_count}\\n\" # More accurately, enabled rules
            
            if alert_details:
                result_str += "\\nEnabled Alert Rule Details (first 5):\\n"
                for alert_info in alert_details[:5]:
                    result_str += f"- Name: {alert_info['name']}, RG: {alert_info['resourceGroup']}, Severity: {alert_info['severity']}, Condition: {alert_info['condition']}\\n"
                    
            return result_str
            
        except Exception as e:
            self.logger.error(f"Error checking alerts via MCP: {str(e)}")
            return f"Error checking alerts via MCP: {str(e)}"


class InfrastructureMonitorAgent(BaseDevOpsAgent):
    """Agent responsible for monitoring Azure infrastructure."""
    
    def __init__(self, subscription_id: Optional[str] = None): # Allow optional subscription_id
        super().__init__("InfrastructureMonitor", "Monitors Azure infrastructure health and metrics using Azure MCP")
        self.subscription_id = subscription_id
        self.capabilities = [
            "resource_health_monitoring", 
            "metrics_collection", 
            "alert_management",
            "performance_tracking"
        ]
        
    async def _setup_plugins(self):
        """Setup infrastructure monitoring plugins."""
        # Ensure MCP client is started (ideally by orchestrator or a global startup)
        if not azure_mcp_client.is_connected:
            self.logger.info("Attempting to start Azure MCP server from InfrastructureMonitorAgent...")
            await azure_mcp_client.start_mcp_server()
            if not azure_mcp_client.is_connected:
                self.logger.error("Failed to start Azure MCP server. Monitoring capabilities will be limited.")

        self.monitor_plugin = InfrastructureMonitorPlugin(self.subscription_id)
        self.kernel.add_plugin(
            plugin=self.monitor_plugin, 
            plugin_name="infrastructure_monitor",
            description="Infrastructure monitoring capabilities via Azure MCP"
        )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process infrastructure monitoring requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        # Ensure MCP client is ready before processing
        if not azure_mcp_client.is_connected:
            await azure_mcp_client.start_mcp_server() # Attempt to start if not connected
            if not azure_mcp_client.is_connected:
                 return {
                    'agent': self.name,
                    'action': action,
                    'status': 'error',
                    'error': 'Azure MCP Server is not connected. Cannot process request.',
                    'timestamp': datetime.utcnow().isoformat()
                }

        try:
            if action == 'check_health':
                result = await self.monitor_plugin.get_resource_health(
                    params.get('resource_group')
                )
            elif action == 'get_metrics':
                result = await self.monitor_plugin.get_metrics(
                    params.get('resource_id', ''),
                    params.get('metric_names', 'Percentage CPU') # Changed to metric_names
                )
            elif action == 'check_alerts':
                result = await self.monitor_plugin.check_alerts()
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