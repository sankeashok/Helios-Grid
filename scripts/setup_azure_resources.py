"""
Azure Resource Setup Script
Automates the creation of Azure resources for MLOps pipeline
"""

import json
import logging
import os
from typing import Any
from typing import Dict

import click
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.machinelearningservices import MachineLearningServicesMgmtClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AzureResourceManager:
    """Manages Azure resource creation and configuration"""

    def __init__(self, subscription_id: str, resource_group: str, location: str):
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.location = location
        self.credential = DefaultAzureCredential()

        # Initialize clients
        self.resource_client = ResourceManagementClient(
            self.credential, subscription_id
        )
        self.storage_client = StorageManagementClient(self.credential, subscription_id)
        self.keyvault_client = KeyVaultManagementClient(
            self.credential, subscription_id
        )
        self.ml_client = MachineLearningServicesMgmtClient(
            self.credential, subscription_id
        )

    def create_resource_group(self) -> bool:
        """Create resource group if it doesn't exist"""
        try:
            logger.info(f"Creating resource group: {self.resource_group}")

            rg_result = self.resource_client.resource_groups.create_or_update(
                self.resource_group,
                {
                    "location": self.location,
                    "tags": {"project": "mlops-pipeline", "environment": "production"},
                },
            )

            logger.info(f"Resource group created: {rg_result.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create resource group: {e}")
            return False

    def create_storage_account(self, storage_account_name: str) -> Dict[str, str]:
        """Create Azure Storage Account"""
        try:
            logger.info(f"Creating storage account: {storage_account_name}")

            # Check availability
            availability = self.storage_client.storage_accounts.check_name_availability(
                {"name": storage_account_name}
            )

            if not availability.name_available:
                logger.error(
                    f"Storage account name not available: {availability.reason}"
                )
                return {}

            # Create storage account
            poller = self.storage_client.storage_accounts.begin_create(
                self.resource_group,
                storage_account_name,
                {
                    "sku": {"name": "Standard_LRS"},
                    "kind": "StorageV2",
                    "location": self.location,
                    "access_tier": "Hot",
                    "tags": {"project": "mlops-pipeline", "purpose": "data-storage"},
                },
            )

            storage_account = poller.result()

            # Get connection string
            keys = self.storage_client.storage_accounts.list_keys(
                self.resource_group, storage_account_name
            )

            connection_string = (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={storage_account_name};"
                f"AccountKey={keys.keys[0].value};"
                f"EndpointSuffix=core.windows.net"
            )

            logger.info(f"Storage account created: {storage_account.name}")

            return {
                "account_name": storage_account_name,
                "connection_string": connection_string,
                "primary_key": keys.keys[0].value,
            }

        except Exception as e:
            logger.error(f"Failed to create storage account: {e}")
            return {}

    def create_key_vault(self, keyvault_name: str) -> Dict[str, str]:
        """Create Azure Key Vault"""
        try:
            logger.info(f"Creating Key Vault: {keyvault_name}")

            # Get current user object ID (needed for access policy)
            import subprocess

            result = subprocess.run(
                ["az", "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"],
                capture_output=True,
                text=True,
            )
            user_object_id = result.stdout.strip()

            # Create Key Vault
            poller = self.keyvault_client.vaults.begin_create_or_update(
                self.resource_group,
                keyvault_name,
                {
                    "location": self.location,
                    "properties": {
                        "sku": {"family": "A", "name": "standard"},
                        "tenant_id": self.credential._get_token(
                            "https://management.azure.com/.default"
                        ).token,
                        "access_policies": [
                            {
                                "tenant_id": self.credential._get_token(
                                    "https://management.azure.com/.default"
                                ).token,
                                "object_id": user_object_id,
                                "permissions": {
                                    "keys": ["all"],
                                    "secrets": ["all"],
                                    "certificates": ["all"],
                                },
                            }
                        ],
                    },
                    "tags": {
                        "project": "mlops-pipeline",
                        "purpose": "secrets-management",
                    },
                },
            )

            keyvault = poller.result()
            vault_url = f"https://{keyvault_name}.vault.azure.net/"

            logger.info(f"Key Vault created: {keyvault.name}")

            return {"vault_name": keyvault_name, "vault_url": vault_url}

        except Exception as e:
            logger.error(f"Failed to create Key Vault: {e}")
            return {}

    def create_ml_workspace(
        self, workspace_name: str, storage_account: str, keyvault_name: str
    ) -> Dict[str, str]:
        """Create Azure ML Workspace"""
        try:
            logger.info(f"Creating ML Workspace: {workspace_name}")

            # Create Application Insights (required for ML workspace)
            app_insights_name = f"{workspace_name}-insights"

            # Create ML Workspace
            poller = self.ml_client.workspaces.begin_create_or_update(
                self.resource_group,
                workspace_name,
                {
                    "location": self.location,
                    "friendly_name": workspace_name,
                    "description": "MLOps Pipeline Workspace",
                    "storage_account": f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.Storage/storageAccounts/{storage_account}",
                    "key_vault": f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}/providers/Microsoft.KeyVault/vaults/{keyvault_name}",
                    "tags": {"project": "mlops-pipeline", "purpose": "ml-workspace"},
                },
            )

            workspace = poller.result()

            logger.info(f"ML Workspace created: {workspace.name}")

            return {
                "workspace_name": workspace_name,
                "workspace_id": workspace.workspace_id,
            }

        except Exception as e:
            logger.error(f"Failed to create ML Workspace: {e}")
            return {}

    def setup_secrets(self, keyvault_name: str, secrets: Dict[str, str]):
        """Store secrets in Key Vault"""
        try:
            vault_url = f"https://{keyvault_name}.vault.azure.net/"
            secret_client = SecretClient(
                vault_url=vault_url, credential=self.credential
            )

            for secret_name, secret_value in secrets.items():
                secret_client.set_secret(secret_name, secret_value)
                logger.info(f"Secret stored: {secret_name}")

        except Exception as e:
            logger.error(f"Failed to store secrets: {e}")

    def create_containers(self, storage_account_name: str, containers: list):
        """Create blob containers"""
        try:
            from azure.storage.blob import BlobServiceClient

            # Get connection string
            keys = self.storage_client.storage_accounts.list_keys(
                self.resource_group, storage_account_name
            )

            connection_string = (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={storage_account_name};"
                f"AccountKey={keys.keys[0].value};"
                f"EndpointSuffix=core.windows.net"
            )

            blob_service = BlobServiceClient.from_connection_string(connection_string)

            for container_name in containers:
                try:
                    blob_service.create_container(container_name)
                    logger.info(f"Container created: {container_name}")
                except Exception as e:
                    if "ContainerAlreadyExists" in str(e):
                        logger.info(f"Container already exists: {container_name}")
                    else:
                        raise e

        except Exception as e:
            logger.error(f"Failed to create containers: {e}")


