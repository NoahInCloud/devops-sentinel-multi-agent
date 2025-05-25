#!/usr/bin/env python3
"""
Script to help fetch and identify Azure configuration values.
This script will help you find the Azure credentials and configuration needed for the DevOps Sentinel system.
"""

import os
import subprocess
import json
import sys

def run_command(command):
    """Run a command and return the output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Exception: {str(e)}"

def check_azure_cli():
    """Check if Azure CLI is installed."""
    print("🔍 Checking Azure CLI installation...")
    result = run_command("az --version")
    if "azure-cli" in result:
        print("✅ Azure CLI is installed")
        return True
    else:
        print("❌ Azure CLI is not installed")
        print("Please install Azure CLI from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        return False

def check_azure_login():
    """Check if user is logged into Azure."""
    print("\n🔍 Checking Azure login status...")
    result = run_command("az account show")
    if "error" in result.lower() or "please run 'az login'" in result.lower():
        print("❌ You are not logged into Azure")
        print("Please run: az login")
        return False
    else:
        print("✅ You are logged into Azure")
        return True

def get_azure_account_info():
    """Get current Azure account information."""
    print("\n📊 Fetching Azure account information...")
    
    # Get account details
    account_info = run_command("az account show --output json")
    try:
        account_data = json.loads(account_info)
        print(f"✅ Subscription ID: {account_data.get('id', 'N/A')}")
        print(f"✅ Tenant ID: {account_data.get('tenantId', 'N/A')}")
        print(f"✅ Subscription Name: {account_data.get('name', 'N/A')}")
        return {
            'subscription_id': account_data.get('id'),
            'tenant_id': account_data.get('tenantId'),
            'subscription_name': account_data.get('name')
        }
    except json.JSONDecodeError:
        print("❌ Failed to parse account information")
        return None

def list_resource_groups():
    """List available resource groups."""
    print("\n📦 Fetching available resource groups...")
    result = run_command("az group list --output table")
    print(result)
    
    # Also get JSON format for parsing
    rg_json = run_command("az group list --output json")
    try:
        rg_data = json.loads(rg_json)
        return [rg['name'] for rg in rg_data]
    except json.JSONDecodeError:
        return []

def create_service_principal():
    """Create a service principal for the application."""
    print("\n🔑 Creating service principal...")
    print("This will create a service principal that can be used for authentication.")
    
    # Get current subscription ID
    account_info = run_command("az account show --query id --output tsv")
    if not account_info or "error" in account_info.lower():
        print("❌ Cannot get subscription ID")
        return None
    
    sp_name = "devops-sentinel-sp"
    role = "Contributor"  # You might want to use a more specific role
    
    print(f"Creating service principal '{sp_name}' with '{role}' role...")
    
    # Create service principal
    sp_command = f'az ad sp create-for-rbac --name "{sp_name}" --role "{role}" --scopes "/subscriptions/{account_info}" --output json'
    result = run_command(sp_command)
    
    try:
        sp_data = json.loads(result)
        print("✅ Service principal created successfully!")
        print(f"📋 App ID (Client ID): {sp_data.get('appId')}")
        print(f"🔐 Password (Client Secret): {sp_data.get('password')}")
        print(f"🏢 Tenant: {sp_data.get('tenant')}")
        
        return {
            'client_id': sp_data.get('appId'),
            'client_secret': sp_data.get('password'),
            'tenant_id': sp_data.get('tenant')
        }
    except json.JSONDecodeError:
        print("❌ Failed to create service principal")
        print(f"Raw output: {result}")
        return None

def update_env_file(config_data, resource_groups):
    """Update the .env file with the fetched configuration."""
    env_file_path = ".env"
    
    print(f"\n📝 Updating {env_file_path}...")
    
    # Read current .env file
    try:
        with open(env_file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ .env file not found")
        return
    
    # Update values
    if config_data:
        if 'subscription_id' in config_data and config_data['subscription_id']:
            content = content.replace('AZURE_SUBSCRIPTION_ID=3362d230-8cec-4912-822d-8383b4afe306', 
                                    f'AZURE_SUBSCRIPTION_ID={config_data["subscription_id"]}')
        
        if 'client_id' in config_data and config_data['client_id']:
            content = content.replace('AZURE_CLIENT_ID=your_azure_client_id', 
                                    f'AZURE_CLIENT_ID={config_data["client_id"]}')
        
        if 'client_secret' in config_data and config_data['client_secret']:
            content = content.replace('AZURE_CLIENT_SECRET=your_azure_client_secret', 
                                    f'AZURE_CLIENT_SECRET={config_data["client_secret"]}')
        
        if 'tenant_id' in config_data and config_data['tenant_id']:
            content = content.replace('AZURE_TENANT_ID=your_azure_tenant_id', 
                                    f'AZURE_TENANT_ID={config_data["tenant_id"]}')
    
    # Update resource group if we have any
    if resource_groups:
        print(f"\n📦 Available resource groups: {', '.join(resource_groups)}")
        print("💡 Consider using one of these for AZURE_RESOURCE_GROUP")
        # For now, let's use the first one as a suggestion
        if resource_groups:
            content = content.replace('AZURE_RESOURCE_GROUP=your_resource_group', 
                                    f'AZURE_RESOURCE_GROUP={resource_groups[0]}')
    
    # Write back to file
    try:
        with open(env_file_path, 'w') as f:
            f.write(content)
        print("✅ .env file updated successfully!")
    except Exception as e:
        print(f"❌ Failed to update .env file: {e}")

def main():
    """Main function to fetch Azure configuration."""
    print("🚀 Azure Configuration Fetcher for DevOps Sentinel")
    print("=" * 55)
    
    # Check prerequisites
    if not check_azure_cli():
        return
    
    if not check_azure_login():
        print("\n💡 Please run 'az login' first, then run this script again.")
        return
    
    # Get account information
    account_info = get_azure_account_info()
    
    # List resource groups
    resource_groups = list_resource_groups()
    
    # Ask if user wants to create a service principal
    print("\n🤔 Do you want to create a service principal for authentication?")
    print("This is recommended for production use. (y/n): ", end="")
    
    try:
        choice = input().lower().strip()
        if choice in ['y', 'yes']:
            sp_info = create_service_principal()
            if sp_info and account_info:
                # Combine account info and service principal info
                config_data = {**account_info, **sp_info}
                update_env_file(config_data, resource_groups)
            else:
                print("❌ Failed to create service principal")
        else:
            print("💡 You can manually set up service principal later.")
            if account_info:
                update_env_file(account_info, resource_groups)
    except KeyboardInterrupt:
        print("\n\n👋 Script cancelled by user")
        return
    
    print("\n✅ Configuration fetch completed!")
    print("\n📋 Summary of what you need to do:")
    print("1. Review the updated .env file")
    print("2. If you didn't create a service principal, set up authentication manually")
    print("3. Choose an appropriate resource group for your application")
    print("4. Test the configuration by running the DevOps Sentinel system")

if __name__ == "__main__":
    main()
