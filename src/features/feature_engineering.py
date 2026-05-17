"""
Feature Engineering Pipeline with Azure ML Integration
Handles feature creation, selection, and transformation with MLflow tracking
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """Configuration for feature engineering"""

    numerical_features: List[str]
    categorical_features: List[str]
    target_column: str
    feature_selection_k: int = 20
    handle_missing: str = "median"  # 'median', 'mean', 'mode', 'drop'


class AdvancedFeatureEngineer(BaseEstimator, TransformerMixin):
    """Advanced feature engineering with domain-specific transformations"""

    def __init__(self, config: FeatureConfig):
        self.config = config
        self.numerical_transformer = None
        self.categorical_transformer = None
        self.feature_selector = None
        self.preprocessor = None

    def _create_numerical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create advanced numerical features"""
        df_enhanced = df.copy()

        # Example for house prices - adapt based on your domain
        if "GrLivArea" in df.columns and "BedroomAbvGr" in df.columns:
            df_enhanced["AreaPerBedroom"] = df_enhanced["GrLivArea"] / (
                df_enhanced["BedroomAbvGr"] + 1
            )

        if "TotalBsmtSF" in df.columns and "GrLivArea" in df.columns:
            df_enhanced["TotalSF"] = (
                df_enhanced["TotalBsmtSF"] + df_enhanced["GrLivArea"]
            )

        # Polynomial features for key variables
        numerical_cols = self.config.numerical_features
        for col in numerical_cols[:3]:  # Limit to avoid feature explosion
            if col in df_enhanced.columns:
                df_enhanced[f"{col}_squared"] = df_enhanced[col] ** 2
                df_enhanced[f"{col}_log"] = np.log1p(df_enhanced[col].clip(lower=0))

        return df_enhanced

    def _create_categorical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create advanced categorical features"""
        df_enhanced = df.copy()

        # Feature interactions
        if "Neighborhood" in df.columns and "HouseStyle" in df.columns:
            df_enhanced["Neighborhood_HouseStyle"] = (
                df_enhanced["Neighborhood"].astype(str)
                + "_"
                + df_enhanced["HouseStyle"].astype(str)
            )

        # Binning numerical features into categories
        if "YearBuilt" in df.columns:
            df_enhanced["HouseAge"] = 2024 - df_enhanced["YearBuilt"]
            df_enhanced["AgeCategory"] = pd.cut(
                df_enhanced["HouseAge"],
                bins=[0, 10, 30, 50, 100],
                labels=["New", "Modern", "Mature", "Old"],
            )

        return df_enhanced

    def fit(self, X: pd.DataFrame, y: pd.Series = None):
        """Fit the feature engineering pipeline"""
        logger.info("Fitting feature engineering pipeline")

        # Create enhanced features
        X_enhanced = self._create_numerical_features(X)
        X_enhanced = self._create_categorical_features(X_enhanced)

        # Update feature lists with new features
        numerical_features = [
            col
            for col in X_enhanced.columns
            if X_enhanced[col].dtype in ["int64", "float64"]
        ]
        categorical_features = [
            col for col in X_enhanced.columns if X_enhanced[col].dtype == "object"
        ]

        # Create preprocessing pipelines
        self.numerical_transformer = Pipeline([("scaler", StandardScaler())])

        self.categorical_transformer = Pipeline(
            [("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]
        )

        # Combine transformers
        self.preprocessor = ColumnTransformer(
            [
                ("num", self.numerical_transformer, numerical_features),
                ("cat", self.categorical_transformer, categorical_features),
            ]
        )

        # Fit preprocessor
        X_processed = self.preprocessor.fit_transform(X_enhanced)

        # Feature selection (if target provided)
        if y is not None:
            self.feature_selector = SelectKBest(
                score_func=f_regression,
                k=min(self.config.feature_selection_k, X_processed.shape[1]),
            )
            self.feature_selector.fit(X_processed, y)

        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Transform features using fitted pipeline"""
        # Create enhanced features
        X_enhanced = self._create_numerical_features(X)
        X_enhanced = self._create_categorical_features(X_enhanced)

        # Apply preprocessing
        X_processed = self.preprocessor.transform(X_enhanced)

        # Apply feature selection
        if self.feature_selector is not None:
            X_processed = self.feature_selector.transform(X_processed)

        return X_processed

    def get_feature_names(self) -> List[str]:
        """Get names of output features"""
        if self.preprocessor is None:
            return []

        # Get feature names from transformers
        num_features = self.preprocessor.named_transformers_[
            "num"
        ].get_feature_names_out()
        cat_features = self.preprocessor.named_transformers_[
            "cat"
        ].get_feature_names_out()

        all_features = list(num_features) + list(cat_features)

        if self.feature_selector is not None:
            selected_indices = self.feature_selector.get_support()
            all_features = [
                feat for i, feat in enumerate(all_features) if selected_indices[i]
            ]

        return all_features


class FeaturePipeline:
    """Complete feature engineering pipeline with MLflow tracking"""

    def __init__(self, config: FeatureConfig):
        self.config = config
        self.feature_engineer = AdvancedFeatureEngineer(config)

    def process_features(
        self, train_df: pd.DataFrame, test_df: pd.DataFrame = None
    ) -> Tuple[np.ndarray, np.ndarray, pd.Series]:
        """Process features for training and testing"""

        with mlflow.start_run(nested=True, run_name="feature_engineering"):
            logger.info("Starting feature engineering process")

            # Separate features and target
            X_train = train_df.drop(columns=[self.config.target_column])
            y_train = train_df[self.config.target_column]

            # Log original data info
            mlflow.log_param("original_features", X_train.shape[1])
            mlflow.log_param("training_samples", X_train.shape[0])

            # Fit and transform training data
            self.feature_engineer.fit(X_train, y_train)
            X_train_processed = self.feature_engineer.transform(X_train)

            # Transform test data if provided
            X_test_processed = None
            if test_df is not None:
                X_test = test_df.drop(
                    columns=[self.config.target_column], errors="ignore"
                )
                X_test_processed = self.feature_engineer.transform(X_test)
                mlflow.log_param("test_samples", X_test.shape[0])

            # Log feature engineering results
            feature_names = self.feature_engineer.get_feature_names()
            mlflow.log_param("final_features", len(feature_names))
            mlflow.log_param("feature_selection_k", self.config.feature_selection_k)

            # Log feature importance if available
            if self.feature_engineer.feature_selector is not None:
                feature_scores = self.feature_engineer.feature_selector.scores_
                top_features = sorted(
                    zip(feature_names, feature_scores), key=lambda x: x[1], reverse=True
                )[:10]

                for i, (feat, score) in enumerate(top_features):
                    mlflow.log_metric(f"top_feature_{i+1}_score", score)

            # Save feature engineering pipeline
            mlflow.sklearn.log_model(
                self.feature_engineer,
                "feature_pipeline",
                registered_model_name="feature_engineering_pipeline",
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
    # Example configuration for house prices
    config = FeatureConfig(
        numerical_features=["LotArea", "YearBuilt", "TotalBsmtSF", "GrLivArea"],
        categorical_features=["Neighborhood", "HouseStyle", "ExterQual"],
        target_column="SalePrice",
        feature_selection_k=50,
    )

    # Load sample data (replace with actual data loading)
    # train_df = pd.read_csv('data/train.csv')
    # test_df = pd.read_csv('data/test.csv')

    pipeline = FeaturePipeline(config)
    # X_train, X_test, y_train = pipeline.process_features(train_df, test_df)
