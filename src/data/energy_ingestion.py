"""
Energy Consumption MLOps Pipeline - Enhanced Data Ingestion
Uses existing Kaggle credentials for hourly energy consumption dataset
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import great_expectations as gx
import kagglehub
import numpy as np
import pandas as pd
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EnergyDatasetConfig:
    """Configuration for Energy Consumption dataset"""

    dataset_name: str = "robikscube/hourly-energy-consumption"
    target_column: str = "energy_consumption_mwh"
    datetime_column: str = "datetime"
    feature_columns: List[str] = None
    validation_rules: Dict[str, Any] = None

    def __post_init__(self):
        if self.feature_columns is None:
            self.feature_columns = [
                "hour",
                "day_of_week",
                "month",
                "year",
                "is_weekend",
                "season",
                "temperature_lag",
                "consumption_lag_1h",
                "consumption_lag_24h",
            ]

        if self.validation_rules is None:
            self.validation_rules = {
                "missing_threshold": 0.05,  # Max 5% missing values
                "min_records": 1000,
                "date_range_years": 5,
            }


class EnergyConsumptionIngestion:
    """Enhanced data ingestion for energy consumption with enterprise features"""

    def __init__(self, config: EnergyDatasetConfig):
        self.config = config
        self.blob_client = self._setup_azure_storage()
        self.data_context = gx.get_context()
        self.kaggle_credentials = self._load_kaggle_credentials()

    def _load_kaggle_credentials(self) -> Dict[str, str]:
        """Load existing Kaggle credentials"""
        try:
            # First try from the existing project location
            kaggle_path = Path(
                "C:/Users/sanke/Documents/MLops/Project-Aegis-Finance/_temp/kaggle.json"
            )
            if kaggle_path.exists():
                with open(kaggle_path, "r") as f:
                    creds = json.load(f)
                logger.info("Loaded Kaggle credentials from existing project")
                return creds

            # Fallback to standard Kaggle location
            kaggle_dir = Path.home() / ".kaggle"
            kaggle_file = kaggle_dir / "kaggle.json"

            if kaggle_file.exists():
                with open(kaggle_file, "r") as f:
                    creds = json.load(f)
                logger.info("Loaded Kaggle credentials from ~/.kaggle/")
                return creds

            # If not found, copy from existing location to standard location
            if kaggle_path.exists():
                kaggle_dir.mkdir(exist_ok=True)
                shutil.copy2(kaggle_path, kaggle_file)
                kaggle_file.chmod(0o600)  # Set proper permissions

                with open(kaggle_file, "r") as f:
                    creds = json.load(f)
                logger.info("Copied and loaded Kaggle credentials")
                return creds

        except Exception as e:
            logger.error(f"Failed to load Kaggle credentials: {e}")

        return {"username": "", "key": ""}

    def _setup_azure_storage(self) -> Optional[BlobServiceClient]:
        """Setup Azure Blob Storage client"""
        try:
            credential = DefaultAzureCredential()
            account_url = f"https://{os.getenv('AZURE_STORAGE_ACCOUNT', 'mlopsstorage')}.blob.core.windows.net"
            return BlobServiceClient(account_url=account_url, credential=credential)
        except Exception as e:
            logger.warning(f"Azure Storage setup failed: {e}")
            return None

    def download_energy_dataset(self, local_path: str = "data/raw") -> Path:
        """Download energy consumption dataset using kagglehub"""
        try:
            # Setup Kaggle credentials
            os.environ["KAGGLE_USERNAME"] = self.kaggle_credentials["username"]
            os.environ["KAGGLE_KEY"] = self.kaggle_credentials["key"]

            logger.info(f"Downloading dataset: {self.config.dataset_name}")

            # Download using kagglehub
            dataset_path = kagglehub.dataset_download(self.config.dataset_name)
            logger.info(f"Dataset downloaded to: {dataset_path}")

            # Copy to our project structure
            local_path_obj = Path(local_path)
            local_path_obj.mkdir(parents=True, exist_ok=True)

            # Find CSV files in downloaded dataset
            dataset_path_obj = Path(dataset_path)
            csv_files = list(dataset_path_obj.glob("*.csv"))

            if not csv_files:
                raise FileNotFoundError("No CSV files found in downloaded dataset")

            # Copy main dataset file
            main_csv = csv_files[0]  # Assume first CSV is main dataset
            destination = local_path_obj / main_csv.name
            shutil.copy2(main_csv, destination)

            logger.info(f"Dataset copied to project: {destination}")
            return destination

        except Exception as e:
            logger.error(f"Failed to download dataset: {e}")
            raise

    def load_and_preprocess_data(self, file_path: Path) -> pd.DataFrame:
        """Load and preprocess energy consumption data"""
        try:
            logger.info(f"Loading data from: {file_path}")

            # Load the dataset
            df = pd.read_csv(file_path)
            logger.info(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")
            logger.info(f"Columns: {list(df.columns)}")

            # Identify datetime and target columns dynamically
            datetime_col = self._identify_datetime_column(df)
            target_col = self._identify_target_column(df)

            if datetime_col:
                # Convert datetime column
                df[datetime_col] = pd.to_datetime(df[datetime_col])
                df = df.sort_values(datetime_col).reset_index(drop=True)

                # Create time-based features
                df = self._create_time_features(df, datetime_col)

            if target_col:
                # Clean target column
                df = self._clean_target_column(df, target_col)

                # Create lag features
                df = self._create_lag_features(df, target_col)

            # Handle missing values
            df = self._handle_missing_values(df)

            # Remove outliers
            df = self._remove_outliers(df, target_col)

            logger.info(
                f"Preprocessed dataset: {df.shape[0]} rows, {df.shape[1]} columns"
            )
            return df

        except Exception as e:
            logger.error(f"Data preprocessing failed: {e}")
            raise

    def _identify_datetime_column(self, df: pd.DataFrame) -> Optional[str]:
        """Identify datetime column in the dataset"""
        datetime_candidates = ["datetime", "date", "timestamp", "time", "Datetime"]

        for col in datetime_candidates:
            if col in df.columns:
                return col

        # Check for columns that might be datetime
        for col in df.columns:
            if df[col].dtype == "object":
                try:
                    pd.to_datetime(df[col].head(100))
                    logger.info(f"Identified datetime column: {col}")
                    return col
                except:
                    continue

        logger.warning("No datetime column identified")
        return None

    def _identify_target_column(self, df: pd.DataFrame) -> Optional[str]:
        """Identify target column for energy consumption"""
        target_candidates = [
            "energy_consumption",
            "consumption",
            "demand",
            "load",
            "mwh",
            "kwh",
            "power",
            "usage",
            "Energy_Consumption",
            "PJME_MW",
            "AEP_MW",
            "COMED_MW",
            "DAYTON_MW",
        ]

        for col in df.columns:
            col_lower = col.lower()
            for candidate in target_candidates:
                if candidate.lower() in col_lower:
                    logger.info(f"Identified target column: {col}")
                    return col

        # If no clear target, use first numeric column
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            target_col = numeric_cols[0]
            logger.info(f"Using first numeric column as target: {target_col}")
            return target_col

        logger.warning("No target column identified")
        return None

    def _create_time_features(
        self, df: pd.DataFrame, datetime_col: str
    ) -> pd.DataFrame:
        """Create time-based features for energy consumption prediction"""
        df = df.copy()

        # Basic time features
        df["hour"] = df[datetime_col].dt.hour
        df["day_of_week"] = df[datetime_col].dt.dayofweek
        df["month"] = df[datetime_col].dt.month
        df["year"] = df[datetime_col].dt.year
        df["day_of_year"] = df[datetime_col].dt.dayofyear

        # Cyclical features (important for energy consumption patterns)
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        df["day_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["day_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

        # Business logic features
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        df["is_business_hour"] = ((df["hour"] >= 9) & (df["hour"] <= 17)).astype(int)

        # Season encoding
        df["season"] = df["month"].map(
            {
                12: 0,
                1: 0,
                2: 0,  # Winter
                3: 1,
                4: 1,
                5: 1,  # Spring
                6: 2,
                7: 2,
                8: 2,  # Summer
                9: 3,
                10: 3,
                11: 3,  # Fall
            }
        )

        # Peak hours (energy consumption typically peaks in evening)
        df["is_peak_hour"] = ((df["hour"] >= 17) & (df["hour"] <= 21)).astype(int)

        logger.info("Created time-based features")
        return df

    def _create_lag_features(self, df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Create lag features for time series prediction"""
        df = df.copy()

        # Create lag features (important for energy consumption prediction)
        lag_periods = [1, 2, 3, 6, 12, 24, 48, 168]  # 1h, 2h, 3h, 6h, 12h, 1d, 2d, 1w

        for lag in lag_periods:
            df[f"{target_col}_lag_{lag}h"] = df[target_col].shift(lag)

        # Rolling statistics
        for window in [24, 168]:  # 1 day, 1 week
            df[f"{target_col}_rolling_mean_{window}h"] = (
                df[target_col].rolling(window=window).mean()
            )
            df[f"{target_col}_rolling_std_{window}h"] = (
                df[target_col].rolling(window=window).std()
            )
            df[f"{target_col}_rolling_min_{window}h"] = (
                df[target_col].rolling(window=window).min()
            )
            df[f"{target_col}_rolling_max_{window}h"] = (
                df[target_col].rolling(window=window).max()
            )

        # Difference features
        df[f"{target_col}_diff_1h"] = df[target_col].diff(1)
        df[f"{target_col}_diff_24h"] = df[target_col].diff(24)

        logger.info("Created lag and rolling features")
        return df

    def _clean_target_column(self, df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Clean and validate target column"""
        df = df.copy()

        # Remove negative values (energy consumption should be positive)
        negative_mask = df[target_col] < 0
        if negative_mask.sum() > 0:
            logger.warning(
                f"Removing {negative_mask.sum()} negative values from target column"
            )
            df.loc[negative_mask, target_col] = np.nan

        # Handle extreme outliers (values > 99.9th percentile)
        upper_threshold = df[target_col].quantile(0.999)
        outlier_mask = df[target_col] > upper_threshold
        if outlier_mask.sum() > 0:
            logger.warning(
                f"Capping {outlier_mask.sum()} extreme outliers in target column"
            )
            df.loc[outlier_mask, target_col] = upper_threshold

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values with domain-specific strategies"""
        df = df.copy()

        # For lag features, forward fill (energy consumption is continuous)
        lag_columns = [col for col in df.columns if "lag" in col or "rolling" in col]
        for col in lag_columns:
            df[col] = df[col].fillna(method="ffill").fillna(method="bfill")

        # For other numeric columns, use median
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col not in lag_columns and df[col].isnull().sum() > 0:
                df[col] = df[col].fillna(df[col].median())

        # Drop rows with too many missing values
        missing_threshold = len(df.columns) * 0.5
        df = df.dropna(thresh=missing_threshold)

        logger.info(f"Handled missing values, remaining rows: {len(df)}")
        return df

    def _remove_outliers(self, df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Remove outliers using IQR method"""
        if target_col not in df.columns:
            return df

        df = df.copy()

        Q1 = df[target_col].quantile(0.25)
        Q3 = df[target_col].quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outlier_mask = (df[target_col] < lower_bound) | (df[target_col] > upper_bound)
        outliers_count = outlier_mask.sum()

        if outliers_count > 0:
            logger.info(
                f"Removing {outliers_count} outliers ({outliers_count/len(df)*100:.2f}%)"
            )
            df = df[~outlier_mask]

        return df

    def validate_energy_data(self, df: pd.DataFrame) -> bool:
        """Validate energy consumption dataset"""
        try:
            # Basic validation
            if len(df) < self.config.validation_rules["min_records"]:
                logger.error(
                    f"Dataset too small: {len(df)} < {self.config.validation_rules['min_records']}"
                )
                return False

            # Check for target column
            target_col = self._identify_target_column(df)
            if not target_col:
                logger.error("No target column found")
                return False

            # Check missing values threshold
            missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
            if missing_ratio > self.config.validation_rules["missing_threshold"]:
                logger.error(f"Too many missing values: {missing_ratio:.2%}")
                return False

            # Energy-specific validations
            if target_col in df.columns:
                # Check for reasonable energy consumption values
                if df[target_col].min() < 0:
                    logger.error("Negative energy consumption values found")
                    return False

                # Check for data completeness
                if df[target_col].isnull().sum() / len(df) > 0.1:
                    logger.error("Too many missing values in target column")
                    return False

            logger.info("Data validation passed")
            return True

        except Exception as e:
            logger.error(f"Data validation error: {e}")
            return False

    def upload_to_azure(self, df: pd.DataFrame, blob_name: str) -> Optional[str]:
        """Upload processed data to Azure Blob Storage"""
        if not self.blob_client:
            logger.warning("Azure Blob Storage not available")
            return None

        try:
            container_name = os.getenv("AZURE_CONTAINER_NAME", "datasets")

            # Convert DataFrame to CSV
            csv_buffer = df.to_csv(index=False)

            blob_client = self.blob_client.get_blob_client(
                container=container_name, blob=blob_name
            )

            blob_client.upload_blob(csv_buffer, overwrite=True)

            blob_url = f"https://{os.getenv('AZURE_STORAGE_ACCOUNT', 'mlopsstorage')}.blob.core.windows.net/{container_name}/{blob_name}"
            logger.info(f"Data uploaded to: {blob_url}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload to Azure: {e}")
            return None

    def process_energy_pipeline(self) -> Dict[str, Any]:
        """Execute complete energy consumption data pipeline"""
        logger.info("Starting energy consumption data pipeline")

        try:
            # Download dataset
            dataset_path = self.download_energy_dataset()

            # Load and preprocess data
            df = self.load_and_preprocess_data(dataset_path)

            # Validate data
            if not self.validate_energy_data(df):
                raise ValueError("Data validation failed")

            # Save processed data locally
            processed_path = Path("data/processed/energy_consumption_processed.csv")
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(processed_path, index=False)

            # Upload to Azure (if available)
            blob_url = self.upload_to_azure(
                df, "processed/energy_consumption_processed.csv"
            )

            # Prepare train/test split
            train_size = int(0.8 * len(df))
            train_df = df[:train_size]
            test_df = df[train_size:]

            # Save splits
            train_df.to_csv("data/processed/train_energy.csv", index=False)
            test_df.to_csv("data/processed/test_energy.csv", index=False)

            target_col = self._identify_target_column(df)

            result = {
                "dataset_name": self.config.dataset_name,
                "local_path": str(processed_path),
                "blob_url": blob_url,
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "target_column": target_col,
                "train_rows": len(train_df),
                "test_rows": len(test_df),
                "date_range": {
                    "start": (
                        str(df.iloc[0]["datetime"])
                        if "datetime" in df.columns
                        else "unknown"
                    ),
                    "end": (
                        str(df.iloc[-1]["datetime"])
                        if "datetime" in df.columns
                        else "unknown"
                    ),
                },
                "feature_columns": [col for col in df.columns if col != target_col],
                "preprocessing_steps": [
                    "time_features_created",
                    "lag_features_created",
                    "missing_values_handled",
                    "outliers_removed",
                ],
            }

            logger.info("Energy consumption pipeline completed successfully")
            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise


# Example usage
if __name__ == "__main__":
    # Configure for energy consumption dataset
    config = EnergyDatasetConfig(
        dataset_name="robikscube/hourly-energy-consumption",
        validation_rules={
            "missing_threshold": 0.05,
            "min_records": 5000,
            "date_range_years": 3,
        },
    )

    # Run the pipeline
    ingestion = EnergyConsumptionIngestion(config)
    result = ingestion.process_energy_pipeline()

    print("Pipeline Results:")
    print(f"Dataset: {result['dataset_name']}")
    print(f"Total Records: {result['total_rows']:,}")
    print(f"Features: {result['total_columns']}")
    print(f"Target Column: {result['target_column']}")
    print(
        f"Date Range: {result['date_range']['start']} to {result['date_range']['end']}"
    )
    print(f"Train/Test Split: {result['train_rows']:,} / {result['test_rows']:,}")
