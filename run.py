#!/usr/bin/env python3
"""
DevOps Sentinel Multi-Agent System Launcher
"""

import os
import sys
import logging
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

try:
    from main import main
    
    if __name__ == "__main__":
        # Setup basic logging for startup
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        logger = logging.getLogger("launcher")
        
        # Check for required environment variables
        required_env_vars = [
            'AZURE_SUBSCRIPTION_ID',
            'AZURE_CLIENT_ID', 
            'AZURE_CLIENT_SECRET',
            'AZURE_TENANT_ID'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
            logger.info("Please set up your .env file based on .env.example")
            logger.info("The system will start with default/mock configurations")
        
        try:
            logger.info("Starting DevOps Sentinel Multi-Agent System...")
            main()
        except KeyboardInterrupt:
            logger.info("System shutdown requested by user")
        except Exception as e:
            logger.error(f"Error starting system: {str(e)}")
            sys.exit(1)
            
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required packages are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)
