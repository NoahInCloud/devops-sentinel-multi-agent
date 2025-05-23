from agents.infrastructure_monitor import InfrastructureMonitorAgent
from agents.rca_analyzer import RCAAnalyzerAgent
from agents.cost_optimizer import CostOptimizerAgent
from agents.report_generator import ReportGeneratorAgent
from agents.deployment_manager import DeploymentManagerAgent
from agents.kubernetes_agent import KubernetesAgent
from communication.websocket_handler import WebSocketHandler
from interfaces.chat_interface import ChatInterface
from interfaces.audio_handler import AudioHandler
from core.orchestrator import DevOpsOrchestrator
from utils.config import ConfigManager

def main():
    # Initialize configuration manager
    config_manager = ConfigManager()
    
    # Get configuration sections
    agents_config = config_manager.get_config('agents')
    azure_config = config_manager.get_config('azure')
    k8s_config = config_manager.get_config('kubernetes')
    
    # Get subscription ID from environment or config
    subscription_id = config_manager.get_env('AZURE_SUBSCRIPTION_ID') or azure_config.get('subscription_id', '')
    
    # Initialize agents with proper configuration
    infrastructure_monitor = InfrastructureMonitorAgent(subscription_id)
    rca_analyzer = RCAAnalyzerAgent()
    cost_optimizer = CostOptimizerAgent(subscription_id)
    report_generator = ReportGeneratorAgent()
    deployment_manager = DeploymentManagerAgent(subscription_id)
    kubernetes_agent = KubernetesAgent(k8s_config)

    # Initialize communication handlers
    websocket_handler = WebSocketHandler()
    
    # Interface configuration
    interface_config = {
        'host': config_manager.get_env('CHAT_HOST', '0.0.0.0'),
        'port': int(config_manager.get_env('CHAT_PORT', 8080)),
        'audio_format': 'pcm16',
        'sample_rate': 16000
    }
    
    chat_interface = ChatInterface(interface_config)
    audio_handler = AudioHandler(interface_config)

    # Create orchestrator configuration
    orchestrator_config = {
        'agents': {
            'infrastructure_monitor': infrastructure_monitor,
            'rca_analyzer': rca_analyzer,
            'cost_optimizer': cost_optimizer,
            'report_generator': report_generator,
            'deployment_manager': deployment_manager,
            'kubernetes_agent': kubernetes_agent
        },
        'communication': {
            'websocket_handler': websocket_handler,
            'chat_interface': chat_interface,
            'audio_handler': audio_handler
        },
        'azure': azure_config,
        'kubernetes': k8s_config
    }

    # Initialize orchestrator
    orchestrator = DevOpsOrchestrator(orchestrator_config)

    # Start the orchestrator
    import asyncio
    asyncio.run(orchestrator.initialize())

if __name__ == "__main__":
    main()