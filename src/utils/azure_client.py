"""Azure client management for DevOps Sentinel multi-agent system."""

# Fix Azure imports FIRST
try:
    import azure
    azure.__path__ = azure.__extend_path__(azure.__path__, azure.__name__)
except:
    pass

import os
import logging
from typing import Dict, Any, Optional
from functools import lru_cache

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.loganalytics import LogAnalyticsManagementClient
import azure.monitor.query
LogsQueryClient = azure.monitor.query.LogsQueryClient
MetricsQueryClient = azure.monitor.query.MetricsQueryClient

logger = logging.getLogger(__name__)


class AzureClientManager:
    """Manages Azure SDK clients with proper authentication."""
    
    def __init__(self, subscription_id: Optional[str] = None):
        self.subscription_id = subscription_id or os.getenv('AZURE_SUBSCRIPTION_ID')
        self._credential = None
        self._clients = {}
        
    @property
    def credential(self):
        """Get or create Azure credential."""
        if self._credential is None:
            # Try ClientSecretCredential first (for service principals)
            client_id = os.getenv('AZURE_CLIENT_ID')
            client_secret = os.getenv('AZURE_CLIENT_SECRET')
            tenant_id = os.getenv('AZURE_TENANT_ID')
            
            if all([client_id, client_secret, tenant_id]):
                logger.info("Using ClientSecretCredential for authentication")
                self._credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
            else:
                # Fall back to DefaultAzureCredential (supports multiple auth methods)
                logger.info("Using DefaultAzureCredential for authentication")
                self._credential = DefaultAzureCredential()
                
        return self._credential
    
    @lru_cache(maxsize=None)
    def get_monitor_client(self) -> MonitorManagementClient:
        """Get Azure Monitor client."""
        if 'monitor' not in self._clients:
            self._clients['monitor'] = MonitorManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._clients['monitor']
    
    @lru_cache(maxsize=None)
    def get_cost_client(self) -> CostManagementClient:
        """Get Cost Management client."""
        if 'cost' not in self._clients:
            self._clients['cost'] = CostManagementClient(
                credential=self.credential
            )
        return self._clients['cost']
    
    @lru_cache(maxsize=None)
    def get_resource_client(self) -> ResourceManagementClient:
        """Get Resource Management client."""
        if 'resource' not in self._clients:
            self._clients['resource'] = ResourceManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._clients['resource']
    
    @lru_cache(maxsize=None)
    def get_compute_client(self) -> ComputeManagementClient:
        """Get Compute Management client."""
        if 'compute' not in self._clients:
            self._clients['compute'] = ComputeManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._clients['compute']
    
    @lru_cache(maxsize=None)
    def get_container_service_client(self) -> ContainerServiceClient:
        """Get Container Service client for AKS."""
        if 'container' not in self._clients:
            self._clients['container'] = ContainerServiceClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._clients['container']
    
    @lru_cache(maxsize=None)
    def get_network_client(self) -> NetworkManagementClient:
        """Get Network Management client."""
        if 'network' not in self._clients:
            self._clients['network'] = NetworkManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._clients['network']
    
    @lru_cache(maxsize=None)
    def get_storage_client(self) -> StorageManagementClient:
        """Get Storage Management client."""
        if 'storage' not in self._clients:
            self._clients['storage'] = StorageManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._clients['storage']
    
    @lru_cache(maxsize=None)
    def get_logs_query_client(self) -> LogsQueryClient:
        """Get Logs Query client for Log Analytics."""
        if 'logs_query' not in self._clients:
            self._clients['logs_query'] = LogsQueryClient(
                credential=self.credential
            )
        return self._clients['logs_query']
    
    @lru_cache(maxsize=None)
    def get_metrics_query_client(self) -> MetricsQueryClient:
        """Get Metrics Query client."""
        if 'metrics_query' not in self._clients:
            self._clients['metrics_query'] = MetricsQueryClient(
                credential=self.credential
            )
        return self._clients['metrics_query']
    
    @lru_cache(maxsize=None)
    def get_log_analytics_client(self) -> LogAnalyticsManagementClient:
        """Get Log Analytics Management client."""
        if 'log_analytics' not in self._clients:
            self._clients['log_analytics'] = LogAnalyticsManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
        return self._clients['log_analytics']
    
    def get_subscription_client(self) -> SubscriptionClient:
        """Get Subscription client."""
        if 'subscription' not in self._clients:
            self._clients['subscription'] = SubscriptionClient(
                credential=self.credential
            )
        return self._clients['subscription']
    
    async def validate_connection(self) -> bool:
        """Validate Azure connection and permissions."""
        try:
            # Try to list resource groups as a connection test
            resource_client = self.get_resource_client()
            resource_groups = list(resource_client.resource_groups.list())
            logger.info(f"Successfully connected to Azure. Found {len(resource_groups)} resource groups.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Azure: {str(e)}")
            return False
    
    def get_all_resource_groups(self) -> list:
        """Get all resource groups in the subscription."""
        try:
            resource_client = self.get_resource_client()
            return [rg.name for rg in resource_client.resource_groups.list()]
        except Exception as e:
            logger.error(f"Error listing resource groups: {str(e)}")
            return []
    
    def get_workspace_id(self, workspace_name: str, resource_group: Optional[str] = None) -> Optional[str]:
        """Get Log Analytics workspace ID."""
        try:
            log_analytics_client = self.get_log_analytics_client()
            
            if resource_group:
                workspace = log_analytics_client.workspaces.get(
                    resource_group_name=resource_group,
                    workspace_name=workspace_name
                )
                return workspace.customer_id
            else:
                # Search all workspaces
                for workspace in log_analytics_client.workspaces.list():
                    if workspace.name == workspace_name:
                        return workspace.customer_id
            
            return None
        except Exception as e:
            logger.error(f"Error getting workspace ID: {str(e)}")
            return None


# Global instance for easy access
_azure_client_manager = None


def get_azure_client_manager(subscription_id: Optional[str] = None) -> AzureClientManager:
    """Get or create the global Azure client manager."""
    global _azure_client_manager
    
    if _azure_client_manager is None:
        _azure_client_manager = AzureClientManager(subscription_id)
    
    return _azure_client_manager