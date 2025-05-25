"""Main entry point for DevOps Sentinel Multi-Agent System."""

import asyncio
import logging
import os
from pathlib import Path

from utils.config import get_config_manager
from utils.logging import setup_logging
from core.orchestrator import DevOpsOrchestrator
from interfaces.chat_interface import ChatInterface
from interfaces.audio_handler import AudioHandler
from communication.websocket_handler import WebSocketHandler


async def initialize_system():
    """Initialize the DevOps Sentinel system."""
    # Setup logging
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_dir = os.getenv('LOG_DIR', 'logs')
    setup_logging(
        log_level=log_level,
        log_dir=log_dir,
        enable_structured_logging=os.getenv('STRUCTURED_LOGGING', 'false').lower() == 'true'
    )
    
    logger = logging.getLogger("main")
    logger.info("Starting DevOps Sentinel Multi-Agent System...")
    
    # Load configuration
    config_manager = get_config_manager()
    
    # Create orchestrator configuration
    orchestrator_config = {
        'azure': config_manager.get_azure_config(),
        'kubernetes': config_manager.get_kubernetes_config(),
        'agents': config_manager.get_config('agents')
    }
    
    # Validate Azure configuration
    if not orchestrator_config['azure'].get('subscription_id'):
        logger.warning("No Azure subscription ID configured. Some features may be limited.")
    
    # Initialize orchestrator
    orchestrator = DevOpsOrchestrator(orchestrator_config)
    await orchestrator.initialize()
    
    # Initialize interfaces
    interface_config = {
        'host': os.getenv('HOST', '0.0.0.0'),
        'port': int(os.getenv('PORT', '8080')),
        'audio_format': 'pcm16',
        'sample_rate': 16000,
        'azure_openai_endpoint': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'azure_openai_key': os.getenv('AZURE_OPENAI_API_KEY')
    }
    
    # Create chat interface
    chat_interface = ChatInterface(interface_config)
    await chat_interface.initialize(orchestrator)
    
    # Create audio handler
    audio_handler = AudioHandler(interface_config)
    
    # Create WebSocket handler
    websocket_handler = WebSocketHandler()
    
    logger.info("System initialization complete")
    
    return orchestrator, chat_interface, audio_handler, websocket_handler


async def run_system():
    """Run the DevOps Sentinel system."""
    logger = logging.getLogger("main")
    
    try:
        # Initialize system
        orchestrator, chat_interface, audio_handler, websocket_handler = await initialize_system()
        
        # Start WebSocket server
        ws_host = os.getenv('WEBSOCKET_HOST', 'localhost')
        ws_port = int(os.getenv('WEBSOCKET_PORT', '8765'))
        
        ws_server_task = asyncio.create_task(
            websocket_handler.start_server(ws_host, ws_port)
        )
        
        logger.info(f"WebSocket server started on {ws_host}:{ws_port}")
        
        # Run chat interface (this will block)
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', '8080'))
        
        logger.info(f"Starting web interface on http://{host}:{port}")
        
        # Run the chat interface
        await chat_interface.app.run_task(
            host=host,
            port=port,
            debug=os.getenv('DEBUG', 'false').lower() == 'true'
        )
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"System error: {str(e)}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Shutting down system...")
        
        if 'orchestrator' in locals():
            await orchestrator.shutdown()
        
        if 'websocket_handler' in locals():
            await websocket_handler.stop_server()
        
        logger.info("System shutdown complete")


def main():
    """Main entry point."""
    # Check Python version
    import sys
    if sys.version_info < (3, 8):
        print("Python 3.8 or higher is required")
        sys.exit(1)
    
    # Check for required environment variables
    required_env_vars = []  # Made optional since we have fallbacks
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set up your .env file based on .env.example")
        sys.exit(1)
    
    # Load .env file if it exists
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment from {env_path}")
    
    # Run the async main function
    try:
        asyncio.run(run_system())
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()