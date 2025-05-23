"""Configuration management for DevOps Sentinel multi-agent system."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ConfigManager:
    """Configuration manager for the DevOps Sentinel system."""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            # Get the config directory relative to this file
            current_dir = Path(__file__).parent.parent.parent
            self.config_dir = current_dir / "config"
        else:
            self.config_dir = Path(config_dir)
        
        self._configs = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files."""
        config_files = {
            'agents': 'agents.yaml',
            'azure': 'azure.yaml', 
            'kubernetes': 'kubernetes.yaml'
        }
        
        for config_name, filename in config_files.items():
            config_path = self.config_dir / filename
            if config_path.exists():
                with open(config_path, 'r') as file:
                    self._configs[config_name] = yaml.safe_load(file)
            else:
                self._configs[config_name] = {}
    
    def get_config(self, config_name: str) -> Dict[str, Any]:
        """Get a complete configuration section."""
        return self._configs.get(config_name, {})
    
    def get(self, config_name: str, key: str, default: Any = None) -> Any:
        """Get a specific configuration value."""
        config = self._configs.get(config_name, {})
        return config.get(key, default)
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """Get environment variable with fallback."""
        return os.getenv(key, default)
    
    def get_azure_config(self) -> Dict[str, Any]:
        """Get Azure-specific configuration."""
        azure_config = self.get_config('azure')
        
        # Override with environment variables if they exist
        env_overrides = {
            'subscription_id': self.get_env('AZURE_SUBSCRIPTION_ID'),
            'tenant_id': self.get_env('AZURE_TENANT_ID'),
            'client_id': self.get_env('AZURE_CLIENT_ID'),
            'client_secret': self.get_env('AZURE_CLIENT_SECRET'),
            'openai_endpoint': self.get_env('AZURE_OPENAI_ENDPOINT'),
            'openai_api_key': self.get_env('AZURE_OPENAI_API_KEY'),
            'deployment_name': self.get_env('AZURE_OPENAI_DEPLOYMENT_NAME')
        }
        
        for key, value in env_overrides.items():
            if value:
                azure_config[key] = value
        
        return azure_config
    
    def get_kubernetes_config(self) -> Dict[str, Any]:
        """Get Kubernetes-specific configuration."""
        k8s_config = self.get_config('kubernetes')
        
        # Override with environment variables if they exist
        env_overrides = {
            'kubeconfig_path': self.get_env('KUBECONFIG'),
            'kagent_repo_url': self.get_env('KAGENT_REPO_URL', 'https://github.com/NoahInCloud/kagent'),
            'kagent_branch': self.get_env('KAGENT_BRANCH', 'main')
        }
        
        for key, value in env_overrides.items():
            if value:
                k8s_config[key] = value
        
        return k8s_config

# Global configuration instance
_config_manager = None

def load_config() -> Dict[str, Any]:
    """Load and return configuration for all components."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return {
        'infrastructure': _config_manager.get_config('agents'),
        'rca': _config_manager.get_config('agents'),
        'cost': _config_manager.get_config('agents'),
        'report': _config_manager.get_config('agents'),
        'deployment': _config_manager.get_config('agents'),
        'kubernetes': _config_manager.get_kubernetes_config(),
        'azure': _config_manager.get_azure_config()
    }

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager