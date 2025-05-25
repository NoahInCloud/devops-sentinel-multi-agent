"""Base agent class for DevOps Sentinel multi-agent system with Semantic Kernel integration."""

import asyncio
import logging
import os
import yaml
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pathlib import Path

from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.function_call_behavior import FunctionCallBehavior
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings,
)
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_arguments import KernelArguments

from utils.config import get_config_manager


class BaseDevOpsAgent(ABC):
    """Base class for all DevOps agents with Semantic Kernel integration."""
    
    def __init__(self, name: str, description: str, agent_type: str):
        self.agent_id = str(uuid4())
        self.name = name
        self.description = description
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"agent.{name}")
        self.kernel = None
        self.is_active = False
        self.capabilities: List[str] = []
        self.chat_history = ChatHistory()
        self.model_config = {}
        
    async def initialize(self):
        """Initialize the agent with Semantic Kernel and model configuration."""
        self.logger.info(f"Initializing agent: {self.name}")
        
        # Load model configuration
        self._load_model_config()
        
        # Initialize Semantic Kernel
        await self._initialize_kernel()
        
        # Setup agent-specific plugins
        await self._setup_plugins()
        
        self.is_active = True
        self.logger.info(f"Agent {self.name} initialized with model: {self.model_config.get('model', 'default')}")
        
    def _load_model_config(self):
        """Load model configuration for this agent type."""
        try:
            # Load models.yaml
            config_path = Path(__file__).parent.parent.parent / "config" / "models.yaml"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    models_config = yaml.safe_load(f)
                    
                # Get agent-specific config
                agent_config = models_config.get('agents', {}).get(self.agent_type, {})
                defaults = models_config.get('defaults', {})
                
                # Merge with defaults
                self.model_config = {**defaults, **agent_config}
            else:
                # Fallback configuration
                self.model_config = {
                    'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo'),
                    'model': 'gpt-3.5-turbo',
                    'temperature': 0.5,
                    'max_tokens': 2000,
                    'api_version': '2024-02-01'
                }
                
        except Exception as e:
            self.logger.error(f"Error loading model config: {str(e)}")
            # Use fallback configuration
            self.model_config = {
                'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo'),
                'model': 'gpt-3.5-turbo',
                'temperature': 0.5,
                'max_tokens': 2000,
                'api_version': '2024-02-01'
            }
    
    async def _initialize_kernel(self):
        """Initialize Semantic Kernel with Azure OpenAI."""
        try:
            self.kernel = Kernel()
            
            # Get Azure OpenAI configuration
            endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
            api_key = os.getenv('AZURE_OPENAI_API_KEY')
            
            if not endpoint or not api_key:
                self.logger.warning("Azure OpenAI credentials not found. Agent will operate in limited mode.")
                return
            
            # Create Azure OpenAI chat service with agent-specific model
            service_id = f"{self.agent_type}_chat"
            chat_service = AzureChatCompletion(
                service_id=service_id,
                deployment_name=self.model_config['deployment_name'],
                endpoint=endpoint,
                api_key=api_key,
                api_version=self.model_config.get('api_version', '2024-02-01')
            )
            
            # Add service to kernel
            self.kernel.add_service(chat_service)
            
            # Set up execution settings
            self.execution_settings = AzureChatPromptExecutionSettings(
                service_id=service_id,
                temperature=self.model_config.get('temperature', 0.5),
                max_tokens=self.model_config.get('max_tokens', 2000),
                top_p=self.model_config.get('top_p', 0.95),
                frequency_penalty=self.model_config.get('frequency_penalty', 0),
                presence_penalty=self.model_config.get('presence_penalty', 0),
                function_call_behavior=FunctionCallBehavior.AutoInvokeKernelFunctions()
            )
            
            self.logger.info(f"Semantic Kernel initialized with Azure OpenAI service: {service_id}")
            
        except Exception as e:
            self.logger.error(f"Error initializing Semantic Kernel: {str(e)}")
            # Create a basic kernel without AI service
            self.kernel = Kernel()
        
    @abstractmethod
    async def _setup_plugins(self):
        """Setup agent-specific plugins."""
        pass
        
    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming request."""
        pass
    
    async def invoke_semantic_function(self, prompt: str, **kwargs) -> str:
        """Invoke a semantic function with the configured model."""
        try:
            if not self.kernel or not hasattr(self, 'execution_settings'):
                self.logger.warning("Kernel not properly initialized, returning prompt analysis")
                return f"[Limited Mode] Analysis of: {prompt}"
            
            # Create kernel arguments
            arguments = KernelArguments(settings=self.execution_settings, **kwargs)
            
            # Add to chat history
            self.chat_history.add_user_message(prompt)
            
            # Invoke the kernel
            response = await self.kernel.invoke_prompt(
                prompt_template=prompt,
                arguments=arguments
            )
            
            # Add response to chat history
            result = str(response)
            self.chat_history.add_assistant_message(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error invoking semantic function: {str(e)}")
            return f"Error processing request: {str(e)}"
    
    @kernel_function(name="get_agent_status", description="Get the current status of the agent")
    async def get_agent_status(self) -> str:
        """Get the current status of the agent."""
        status_info = {
            'agent_id': self.agent_id,
            'name': self.name,
            'type': self.agent_type,
            'active': self.is_active,
            'model': self.model_config.get('model', 'unknown'),
            'deployment': self.model_config.get('deployment_name', 'unknown'),
            'capabilities': self.capabilities
        }
        return f"Agent Status: {status_info}"
        
    @kernel_function(name="get_capabilities", description="Get the capabilities of this agent")
    async def get_capabilities(self) -> str:
        """Get the capabilities of this agent."""
        return f"Agent {self.name} capabilities: {', '.join(self.capabilities)}"
    
    @kernel_function(name="analyze_with_ai", description="Analyze data using the agent's AI model")
    async def analyze_with_ai(self, data: str, analysis_type: str = "general") -> str:
        """Analyze data using the agent's configured AI model."""
        prompt = f"""
        As the {self.name} agent specializing in {self.description}, 
        please analyze the following data:
        
        Analysis Type: {analysis_type}
        Data: {data}
        
        Provide a detailed analysis with actionable insights.
        """
        
        return await self.invoke_semantic_function(prompt)
        
    async def shutdown(self):
        """Shutdown the agent gracefully."""
        self.logger.info(f"Shutting down agent: {self.name}")
        self.is_active = False
        
        # Clear chat history
        self.chat_history = ChatHistory()
        
    async def handle_a2a_message(self, message: Any):
        """Handle agent-to-agent messages."""
        self.logger.info(f"Received A2A message: {message.content}")
        
        # Process based on message type
        if message.message_type.value == "request":
            response = await self.process_request(message.content)
            return response
        else:
            self.logger.info(f"Received {message.message_type.value} message")


class DevOpsAgentPlugin:
    """Base plugin class for DevOps agents."""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"plugin.{agent_name}")
        
    @kernel_function(name="log_action", description="Log an action performed by the agent")
    async def log_action(self, action: str, details: str = "") -> str:
        """Log an action performed by the agent."""
        self.logger.info(f"Action performed: {action} - {details}")
        return f"Logged action: {action}"