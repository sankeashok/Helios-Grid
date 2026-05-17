"""
Energy Consumption Feature Engineering Pipeline
Specialized feature engineering for time series energy prediction
"""

import logging
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EnergyFeatureConfig:
    """Configuration for energy consumption feature engineering"""

    target_column: str = "energy_consumption"
    datetime_column: str = "datetime"

    # Time-based features
    create_cyclical_features: bool = True
    create_lag_features: bool = True
    lag_periods: List[int] = None
    rolling_windows: List[int] = None

    # Feature selection
    feature_selection_method: str = (
        "mutual_info"  # 'f_regression', 'mutual_info', 'both'
    )
    max_features: int = 50

    # Scaling
    scaling_method: str = "robust"  # 'standard', 'robust', 'minmax'

    # Validation
    min_correlation_threshold: float = 0.01
    max_correlation_threshold: float = 0.95

    def __post_init__(self):
        if self.lag_periods is None:
            # Energy consumption specific lags (hourly data)
            self.lag_periods = [1, 2, 3, 6, 12, 24, 48, 168, 336]  # 1h to 2 weeks

        if self.rolling_windows is None:
            self.rolling_windows = [6, 12, 24, 48, 168]  # 6h to 1 week


class EnergyFeatureEngineer(BaseEstimator, TransformerMixin):
    """Advanced feature engineering for energy consumption prediction"""

    def __init__(self, config: EnergyFeatureConfig):
        self.config = config
        self.feature_names_ = []
        self.scaler = None
        self.feature_selector = None
        self.feature_importance_ = {}

    def fit(self, X: pd.DataFrame, y: pd.Series = None):
        """Fit the feature engineering pipeline"""
        logger.info("Fitting energy consumption feature engineering pipeline")

        # Create all features
        X_features = self._create_all_features(X.copy())

        # Remove highly correlated features
        X_features = self._remove_correlated_features(X_features)

        # Setup scaler
        self._setup_scaler(X_features)

        # Fit scaler on numeric features
        numeric_features = X_features.select_dtypes(include=[np.number]).columns
        if len(numeric_features) > 0:
            self.scaler.fit(X_features[numeric_features])

        # Feature selection
        if y is not None:
            self._setup_feature_selection(X_features, y)

        # Store feature names
        self.feature_names_ = list(X_features.columns)

        logger.info(
            f"Feature engineering fitted with {len(self.feature_names_)} features"
        )
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform features using fitted pipeline"""
        # Create all features
        X_features = self._create_all_features(X.copy())

        # Ensure we have the same columns as during fit
        missing_cols = set(self.feature_names_) - set(X_features.columns)
        for col in missing_cols:
            X_features[col] = 0  # Fill missing columns with 0

        # Reorder columns to match training
        X_features = X_features[self.feature_names_]

        # Apply scaling
        if self.scaler is not None:
            numeric_features = X_features.select_dtypes(include=[np.number]).columns
            if len(numeric_features) > 0:
                X_features[numeric_features] = self.scaler.transform(
                    X_features[numeric_features]
                )

        # Apply feature selection
        if self.feature_selector is not None:
            X_features = pd.DataFrame(
                self.feature_selector.transform(X_features),
                columns=self.feature_selector.get_feature_names_out(),
                index=X_features.index,
            )

        return X_features

    def _create_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive feature set for energy consumption"""

        # Identify datetime column if exists
        datetime_col = None
        for col in df.columns:
            if (
                "datetime" in col.lower()
                or "date" in col.lower()
                or "time" in col.lower()
            ):
                try:
                    pd.to_datetime(df[col])
                    datetime_col = col
                    break
                except:
                    continue

        if datetime_col:
            df = self._create_temporal_features(df, datetime_col)

        # Create lag features if target column exists
        target_col = self._identify_target_column(df)
        if target_col and self.config.create_lag_features:
            df = self._create_lag_features(df, target_col)
            df = self._create_rolling_features(df, target_col)

        # Create interaction features
        df = self._create_interaction_features(df)

        # Create statistical features
        df = self._create_statistical_features(df)

        # Handle missing values
        df = self._handle_missing_values(df)

        return df

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
                    return col

        return None

    def _create_temporal_features(
        self, df: pd.DataFrame, datetime_col: str
    ) -> pd.DataFrame:
        """Create comprehensive temporal features"""
        df = df.copy()

        # Ensure datetime column is datetime type
        df[datetime_col] = pd.to_datetime(df[datetime_col])

        # Basic time components
        df["hour"] = df[datetime_col].dt.hour
        df["day_of_week"] = df[datetime_col].dt.dayofweek
        df["day_of_month"] = df[datetime_col].dt.day
        df["month"] = df[datetime_col].dt.month
        df["quarter"] = df[datetime_col].dt.quarter
        df["year"] = df[datetime_col].dt.year
        df["day_of_year"] = df[datetime_col].dt.dayofyear
        df["week_of_year"] = df[datetime_col].dt.isocalendar().week

        if self.config.create_cyclical_features:
            # Cyclical encoding for periodic patterns
            df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
            df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
            df["day_of_week_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
            df["day_of_week_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
            df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
            df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
            df["day_of_year_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
            df["day_of_year_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

        # Business logic features for energy consumption
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        df["is_monday"] = (df["day_of_week"] == 0).astype(int)
        df["is_friday"] = (df["day_of_week"] == 4).astype(int)

        # Energy-specific time periods
        df["is_business_hour"] = ((df["hour"] >= 8) & (df["hour"] <= 18)).astype(int)
        df["is_peak_morning"] = ((df["hour"] >= 7) & (df["hour"] <= 9)).astype(int)
        df["is_peak_evening"] = ((df["hour"] >= 17) & (df["hour"] <= 20)).astype(int)
        df["is_night"] = ((df["hour"] >= 22) | (df["hour"] <= 6)).astype(int)

        # Seasonal features
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

        # Holiday approximations (simplified)
        df["is_holiday_season"] = ((df["month"] == 12) | (df["month"] == 1)).astype(int)
        df["is_summer_peak"] = ((df["month"] >= 6) & (df["month"] <= 8)).astype(int)
        df["is_winter_peak"] = ((df["month"] == 12) | (df["month"] <= 2)).astype(int)

        logger.info("Created temporal features")
        return df

    def _create_lag_features(self, df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Create lag features for time series prediction"""
        df = df.copy()

        for lag in self.config.lag_periods:
            df[f"{target_col}_lag_{lag}"] = df[target_col].shift(lag)

        # Difference features
        df[f"{target_col}_diff_1"] = df[target_col].diff(1)
        df[f"{target_col}_diff_24"] = df[target_col].diff(24)  # Daily difference
        df[f"{target_col}_diff_168"] = df[target_col].diff(168)  # Weekly difference

        # Percentage change features
        df[f"{target_col}_pct_change_1"] = df[target_col].pct_change(1)
        df[f"{target_col}_pct_change_24"] = df[target_col].pct_change(24)

        logger.info(f"Created {len(self.config.lag_periods)} lag features")
        return df

    def _create_rolling_features(
        self, df: pd.DataFrame, target_col: str
    ) -> pd.DataFrame:
        """Create rolling window features"""
        df = df.copy()

        for window in self.config.rolling_windows:
            # Basic rolling statistics
            df[f"{target_col}_rolling_mean_{window}"] = (
                df[target_col].rolling(window=window).mean()
            )
            df[f"{target_col}_rolling_std_{window}"] = (
                df[target_col].rolling(window=window).std()
            )
            df[f"{target_col}_rolling_min_{window}"] = (
                df[target_col].rolling(window=window).min()
            )
            df[f"{target_col}_rolling_max_{window}"] = (
                df[target_col].rolling(window=window).max()
            )
            df[f"{target_col}_rolling_median_{window}"] = (
                df[target_col].rolling(window=window).median()
            )

            # Rolling quantiles
            df[f"{target_col}_rolling_q25_{window}"] = (
                df[target_col].rolling(window=window).quantile(0.25)
            )
            df[f"{target_col}_rolling_q75_{window}"] = (
                df[target_col].rolling(window=window).quantile(0.75)
            )

            # Rolling trend features
            df[f"{target_col}_rolling_trend_{window}"] = (
                df[target_col] - df[f"{target_col}_rolling_mean_{window}"]
            )

            # Rolling volatility
            df[f"{target_col}_rolling_volatility_{window}"] = (
                df[f"{target_col}_rolling_std_{window}"]
                / df[f"{target_col}_rolling_mean_{window}"]
            )

        logger.info(
            f"Created rolling features for {len(self.config.rolling_windows)} windows"
        )
        return df

    def _create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create interaction features relevant to energy consumption"""
        df = df.copy()

        # Hour-day interactions (energy patterns differ by day type)
        if "hour" in df.columns and "is_weekend" in df.columns:
            df["hour_weekend_interaction"] = df["hour"] * df["is_weekend"]

        # Season-hour interactions (seasonal energy patterns)
        if "hour" in df.columns and "season" in df.columns:
            df["hour_season_interaction"] = df["hour"] * df["season"]

        # Temperature-related interactions (if temperature data available)
        temp_cols = [col for col in df.columns if "temp" in col.lower()]
        if temp_cols and "hour" in df.columns:
            temp_col = temp_cols[0]
            df["temp_hour_interaction"] = df[temp_col] * df["hour"]

        # Business hour interactions
        if "is_business_hour" in df.columns and "day_of_week" in df.columns:
            df["business_hour_weekday"] = df["is_business_hour"] * (
                1 - df["is_weekend"]
            )

        logger.info("Created interaction features")
        return df

    def _create_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create statistical features from existing numeric columns"""
        df = df.copy()

        # Get numeric columns (excluding target and datetime)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        target_col = self._identify_target_column(df)

        if target_col:
            numeric_cols = [col for col in numeric_cols if col != target_col]

        # Remove lag and rolling features from statistical feature creation
        base_numeric_cols = [
            col
            for col in numeric_cols
            if not any(
                keyword in col for keyword in ["lag", "rolling", "diff", "pct_change"]
            )
        ]

        if len(base_numeric_cols) >= 2:
            # Create ratios between key features
            for i, col1 in enumerate(base_numeric_cols[:5]):  # Limit to avoid explosion
                for col2 in base_numeric_cols[i + 1 : 6]:
                    if df[col2].std() > 0:  # Avoid division by constant
                        df[f"{col1}_{col2}_ratio"] = df[col1] / (df[col2] + 1e-8)

        logger.info("Created statistical features")
        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values with domain-specific strategies"""
        df = df.copy()

        # Forward fill lag features (time series continuity)
        lag_cols = [col for col in df.columns if "lag" in col]
        for col in lag_cols:
            df[col] = df[col].fillna(method="ffill")

        # Forward fill rolling features
        rolling_cols = [col for col in df.columns if "rolling" in col]
        for col in rolling_cols:
            df[col] = df[col].fillna(method="ffill")

        # Fill remaining numeric columns with median
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if df[col].isnull().sum() > 0:
                df[col] = df[col].fillna(df[col].median())

        # Fill categorical columns with mode
        categorical_cols = df.select_dtypes(include=["object"]).columns
        for col in categorical_cols:
            if df[col].isnull().sum() > 0:
                df[col] = df[col].fillna(
                    df[col].mode().iloc[0] if len(df[col].mode()) > 0 else "unknown"
                )

        return df

    def _remove_correlated_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove highly correlated features"""
        numeric_df = df.select_dtypes(include=[np.number])

        if len(numeric_df.columns) <= 1:
            return df

        # Calculate correlation matrix
        corr_matrix = numeric_df.corr().abs()

        # Find highly correlated pairs
        upper_triangle = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )

        # Find features to drop
        to_drop = [
            column
            for column in upper_triangle.columns
            if any(upper_triangle[column] > self.config.max_correlation_threshold)
        ]

        if to_drop:
            logger.info(f"Removing {len(to_drop)} highly correlated features")
            df = df.drop(columns=to_drop)

        return df

    def _setup_scaler(self, X: pd.DataFrame):
        """Setup appropriate scaler based on configuration"""
        if self.config.scaling_method == "standard":
            self.scaler = StandardScaler()
        elif self.config.scaling_method == "robust":
            self.scaler = RobustScaler()
        elif self.config.scaling_method == "minmax":
            self.scaler = MinMaxScaler()
        else:
            self.scaler = RobustScaler()  # Default

    def _setup_feature_selection(self, X: pd.DataFrame, y: pd.Series):
        """Setup feature selection based on configuration"""
        if self.config.feature_selection_method == "f_regression":
            self.feature_selector = SelectKBest(
                score_func=f_regression, k=min(self.config.max_features, X.shape[1])
            )
        elif self.config.feature_selection_method == "mutual_info":
            self.feature_selector = SelectKBest(
                score_func=mutual_info_regression,
                k=min(self.config.max_features, X.shape[1]),
            )

        if self.feature_selector:
            self.feature_selector.fit(X, y)

            # Store feature importance
            feature_scores = self.feature_selector.scores_
            self.feature_importance_ = dict(zip(X.columns, feature_scores))

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        return self.feature_importance_


class EnergyFeaturePipeline:
    """Complete feature engineering pipeline for energy consumption"""

    def __init__(self, config: EnergyFeatureConfig):
        self.config = config
        self.feature_engineer = EnergyFeatureEngineer(config)

    def process_features(
        self, train_df: pd.DataFrame, test_df: pd.DataFrame = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
        """Process features for energy consumption prediction"""

        with mlflow.start_run(nested=True, run_name="energy_feature_engineering"):
            logger.info("Starting energy consumption feature engineering")

            # Identify target column
            target_col = self.feature_engineer._identify_target_column(train_df)
            if not target_col:
                raise ValueError("No target column found in training data")

            # Separate features and target
            X_train = train_df.drop(columns=[target_col])
            y_train = train_df[target_col]

            # Log original data info
            mlflow.log_param("original_features", X_train.shape[1])
            mlflow.log_param("training_samples", X_train.shape[0])
            mlflow.log_param("target_column", target_col)

            # Fit and transform training data
            self.feature_engineer.fit(X_train, y_train)
            X_train_processed = self.feature_engineer.transform(X_train)

            # Transform test data if provided
            X_test_processed = None
            if test_df is not None:
                X_test = test_df.drop(columns=[target_col], errors="ignore")
                X_test_processed = self.feature_engineer.transform(X_test)
                mlflow.log_param("test_samples", X_test.shape[0])

            # Log feature engineering results
            mlflow.log_param("final_features", X_train_processed.shape[1])
            mlflow.log_param("scaling_method", self.config.scaling_method)
            mlflow.log_param(
                "feature_selection_method", self.config.feature_selection_method
            )

            # Log feature importance
            feature_importance = self.feature_engineer.get_feature_importance()
            if feature_importance:
                top_features = sorted(
                    feature_importance.items(), key=lambda x: x[1], reverse=True
                )[:10]
                for i, (feat, score) in enumerate(top_features):
                    mlflow.log_metric(f"top_feature_{i+1}_score", score)

            # Save feature engineering pipeline
            mlflow.sklearn.log_model(
                self.feature_engineer,
                "energy_feature_pipeline",
                registered_model_name="energy_feature_engineering_pipeline",
            )

            logger.info(
                f"Feature engineering completed: {X_train_processed.shape[1]} features"
            )

            return X_train_processed, X_test_processed, y_train

    def save_pipeline(self, filepath: str):
        """Save the fitted feature pipeline"""
        joblib.dump(self.feature_engineer, filepath)
        logger.info(f"Feature pipeline saved to {filepath}")

    def load_pipeline(self, filepath: str):
        """Load a fitted feature pipeline"""
        self.feature_engineer = joblib.load(filepath)
        logger.info(f"Feature pipeline loaded from {filepath}")


# Example usage
if __name__ == "__main__":
    # Load processed energy data
    try:
        train_df = pd.read_csv("data/processed/train_energy.csv")
        test_df = pd.read_csv("data/processed/test_energy.csv")

        # Configure feature engineering
        config = EnergyFeatureConfig(
            target_column="energy_consumption",  # Adjust based on actual column name
            create_cyclical_features=True,
            create_lag_features=True,
            lag_periods=[1, 2, 3, 6, 12, 24, 48, 168],
            rolling_windows=[6, 12, 24, 48, 168],
            feature_selection_method="mutual_info",
            max_features=50,
            scaling_method="robust",
        )

        # Process features
        pipeline = EnergyFeaturePipeline(config)
        X_train, X_test, y_train = pipeline.process_features(train_df, test_df)

        print(f"Feature engineering completed:")
        print(f"Training features shape: {X_train.shape}")
        print(f"Test features shape: {X_test.shape if X_test is not None else 'None'}")
        print(f"Target shape: {y_train.shape}")

        # Save processed features
        X_train.to_csv("data/processed/X_train_energy.csv", index=False)
        y_train.to_csv("data/processed/y_train_energy.csv", index=False)

        if X_test is not None:
            X_test.to_csv("data/processed/X_test_energy.csv", index=False)

        # Save pipeline
        pipeline.save_pipeline("models/energy_feature_pipeline.pkl")

    except FileNotFoundError:
        print(
            "Please run energy_ingestion.py first to download and process the dataset"
        )
    except Exception as e:
        print(f"Error: {e}")
        print(
            "Make sure the energy consumption dataset has been downloaded and processed"
        )
