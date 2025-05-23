"""Deployment manager agent for Azure deployments."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_agent import BaseDevOpsAgent, DevOpsAgentPlugin


class DeploymentManagerPlugin(DevOpsAgentPlugin):
    """Plugin for deployment management capabilities."""
    
    def __init__(self, subscription_id: str):
        super().__init__("deployment_manager")
        self.subscription_id = subscription_id
        self.active_deployments = {}
        
    async def create_deployment(self, deployment_config: Dict[str, Any]) -> str:
        """Create a new Azure deployment."""
        try:
            deployment_name = deployment_config.get('name', f"deployment-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
            resource_group = deployment_config.get('resource_group', 'default-rg')
            template = deployment_config.get('template', {})
            parameters = deployment_config.get('parameters', {})
            
            self.logger.info(f"Creating deployment: {deployment_name}")
            
            # Mock deployment creation
            deployment_id = f"dep-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            deployment_info = {
                'id': deployment_id,
                'name': deployment_name,
                'resource_group': resource_group,
                'status': 'Running',
                'start_time': datetime.utcnow().isoformat(),
                'template': template,
                'parameters': parameters,
                'progress': 0
            }
            
            self.active_deployments[deployment_id] = deployment_info
            
            # Simulate deployment progress
            await self._simulate_deployment_progress(deployment_id)
            
            result = f"Deployment Created Successfully:\n\n"
            result += f"Deployment ID: {deployment_id}\n"
            result += f"Name: {deployment_name}\n"
            result += f"Resource Group: {resource_group}\n"
            result += f"Status: {deployment_info['status']}\n"
            result += f"Start Time: {deployment_info['start_time']}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating deployment: {str(e)}")
            return f"Error creating deployment: {str(e)}"
    
    async def get_deployment_status(self, deployment_id: str) -> str:
        """Get the status of a specific deployment."""
        try:
            self.logger.info(f"Getting status for deployment: {deployment_id}")
            
            if deployment_id not in self.active_deployments:
                return f"Deployment {deployment_id} not found"
            
            deployment = self.active_deployments[deployment_id]
            
            result = f"Deployment Status Report:\n\n"
            result += f"Deployment ID: {deployment['id']}\n"
            result += f"Name: {deployment['name']}\n"
            result += f"Resource Group: {deployment['resource_group']}\n"
            result += f"Status: {deployment['status']}\n"
            result += f"Progress: {deployment['progress']}%\n"
            result += f"Start Time: {deployment['start_time']}\n"
            
            if deployment.get('end_time'):
                result += f"End Time: {deployment['end_time']}\n"
                
            if deployment.get('error'):
                result += f"Error: {deployment['error']}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting deployment status: {str(e)}")
            return f"Error getting deployment status: {str(e)}"
    
    async def list_deployments(self, resource_group: Optional[str] = None) -> str:
        """List all deployments, optionally filtered by resource group."""
        try:
            self.logger.info(f"Listing deployments for resource group: {resource_group or 'all'}")
            
            deployments = []
            for dep_id, deployment in self.active_deployments.items():
                if resource_group is None or deployment['resource_group'] == resource_group:
                    deployments.append(deployment)
            
            result = f"Deployment List:\n\n"
            
            if not deployments:
                result += "No deployments found.\n"
            else:
                for deployment in deployments:
                    result += f"- {deployment['name']} ({deployment['id']})\n"
                    result += f"  Status: {deployment['status']}\n"
                    result += f"  Resource Group: {deployment['resource_group']}\n"
                    result += f"  Progress: {deployment['progress']}%\n"
                    result += f"  Start Time: {deployment['start_time']}\n\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing deployments: {str(e)}")
            return f"Error listing deployments: {str(e)}"
    
    async def rollback_deployment(self, deployment_id: str) -> str:
        """Rollback a deployment to the previous version."""
        try:
            self.logger.info(f"Rolling back deployment: {deployment_id}")
            
            if deployment_id not in self.active_deployments:
                return f"Deployment {deployment_id} not found"
            
            deployment = self.active_deployments[deployment_id]
            
            # Mock rollback process
            deployment['status'] = 'Rolling Back'
            deployment['progress'] = 0
            
            # Simulate rollback progress
            await self._simulate_rollback_progress(deployment_id)
            
            result = f"Deployment Rollback Initiated:\n\n"
            result += f"Deployment ID: {deployment_id}\n"
            result += f"Name: {deployment['name']}\n"
            result += f"Status: {deployment['status']}\n"
            result += f"Rollback will restore the previous stable version.\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error rolling back deployment: {str(e)}")
            return f"Error rolling back deployment: {str(e)}"
    
    async def validate_template(self, template: Dict[str, Any]) -> str:
        """Validate an ARM template or deployment configuration."""
        try:
            self.logger.info("Validating deployment template")
            
            validation_results = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'recommendations': []
            }
            
            # Mock validation logic
            if 'resources' not in template:
                validation_results['is_valid'] = False
                validation_results['errors'].append("Template must contain 'resources' section")
            
            if 'parameters' not in template:
                validation_results['warnings'].append("Template should include parameters for flexibility")
            
            # Check for best practices
            if template.get('$schema'):
                validation_results['recommendations'].append("Using latest ARM template schema")
            else:
                validation_results['warnings'].append("Template should specify schema version")
            
            result = f"Template Validation Report:\n\n"
            result += f"Valid: {'Yes' if validation_results['is_valid'] else 'No'}\n\n"
            
            if validation_results['errors']:
                result += "Errors:\n"
                for error in validation_results['errors']:
                    result += f"- {error}\n"
                result += "\n"
            
            if validation_results['warnings']:
                result += "Warnings:\n"
                for warning in validation_results['warnings']:
                    result += f"- {warning}\n"
                result += "\n"
            
            if validation_results['recommendations']:
                result += "Recommendations:\n"
                for rec in validation_results['recommendations']:
                    result += f"- {rec}\n"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating template: {str(e)}")
            return f"Error validating template: {str(e)}"
    
    async def _simulate_deployment_progress(self, deployment_id: str):
        """Simulate deployment progress (for demo purposes)."""
        deployment = self.active_deployments[deployment_id]
        
        # Simulate deployment taking some time
        for progress in [10, 25, 50, 75, 90, 100]:
            await asyncio.sleep(0.1)  # Small delay for demo
            deployment['progress'] = progress
            
            if progress == 100:
                deployment['status'] = 'Succeeded'
                deployment['end_time'] = datetime.utcnow().isoformat()
    
    async def _simulate_rollback_progress(self, deployment_id: str):
        """Simulate rollback progress (for demo purposes)."""
        deployment = self.active_deployments[deployment_id]
        
        # Simulate rollback taking some time
        for progress in [20, 40, 60, 80, 100]:
            await asyncio.sleep(0.1)  # Small delay for demo
            deployment['progress'] = progress
            
            if progress == 100:
                deployment['status'] = 'Rolled Back'
                deployment['end_time'] = datetime.utcnow().isoformat()


class DeploymentManagerAgent(BaseDevOpsAgent):
    """Agent responsible for managing Azure deployments."""
    
    def __init__(self, subscription_id: str):
        super().__init__("DeploymentManager", "Manages Azure resource deployments and rollbacks")
        self.subscription_id = subscription_id
        self.capabilities = [
            "deployment_creation",
            "deployment_monitoring",
            "rollback_management",
            "template_validation"
        ]
        
    async def _setup_plugins(self):
        """Setup deployment management plugins."""
        self.deployment_plugin = DeploymentManagerPlugin(self.subscription_id)
        self.kernel.add_plugin(
            plugin=self.deployment_plugin,
            plugin_name="deployment_manager",
            description="Deployment management capabilities"
        )
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process deployment management requests."""
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'create_deployment':
                deployment_config = params.get('deployment_config', {})
                result = await self.deployment_plugin.create_deployment(deployment_config)
            elif action == 'get_status':
                deployment_id = params.get('deployment_id', '')
                result = await self.deployment_plugin.get_deployment_status(deployment_id)
            elif action == 'list_deployments':
                resource_group = params.get('resource_group')
                result = await self.deployment_plugin.list_deployments(resource_group)
            elif action == 'rollback':
                deployment_id = params.get('deployment_id', '')
                result = await self.deployment_plugin.rollback_deployment(deployment_id)
            elif action == 'validate_template':
                template = params.get('template', {})
                result = await self.deployment_plugin.validate_template(template)
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