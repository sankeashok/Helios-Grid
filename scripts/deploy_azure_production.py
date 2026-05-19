#!/usr/bin/env python3
"""
🚀 Helios-Grid - Azure Production Deployment
Deploy Docker containers to Azure for public access
"""

import os
import json
import subprocess
from datetime import datetime

class AzureDeployment:
    def __init__(self):
        self.resource_group = "helios-grid-rg"
        self.location = "eastus"
        self.container_name = "helios-grid-api"
        self.image_name = "sankeashok/helios-grid"
        self.dns_label = "helios-grid-energy-api"
        
    def deploy_to_azure(self):
        """Deploy Docker container to Azure Container Instances"""
        
        print("🚀 HELIOS-GRID AZURE PRODUCTION DEPLOYMENT")
        print("=" * 50)
        
        # Step 1: Create Resource Group
        print("📦 Creating Azure Resource Group...")
        rg_cmd = f"""
        az group create \
            --name {self.resource_group} \
            --location {self.location}
        """
        self.run_command(rg_cmd, "Resource Group Creation")
        
        # Step 2: Deploy Container Instance
        print("🐳 Deploying Docker Container to Azure...")
        deploy_cmd = f"""
        az container create \
            --resource-group {self.resource_group} \
            --name {self.container_name} \
            --image {self.image_name}:latest \
            --dns-name-label {self.dns_label} \
            --ports 8000 \
            --cpu 2 \
            --memory 4 \
            --restart-policy Always \
            --environment-variables \
                ENVIRONMENT=production \
                API_VERSION=v1.0 \
                DEPLOYMENT_TIME="{datetime.now().isoformat()}"
        """
        self.run_command(deploy_cmd, "Container Deployment")
        
        # Step 3: Get Public URL
        print("🌐 Getting Public URL...")
        url_cmd = f"""
        az container show \
            --resource-group {self.resource_group} \
            --name {self.container_name} \
            --query ipAddress.fqdn \
            --output tsv
        """
        
        result = subprocess.run(url_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            public_url = result.stdout.strip()
            print(f"✅ PUBLIC API URL: http://{public_url}:8000")
            print(f"✅ API DOCS: http://{public_url}:8000/docs")
            print(f"✅ HEALTH CHECK: http://{public_url}:8000/health")
            
            # Save deployment info
            deployment_info = {
                "deployment_time": datetime.now().isoformat(),
                "public_url": f"http://{public_url}:8000",
                "api_docs": f"http://{public_url}:8000/docs",
                "health_check": f"http://{public_url}:8000/health",
                "resource_group": self.resource_group,
                "container_name": self.container_name
            }
            
            with open("azure_deployment_info.json", "w") as f:
                json.dump(deployment_info, f, indent=2)
                
            print("📄 Deployment info saved to: azure_deployment_info.json")
            
        else:
            print("❌ Failed to get public URL")
            
    def run_command(self, command, description):
        """Execute Azure CLI command"""
        print(f"🔄 {description}...")
        
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            print(f"✅ {description} completed")
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} failed: {e.stderr}")
            raise

def main():
    """Deploy Helios-Grid to Azure"""
    
    # Check Azure CLI
    try:
        subprocess.run("az --version", shell=True, check=True, capture_output=True)
        print("✅ Azure CLI detected")
    except subprocess.CalledProcessError:
        print("❌ Azure CLI not found. Please install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        return
    
    # Check login status
    try:
        subprocess.run("az account show", shell=True, check=True, capture_output=True)
        print("✅ Azure login verified")
    except subprocess.CalledProcessError:
        print("❌ Please login to Azure: az login")
        return
    
    # Deploy
    deployer = AzureDeployment()
    deployer.deploy_to_azure()
    
    print("\n🎉 DEPLOYMENT COMPLETE!")
    print("🌐 Your Helios-Grid API is now live and accessible worldwide!")
    print("📊 Ready for public energy consumption predictions!")

if __name__ == "__main__":
    main()