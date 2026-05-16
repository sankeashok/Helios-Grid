"""
Kaggle Data Ingestion Pipeline with Azure Blob Storage
Handles automated dataset downloading, validation, and cloud storage
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import kaggle
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import great_expectations as gx
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatasetConfig:
    """Configuration for Kaggle dataset"""
    name: str
    competition_or_dataset: str  # 'competition' or 'dataset'
    target_column: str
    validation_rules: Dict[str, Any]

class KaggleDataIngestion:
    """Production-grade Kaggle data ingestion with Azure integration"""
    
    def __init__(self, config: DatasetConfig):
        self.config = config
        self.blob_client = self._setup_azure_storage()
        self.data_context = gx.get_context()
        
    def _setup_azure_storage(self) -> BlobServiceClient:
        """Setup Azure Blob Storage client with managed identity"""
        try:
            credential = DefaultAzureCredential()
            account_url = f"https://{os.getenv('AZURE_STORAGE_ACCOUNT')}.blob.core.windows.net"
            return BlobServiceClient(account_url=account_url, credential=credential)
        except Exception as e:
            logger.error(f"Failed to setup Azure Storage: {e}")
            raise
    
    def _get_kaggle_credentials(self) -> tuple:
        """Retrieve Kaggle credentials from Azure Key Vault"""
        try:
            credential = DefaultAzureCredential()
            vault_url = f"https://{os.getenv('AZURE_KEYVAULT_NAME')}.vault.azure.net/"
            client = SecretClient(vault_url=vault_url, credential=credential)
            
            username = client.get_secret("kaggle-username").value
            key = client.get_secret("kaggle-key").value
            return username, key
        except Exception as e:
            logger.warning(f"Could not retrieve from Key Vault: {e}")
            # Fallback to environment variables
            return os.getenv('KAGGLE_USERNAME'), os.getenv('KAGGLE_KEY')
    
    def download_dataset(self, local_path: str = "data/raw") -> Path:
        """Download dataset from Kaggle with retry logic"""
        os.makedirs(local_path, exist_ok=True)
        
        # Setup Kaggle credentials
        username, key = self._get_kaggle_credentials()
        os.environ['KAGGLE_USERNAME'] = username
        os.environ['KAGGLE_KEY'] = key
        
        try:
            if self.config.competition_or_dataset == 'competition':
                kaggle.api.competition_download_files(
                    self.config.name, 
                    path=local_path, 
                    unzip=True
                )
            else:
                kaggle.api.dataset_download_files(
                    self.config.name, 
                    path=local_path, 
                    unzip=True
                )
            
            logger.info(f"Dataset {self.config.name} downloaded to {local_path}")
            return Path(local_path)
            
        except Exception as e:
            logger.error(f"Failed to download dataset: {e}")
            raise
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """Validate data using Great Expectations"""
        try:
            # Create expectation suite
            suite_name = f"{self.config.name}_validation_suite"
            suite = self.data_context.add_or_update_expectation_suite(suite_name)
            
            # Add basic expectations
            validator = self.data_context.get_validator(
                batch_request=gx.core.batch.RuntimeBatchRequest(
                    datasource_name="pandas_datasource",
                    data_connector_name="runtime_data_connector",
                    data_asset_name="validation_asset",
                    runtime_parameters={"batch_data": df},
                    batch_identifiers={"default_identifier_name": "validation_batch"}
                ),
                expectation_suite_name=suite_name
            )
            
            # Core validations
            validator.expect_table_row_count_to_be_between(min_value=100)
            validator.expect_column_to_exist(self.config.target_column)
            
            # Custom validations from config
            for rule, params in self.config.validation_rules.items():
                if rule == "missing_threshold":
                    for col in df.columns:
                        validator.expect_column_values_to_not_be_null(
                            column=col, 
                            mostly=1-params
                        )
            
            # Run validation
            results = validator.validate()
            
            if results.success:
                logger.info("Data validation passed")
                return True
            else:
                logger.error(f"Data validation failed: {results}")
                return False
                
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def upload_to_azure(self, local_path: Path, blob_name: str) -> str:
        """Upload processed data to Azure Blob Storage"""
        try:
            container_name = os.getenv('AZURE_CONTAINER_NAME', 'datasets')
            blob_client = self.blob_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            with open(local_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            
            blob_url = f"https://{os.getenv('AZURE_STORAGE_ACCOUNT')}.blob.core.windows.net/{container_name}/{blob_name}"
            logger.info(f"Data uploaded to: {blob_url}")
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload to Azure: {e}")
            raise
    
    def process_pipeline(self) -> Dict[str, str]:
        """Execute complete data ingestion pipeline"""
        logger.info(f"Starting data ingestion for {self.config.name}")
        
        # Download data
        local_path = self.download_dataset()
        
        # Find and load main dataset file
        csv_files = list(local_path.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError("No CSV files found in downloaded data")
        
        main_file = csv_files[0]  # Assume first CSV is main dataset
        df = pd.read_csv(main_file)
        
        logger.info(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Validate data
        if not self.validate_data(df):
            raise ValueError("Data validation failed")
        
        # Upload to Azure
        blob_name = f"raw/{self.config.name}/{main_file.name}"
        blob_url = self.upload_to_azure(main_file, blob_name)
        
        return {
            "local_path": str(main_file),
            "blob_url": blob_url,
            "rows": df.shape[0],
            "columns": df.shape[1]
        }

# Example usage for House Prices dataset
if __name__ == "__main__":
    config = DatasetConfig(
        name="house-prices-advanced-regression-techniques",
        competition_or_dataset="competition",
        target_column="SalePrice",
        validation_rules={
            "missing_threshold": 0.3  # Max 30% missing values per column
        }
    )
    
    ingestion = KaggleDataIngestion(config)
    result = ingestion.process_pipeline()
    print(f"Pipeline completed: {result}")