"""Deployment manager agent for real Azure deployments using ARM templates."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from azure.mgmt.resource.resources.models import Deployment, DeploymentProperties, DeploymentMode
from azure.core.exceptions import AzureError

from utils.azure_client import get_azure_client_manager
from agents.base_agent import BaseDevOpsAgent, DevOpsAgentPlugin
from semantic_kernel.functions import kernel_function


class DeploymentManagerPlugin(DevOpsAgentPlugin):
    """Plugin for deployment management capabilities."""
    
    def __init__(self, subscription_id: str):
        super().__init__("deployment_manager")
        self.subscription_id = subscription_id
        self.azure_clients = get_azure_client_manager(subscription_id)
        
    @kernel_function(name="create_deployment", description="Create a new Azure deployment")
    async def create_deployment(self, deployment_config: Dict[str, Any]) -> str:
        """Create a new Azure deployment using ARM templates."""
        try:
            deployment_name = deployment_config.get('name', f"deployment-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
            resource_group = deployment_config.get('resource_group')
            template = deployment_config.get('template', {})
            parameters = deployment_config.get('parameters', {})
            mode = deployment_config.get('mode', 'Incremental')
            
            if not resource_group:
                return "Error: Resource group is required for deployment"
            
            self.logger.info(f"Creating deployment: {deployment_name} in resource group: {resource_group}")
            
            resource_client = self.azure_clients.get_resource_client()
            
            # Ensure resource group exists
            try:
                rg = resource_client.resource_groups.get(resource_group)
            except:
                # Create resource group if it doesn't exist
                location = deployment_config.get('location', 'eastus')
                rg = resource_client.resource_groups.create_or_update(
                    resource_group,
                    {'location': location}
                )
                self.logger.info(f"Created resource group: {resource_group}")
            
            # Create deployment properties
            deployment_properties = DeploymentProperties(
                mode=DeploymentMode.INCREMENTAL if mode == 'Incremental' else DeploymentMode.COMPLETE,
                template=template,
                parameters=parameters
            )
            
            # Start deployment
            deployment_async_operation = resource_client.deployments.begin_create_or_update(
                resource_group_name=resource_group,
                deployment_name=deployment_name,
                parameters=Deployment(properties=deployment_properties)
            )
            
            result = f"Deployment Created Successfully:\n\n"
            result += f"📋 Deployment Details:\n"
            result += f"• Name: {deployment_name}\n"
            result += f"• Resource Group: {resource_group}\n"
            result += f"• Mode: {mode}\n"
            result += f"• Status: In Progress\n"
            result += f"• Started: {datetime.utcnow().isoformat()}\n\n"
            
            # Wait for deployment to complete (with timeout)
            try:
                deployment_result = deployment_async_operation.result(timeout=300)  # 5 minute timeout
                
                if deployment_result.properties.provisioning_state == 'Succeeded':
                    result += "✅ Deployment completed successfully!\n\n"
                    
                    # Get deployment outputs
                    if deployment_result.properties.outputs:
                        result += "📤 Deployment Outputs:\n"
                        for key, value in deployment_result.properties.outputs.items():
                            result += f"• {key}: {value.get('value', 'N/A')}\n"
                else:
                    result += f"⚠️ Deployment finished with state: {deployment_result.properties.provisioning_state}\n"
                    
            except Exception as e:
                result += f"⏱️ Deployment is still in progress. Check status with deployment ID: {deployment_name}\n"
                result += f"Note: Large deployments may take several minutes to complete.\n"
            
            return result
            
        except AzureError as e:
            self.logger.error(f"Azure error creating deployment: {str(e)}")
            return f"Azure error creating deployment: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error creating deployment: {str(e)}")
            return f"Error creating deployment: {str(e)}"
    
    @kernel_function(name="get_deployment_status", description="Get status of an Azure deployment")
    async def get_deployment_status(self, deployment_name: str, resource_group: str) -> str:
        """Get the status of a specific deployment."""
        try:
            self.logger.info(f"Getting status for deployment: {deployment_name}")
            
            resource_client = self.azure_clients.get_resource_client()
            
            # Get deployment
            deployment = resource_client.deployments.get(
                resource_group_name=resource_group,
                deployment_name=deployment_name
            )
            
            result = f"Deployment Status Report:\n\n"
            result += f"📋 Deployment: {deployment_name}\n"
            result += f"• Resource Group: {resource_group}\n"
            result += f"• State: {deployment.properties.provisioning_state}\n"
            result += f"• Mode: {deployment.properties.mode}\n"
            result += f"• Timestamp: {deployment.properties.timestamp}\n"
            
            # Get deployment operations for detailed status
            operations = resource_client.deployment_operations.list(
                resource_group_name=resource_group,
                deployment_name=deployment_name
            )
            
            result += f"\n📊 Deployment Operations:\n"
            for op in operations:
                if op.properties.target_resource:
                    resource_type = op.properties.target_resource.resource_type
                    resource_name = op.properties.target_resource.resource_name
                    status = op.properties.provisioning_state
                    result += f"• {resource_type}/{resource_name}: {status}\n"
                    
                    if op.properties.status_message and op.properties.status_message.get('error'):
                        error = op.properties.status_message['error']
                        result += f"  Error: {error.get('message', 'Unknown error')}\n"
            
            # Get outputs if deployment succeeded
            if deployment.properties.provisioning_state == 'Succeeded' and deployment.properties.outputs:
                result += f"\n📤 Outputs:\n"
                for key, value in deployment.properties.outputs.items():
                    result += f"• {key}: {value.get('value', 'N/A')}\n"
            
            # Duration
            if deployment.properties.timestamp and deployment.properties.duration:
                duration = deployment.properties.duration
                result += f"\n⏱️ Duration: {duration}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting deployment status: {str(e)}")
            return f"Error getting deployment status: {str(e)}"
    
    @kernel_function(name="list_deployments", description="List Azure deployments")
    async def list_deployments(self, resource_group: Optional[str] = None) -> str:
        """List all deployments, optionally filtered by resource group."""
        try:
            self.logger.info(f"Listing deployments for resource group: {resource_group or 'all'}")
            
            resource_client = self.azure_clients.get_resource_client()
            
            if resource_group:
                deployments = list(resource_client.deployments.list_by_resource_group(resource_group))
            else:
                # List deployments for all resource groups
                deployments = []
                for rg in resource_client.resource_groups.list():
                    deployments.extend(list(resource_client.deployments.list_by_resource_group(rg.name)))
            
            result = f"Deployment List:\n\n"
            result += f"📊 Total Deployments: {len(deployments)}\n\n"
            
            if not deployments:
                result += "No deployments found.\n"
            else:
                # Group by status
                by_status = {}
                for deployment in deployments:
                    status = deployment.properties.provisioning_state
                    if status not in by_status:
                        by_status[status] = []
                    by_status[status].append(deployment)
                
                # Show summary
                result += "📈 Status Summary:\n"
                for status, deps in by_status.items():
                    result += f"• {status}: {len(deps)}\n"
                
                result += f"\n📋 Recent Deployments (Last 10):\n"
                
                # Sort by timestamp and show recent
                sorted_deployments = sorted(
                    deployments, 
                    key=lambda d: d.properties.timestamp if d.properties.timestamp else datetime.min,
                    reverse=True
                )[:10]
                
                for deployment in sorted_deployments:
                    rg_name = deployment.id.split('/')[4]
                    result += f"\n• **{deployment.name}**\n"
                    result += f"  Resource Group: {rg_name}\n"
                    result += f"  Status: {deployment.properties.provisioning_state}\n"
                    result += f"  Mode: {deployment.properties.mode}\n"
                    if deployment.properties.timestamp:
                        result += f"  Time: {deployment.properties.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing deployments: {str(e)}")
            return f"Error listing deployments: {str(e)}"
    
    @kernel_function(name="cancel_deployment", description="Cancel an in-progress deployment")
    async def cancel_deployment(self, deployment_name: str, resource_group: str) -> str:
        """Cancel an in-progress deployment."""
        try:
            self.logger.info(f"Cancelling deployment: {deployment_name}")
            
            resource_client = self.azure_clients.get_resource_client()
            
            # Cancel the deployment
            resource_client.deployments.cancel(
                resource_group_name=resource_group,
                deployment_name=deployment_name
            )
            
            result = f"Deployment Cancellation:\n\n"
            result += f"✅ Successfully cancelled deployment: {deployment_name}\n"
            result += f"• Resource Group: {resource_group}\n"
            result += f"• Time: {datetime.utcnow().isoformat()}\n\n"
            result += "Note: Resources already created may need manual cleanup.\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error cancelling deployment: {str(e)}")
            return f"Error cancelling deployment: {str(e)}"
    
    @kernel_function(name="validate_template", description="Validate an ARM template")
    async def validate_template(self, resource_group: str, template: Dict[str, Any], parameters: Dict[str, Any] = None) -> str:
        """Validate an ARM template before deployment."""
        try:
            self.logger.info("Validating deployment template")
            
            resource_client = self.azure_clients.get_resource_client()
            
            # Create deployment properties for validation
            deployment_properties = DeploymentProperties(
                mode=DeploymentMode.INCREMENTAL,
                template=template,
                parameters=parameters or {}
            )
            
            # Validate the template
            validation_result = resource_client.deployments.begin_validate(
                resource_group_name=resource_group,
                deployment_name=f"validation-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                parameters=Deployment(properties=deployment_properties)
            ).result()
            
            result = f"Template Validation Report:\n\n"
            
            if validation_result.error:
                result += "❌ Validation Failed:\n"
                result += f"• Code: {validation_result.error.code}\n"
                result += f"• Message: {validation_result.error.message}\n"
                
                if validation_result.error.details:
                    result += "\nError Details:\n"
                    for detail in validation_result.error.details:
                        result += f"• {detail.code}: {detail.message}\n"
            else:
                result += "✅ Template is valid!\n\n"
                
                # Analyze template
                result += "📋 Template Analysis:\n"
                
                # Count resources
                resources = template.get('resources', [])
                result += f"• Total Resources: {len(resources)}\n"
                
                # Resource types
                resource_types = {}
                for resource in resources:
                    res_type = resource.get('type', 'Unknown')
                    resource_types[res_type] = resource_types.get(res_type, 0) + 1
                
                result += "\n📊 Resources by Type:\n"
                for res_type, count in resource_types.items():
                    result += f"• {res_type}: {count}\n"
                
                # Check for parameters
                params = template.get('parameters', {})
                result += f"\n🔧 Parameters: {len(params)}\n"
                if params:
                    for param_name, param_def in list(params.items())[:5]:
                        param_type = param_def.get('type', 'Unknown')
                        result += f"• {param_name} ({param_type})\n"
                    if len(params) > 5:
                        result += f"• ... and {len(params) - 5} more\n"
                
                # Check for outputs
                outputs = template.get('outputs', {})
                if outputs:
                    result += f"\n📤 Outputs: {len(outputs)}\n"
                    for output_name in list(outputs.keys())[:3]:
                        result += f"• {output_name}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating template: {str(e)}")
            return f"Error validating template: {str(e)}"
    
    @kernel_function(name="get_deployment_template", description="Get template from existing deployment")
    async def get_deployment_template(self, deployment_name: str, resource_group: str) -> str:
        """Export template from an existing deployment."""
        try:
            resource_client = self.azure_clients.get_resource_client()
            
            # Get deployment
            deployment = resource_client.deployments.get(
                resource_group_name=resource_group,
                deployment_name=deployment_name
            )
            
            result = f"Deployment Template Export:\n\n"
            result += f"📋 Deployment: {deployment_name}\n"
            result += f"• Resource Group: {resource_group}\n\n"
            
            # Export template
            exported = resource_client.deployments.export_template(
                resource_group_name=resource_group,
                deployment_name=deployment_name
            )
            
            if exported.template:
                result += "✅ Template exported successfully!\n\n"
                
                # Save template to string (in production, save to file)
                template_json = json.dumps(exported.template, indent=2)
                
                # Show template summary
                resources = exported.template.get('resources', [])
                result += f"📊 Template Summary:\n"
                result += f"• Resources: {len(resources)}\n"
                result += f"• Parameters: {len(exported.template.get('parameters', {}))}\n"
                result += f"• Variables: {len(exported.template.get('variables', {}))}\n"
                result += f"• Outputs: {len(exported.template.get('outputs', {}))}\n\n"
                
                result += "💾 Template can be reused for similar deployments.\n"
                result += f"Size: {len(template_json)} characters\n"
            else:
                result += "❌ No template available for export.\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error exporting template: {str(e)}")
            return f"Error exporting template: {str(e)}"


class DeploymentManagerAgent(BaseDevOpsAgent):
    """Agent responsible for managing Azure deployments."""
    
    def __init__(self, subscription_id: str):
        super().__init__(
            name="DeploymentManager",
            description="Manages Azure resource deployments using ARM templates",
            agent_type="deployment_manager"
        )
        self.subscription_id = subscription_id
        self.capabilities = [
            "deployment_creation",
            "deployment_monitoring",
            "deployment_cancellation",
            "template_validation",
            "template_export",
            "deployment_history"
        ]
        
    async def _setup_plugins(self):
        """Setup deployment management plugins."""
        self.deployment_plugin = DeploymentManagerPlugin(self.subscription_id)
        
        if self.kernel:
            self.kernel.add_plugin(
                self.deployment_plugin,
                "DeploymentManager"
            )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process deployment management requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'create_deployment':
                deployment_config = params.get('deployment_config', {})
                
                # If template_file is provided, load it
                if 'template_file' in deployment_config:
                    template_path = Path(deployment_config['template_file'])
                    if template_path.exists():
                        with open(template_path, 'r') as f:
                            deployment_config['template'] = json.load(f)
                
                result = await self.deployment_plugin.create_deployment(deployment_config)
                
            elif action == 'get_status':
                deployment_name = params.get('deployment_name', '')
                resource_group = params.get('resource_group', '')
                result = await self.deployment_plugin.get_deployment_status(deployment_name, resource_group)
                
            elif action == 'list_deployments':
                resource_group = params.get('resource_group')
                result = await self.deployment_plugin.list_deployments(resource_group)
                
            elif action == 'cancel_deployment':
                deployment_name = params.get('deployment_name', '')
                resource_group = params.get('resource_group', '')
                result = await self.deployment_plugin.cancel_deployment(deployment_name, resource_group)
                
            elif action == 'validate_template':
                resource_group = params.get('resource_group', '')
                template = params.get('template', {})
                parameters = params.get('parameters', {})
                result = await self.deployment_plugin.validate_template(resource_group, template, parameters)
                
            elif action == 'export_template':
                deployment_name = params.get('deployment_name', '')
                resource_group = params.get('resource_group', '')
                result = await self.deployment_plugin.get_deployment_template(deployment_name, resource_group)
                
            else:
                # Use AI for complex deployment scenarios
                analysis_prompt = f"""
                Analyze this deployment request:
                Action: {action}
                Parameters: {params}
                
                Based on my deployment management capabilities: {self.capabilities}
                
                Provide guidance on handling this deployment scenario.
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