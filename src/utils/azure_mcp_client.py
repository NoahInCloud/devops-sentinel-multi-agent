"""Azure MCP client for DevOps Sentinel multi-agent system."""

import asyncio
import json
import subprocess
import logging
from typing import Any, Dict, List, Optional
import os

logger = logging.getLogger(__name__)

class AzureMCPClient:
    """Client for interacting with Azure services via MCP protocol."""
    
    def __init__(self):
        self.logger = logging.getLogger("azure_mcp_client")
        self.mcp_process = None
        self.is_connected = False
        
    async def start_mcp_server(self) -> bool:
        """Start the Azure MCP server."""
        try:
            # Check if npx is available
            result = subprocess.run(['npx', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error("npx not found. Please install Node.js")
                return False
                
            # Start Azure MCP server
            self.logger.info("Starting Azure MCP server...")
            self.mcp_process = subprocess.Popen([
                'npx', '-y', '@azure/mcp@latest', 'server', 'start'
            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, 
               stderr=subprocess.PIPE, text=True)
            
            self.is_connected = True
            self.logger.info("Azure MCP server started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Azure MCP server: {str(e)}")
            return False
    
    async def stop_mcp_server(self):
        """Stop the Azure MCP server."""
        if self.mcp_process:
            self.mcp_process.terminate()
            self.mcp_process = None
            self.is_connected = False
            self.logger.info("Azure MCP server stopped")
    
    async def send_mcp_request(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the Azure MCP server."""
        if not self.is_connected:
            return {
                'error': 'Azure MCP server not connected',
                'status': 'error'
            }
        
        try:
            # Construct MCP request
            request = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'tools/call',
                'params': {
                    'name': tool_name,
                    'arguments': arguments
                }
            }
            
            # Send request to MCP server
            request_json = json.dumps(request) + '\n'
            self.mcp_process.stdin.write(request_json)
            self.mcp_process.stdin.flush()
            
            # Read response
            response_line = self.mcp_process.stdout.readline()
            if response_line:
                response = json.loads(response_line.strip())
                return response.get('result', {})
            else:
                return {'error': 'No response from MCP server', 'status': 'error'}
                
        except Exception as e:
            self.logger.error(f"Error sending MCP request: {str(e)}")
            return {'error': str(e), 'status': 'error'}
    
    async def list_resource_groups(self) -> Dict[str, Any]:
        """List Azure resource groups via MCP."""
        return await self.send_mcp_request('azure_resource_groups_list', {})
    
    async def get_storage_accounts(self) -> Dict[str, Any]:
        """Get Azure storage accounts via MCP."""
        return await self.send_mcp_request('azure_storage_accounts_list', {})
    
    async def query_log_analytics(self, workspace_name: str, query: str) -> Dict[str, Any]:
        """Query Log Analytics workspace via MCP."""
        return await self.send_mcp_request('azure_monitor_logs_query', {
            'workspace_name': workspace_name,
            'query': query
        })
    
    async def get_cosmos_databases(self) -> Dict[str, Any]:
        """Get Cosmos DB databases via MCP."""
        return await self.send_mcp_request('azure_cosmos_accounts_list', {})
    
    async def execute_azure_cli(self, command: str) -> Dict[str, Any]:
        """Execute Azure CLI command via MCP."""
        return await self.send_mcp_request('azure_cli_execute', {
            'command': command
        })
    
    async def get_azure_health(self, entity_id: str) -> Dict[str, Any]:
        """Get health status of Azure entity via MCP."""
        return await self.send_mcp_request('azure_monitor_health_get', {
            'entity_id': entity_id
        })

# Global instance
azure_mcp_client = AzureMCPClient()