@click.command()
@click.option("--subscription-id", required=True, help="Azure subscription ID")
@click.option("--resource-group", default="mlops-rg", help="Resource group name")
@click.option("--location", default="eastus2", help="Azure region")
@click.option("--storage-account", default="mlopsstorage", help="Storage account name")
@click.option("--keyvault-name", default="mlops-keyvault", help="Key Vault name")
@click.option("--workspace-name", default="mlops-workspace", help="ML Workspace name")
@click.option("--kaggle-username", help="Kaggle username")
@click.option("--kaggle-key", help="Kaggle API key")
def setup_azure_resources(
    subscription_id: str,
    resource_group: str,
    location: str,
    storage_account: str,
    keyvault_name: str,
    workspace_name: str,
    kaggle_username: str,
    kaggle_key: str,
):
    """Setup complete Azure infrastructure for MLOps pipeline"""

    logger.info("Starting Azure resource setup...")

    # Initialize resource manager
    arm = AzureResourceManager(subscription_id, resource_group, location)

    # Create resource group
    if not arm.create_resource_group():
        logger.error("Failed to create resource group. Exiting.")
        return

    # Create storage account
    storage_info = arm.create_storage_account(storage_account)
    if not storage_info:
        logger.error("Failed to create storage account. Exiting.")
        return

    # Create Key Vault
    keyvault_info = arm.create_key_vault(keyvault_name)
    if not keyvault_info:
        logger.error("Failed to create Key Vault. Exiting.")
        return

    # Create ML Workspace
    workspace_info = arm.create_ml_workspace(
        workspace_name, storage_account, keyvault_name
    )
    if not workspace_info:
        logger.error("Failed to create ML Workspace. Exiting.")
        return

    # Create blob containers
    containers = ["datasets", "models", "monitoring", "experiments"]
    arm.create_containers(storage_account, containers)

    # Store secrets in Key Vault
    secrets = {
        "storage-connection-string": storage_info["connection_string"],
        "storage-account-key": storage_info["primary_key"],
    }

    if kaggle_username and kaggle_key:
        secrets.update({"kaggle-username": kaggle_username, "kaggle-key": kaggle_key})

    arm.setup_secrets(keyvault_name, secrets)

    # Generate configuration file
    config = {
        "azure": {
            "subscription_id": subscription_id,
            "resource_group": resource_group,
            "location": location,
            "storage_account": storage_account,
            "keyvault_name": keyvault_name,
            "workspace_name": workspace_name,
        },
        "endpoints": {
            "storage_url": f"https://{storage_account}.blob.core.windows.net",
            "keyvault_url": keyvault_info["vault_url"],
            "workspace_url": f"https://ml.azure.com/workspaces/{workspace_info['workspace_id']}",
        },
    }

    # Save configuration
    with open("azure_config.json", "w") as f:
        json.dump(config, f, indent=2)

    logger.info("✅ Azure resource setup completed successfully!")
    logger.info(f"Configuration saved to: azure_config.json")
    logger.info(f"ML Workspace: {workspace_info['workspace_name']}")
    logger.info(f"Storage Account: {storage_info['account_name']}")
    logger.info(f"Key Vault: {keyvault_info['vault_name']}")


if __name__ == "__main__":
    setup_azure_resources()
