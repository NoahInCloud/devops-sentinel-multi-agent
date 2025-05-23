"""Base agent class for DevOps Sentinel multi-agent system."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import uuid4

try:
    from semantic_kernel import Kernel
    from semantic_kernel.functions.kernel_function_decorator import kernel_function
    SEMANTIC_KERNEL_AVAILABLE = True
except ImportError:
    # Fallback if semantic kernel is not available
    SEMANTIC_KERNEL_AVAILABLE = False
    def kernel_function(func):
        return func


class BaseDevOpsAgent(ABC):
    """Base class for all DevOps agents."""
    
    def __init__(self, name: str, description: str):
        self.agent_id = str(uuid4())
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"agent.{name}")
        self.kernel = Kernel()
        self.is_active = False
        self.capabilities: List[str] = []
        
    async def initialize(self):
        """Initialize the agent."""
        self.logger.info(f"Initializing agent: {self.name}")
        await self._setup_plugins()
        self.is_active = True
        
    @abstractmethod
    async def _setup_plugins(self):
        """Setup agent-specific plugins."""
        pass
        
    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming request."""
        pass
        
    @kernel_function
    async def get_agent_status(self) -> str:
        """Get the current status of the agent."""
        return f"Agent {self.name} is {'active' if self.is_active else 'inactive'}"
        
    @kernel_function 
    async def get_capabilities(self) -> str:
        """Get the capabilities of this agent."""
        return f"Agent {self.name} capabilities: {', '.join(self.capabilities)}"
        
    async def shutdown(self):
        """Shutdown the agent gracefully."""
        self.logger.info(f"Shutting down agent: {self.name}")
        self.is_active = False


class DevOpsAgentPlugin:
    """Base plugin class for DevOps agents."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"plugin.{agent_name}")
        
    @kernel_function
    async def log_action(self, action: str, details: str = "") -> str:
        """Log an action performed by the agent."""
        self.logger.info(f"Action performed: {action} - {details}")
        return f"Logged action: {action}"