#!/usr/bin/env python3
"""
Setup script for DevOps Sentinel Multi-Agent System
This script helps with initial configuration and validation.
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional

def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def check_python_version():
    """Check if Python version meets requirements."""
    print("Checking Python version...")
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8 or higher is required. You have {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]} is supported")
    return True

def check_azure_cli():
    """Check if Azure CLI is installed."""
    print("\nChecking Azure CLI...")
    try:
        result = subprocess.run(['az', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Azure CLI is installed")
            # Check if logged in
            result = subprocess.run(['az', 'account', 'show'], capture_output=True, text=True)
            if result.returncode == 0:
                account = json.loads(result.stdout)
                print(f"✅ Logged in to Azure (Subscription: {account['name']})")
                return True
            else:
                print("⚠️  Not logged in to Azure. Run: az login")
                return False
        else:
            print("❌ Azure CLI is not installed")
            return False
    except FileNotFoundError:
        print("❌ Azure CLI is not installed. Install from: https://aka.ms/installazurecli")
        return False

def check_kubectl():
    """Check if kubectl is installed."""
    print("\nChecking kubectl...")
    try:
        result = subprocess.run(['kubectl', 'version', '--client'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ kubectl is installed")
            return True
        else:
            print("⚠️  kubectl not found")
            return False
    except FileNotFoundError:
        print("⚠️  kubectl is not installed. Install for Kubernetes support")
        return False

def create_env_file():
    """Create .env file from template."""
    print("\nSetting up environment configuration...")
    
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if env_file.exists():
        print("⚠️  .env file already exists")
        response = input("Do you want to overwrite it? (y/N): ")
        if response.lower() != 'y':
            return False
    
    if not env_example.exists():
        print("❌ .env.example not found")
        return False
    
    # Copy the template
    env_content = env_example.read_text()
    
    # Get Azure subscription ID
    try:
        result = subprocess.run(['az', 'account', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            account = json.loads(result.stdout)
            subscription_id = account['id']
            tenant_id = account['tenantId']
            
            env_content = env_content.replace('your_azure_subscription_id', subscription_id)
            env_content = env_content.replace('your_azure_tenant_id', tenant_id)
            print(f"✅ Using Azure subscription: {account['name']}")
    except:
        pass
    
    # Get Azure OpenAI configuration
    print("\nAzure OpenAI Configuration:")
    print("Leave blank to skip (you can configure later)")
    
    openai_endpoint = input("Azure OpenAI Endpoint (e.g., https://your-resource.openai.azure.com/): ").strip()
    if openai_endpoint:
        env_content = env_content.replace('https://your-openai-resource.openai.azure.com/', openai_endpoint)
        
        openai_key = input("Azure OpenAI API Key: ").strip()
        if openai_key:
            env_content = env_content.replace('your_openai_api_key', openai_key)
        
        deployment_name = input("Deployment Name (default: gpt-35-turbo): ").strip() or 'gpt-35-turbo'
        env_content = env_content.replace('your_deployment_name', deployment_name)
    
    # Write the file
    env_file.write_text(env_content)
    print("\n✅ Created .env file")
    return True

def install_requirements():
    """Install Python requirements."""
    print("\nInstalling Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def create_directories():
    """Create required directories."""
    print("\nCreating required directories...")
    directories = ['logs', 'templates', 'data']
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Created {dir_name}/ directory")
    
    return True

def validate_azure_resources():
    """Validate Azure resources and permissions."""
    print("\nValidating Azure resources...")
    
    try:
        # Check resource groups
        result = subprocess.run(['az', 'group', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            groups = json.loads(result.stdout)
            print(f"✅ Found {len(groups)} resource groups")
        
        # Check for required providers
        providers = ['Microsoft.Compute', 'Microsoft.Network', 'Microsoft.Storage', 
                    'Microsoft.ContainerService', 'Microsoft.Monitor']
        
        for provider in providers:
            result = subprocess.run(['az', 'provider', 'show', '-n', provider], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                provider_info = json.loads(result.stdout)
                if provider_info['registrationState'] == 'Registered':
                    print(f"✅ {provider} is registered")
                else:
                    print(f"⚠️  {provider} is not registered. Registering...")
                    subprocess.run(['az', 'provider', 'register', '-n', provider])
        
        return True
    except Exception as e:
        print(f"⚠️  Could not validate Azure resources: {str(e)}")
        return False

def create_service_principal():
    """Create Azure service principal for the application."""
    print("\nService Principal Setup:")
    response = input("Do you want to create a service principal for DevOps Sentinel? (y/N): ")
    
    if response.lower() != 'y':
        return False
    
    try:
        name = "DevOps-Sentinel-SP"
        result = subprocess.run(['az', 'ad', 'sp', 'create-for-rbac', 
                               '--name', name,
                               '--role', 'Contributor'],
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            sp_info = json.loads(result.stdout)
            print("\n✅ Service Principal created successfully!")
            print("\nAdd these values to your .env file:")
            print(f"AZURE_CLIENT_ID={sp_info['appId']}")
            print(f"AZURE_CLIENT_SECRET={sp_info['password']}")
            print(f"AZURE_TENANT_ID={sp_info['tenant']}")
            print("\n⚠️  Save the client secret securely - it won't be shown again!")
            return True
        else:
            print("❌ Failed to create service principal")
            return False
    except Exception as e:
        print(f"❌ Error creating service principal: {str(e)}")
        return False

def test_system():
    """Run a basic system test."""
    print("\nRunning system test...")
    
    try:
        # Test imports
        print("Testing imports...")
        import semantic_kernel
        import azure.identity
        import azure.mgmt.resource
        print("✅ Core imports successful")
        
        # Test Azure connection
        from utils.azure_clients import get_azure_client_manager
        print("\nTesting Azure connection...")
        
        # This will use the .env file
        from dotenv import load_dotenv
        load_dotenv()
        
        manager = get_azure_client_manager()
        
        # Just try to create the credential
        cred = manager.credential
        print("✅ Azure authentication configured")
        
        return True
    except Exception as e:
        print(f"❌ System test failed: {str(e)}")
        return False

def main():
    """Main setup flow."""
    print_header("DevOps Sentinel Multi-Agent System Setup")
    
    # Check prerequisites
    if not check_python_version():
        sys.exit(1)
    
    azure_cli_ok = check_azure_cli()
    kubectl_ok = check_kubectl()
    
    if not azure_cli_ok:
        print("\n⚠️  Azure CLI is required for full functionality")
        print("Install from: https://aka.ms/installazurecli")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Setup environment
    if create_env_file():
        print("\n✅ Environment configuration created")
    
    # Install dependencies
    if install_requirements():
        print("\n✅ Dependencies installed")
    
    # Azure setup
    if azure_cli_ok:
        validate_azure_resources()
        create_service_principal()
    
    # Run tests
    print_header("System Validation")
    if test_system():
        print("\n✅ System validation passed!")
    else:
        print("\n⚠️  System validation had issues - check configuration")
    
    # Final instructions
    print_header("Setup Complete!")
    
    print("Next steps:")
    print("1. Review and update .env file with your configuration")
    print("2. Configure Azure OpenAI in the Azure Portal")
    print("3. Set up Log Analytics workspace for monitoring")
    print("4. Configure AKS cluster (if using Kubernetes features)")
    print("\nTo start the system:")
    print("  python run.py")
    print("\nOr using the main module:")
    print("  python -m src.main")
    print("\nVisit http://localhost:8080 to access the web interface")
    
    print("\n📚 Documentation: See README.md for detailed instructions")
    print("💡 Quick test: Ask 'Show me infrastructure health' in the chat")

if __name__ == "__main__":
    main()