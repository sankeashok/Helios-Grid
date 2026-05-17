"""
Model Training Pipeline with Azure ML Integration
Handles model training, hyperparameter tuning, and registration with MLflow
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from typing import Dict
from typing import List
from typing import Tuple

import joblib
import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from azureml.core import Experiment
from azureml.core import Run
from azureml.core import Workspace
from azureml.core.model import Model
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import cross_val_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for model training"""

    model_type: str  # 'xgboost', 'lightgbm', 'random_forest', 'ensemble'
    cv_folds: int = 5
    n_trials: int = 100
    test_size: float = 0.2
    random_state: int = 42
    early_stopping_rounds: int = 50


class ModelTrainer:
    """Production-grade model training with hyperparameter optimization"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.best_model = None
        self.best_params = None
        self.best_score = None
        self.workspace = self._setup_azure_ml()

    def _setup_azure_ml(self) -> Workspace:
        """Setup Azure ML workspace connection"""
        try:
            ws = Workspace.from_config()
            logger.info(f"Connected to workspace: {ws.name}")
            return ws
        except Exception as e:
            logger.warning(f"Could not connect to Azure ML workspace: {e}")
            return None

    def _get_model_and_params(self, trial=None) -> Tuple[Any, Dict]:
        """Get model instance and parameter space for optimization"""

        if self.config.model_type == "xgboost":
            if trial:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
                    "max_depth": trial.suggest_int("max_depth", 3, 10),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float(
                        "colsample_bytree", 0.6, 1.0
                    ),
                    "reg_alpha": trial.suggest_float("reg_alpha", 0, 10),
                    "reg_lambda": trial.suggest_float("reg_lambda", 0, 10),
                    "random_state": self.config.random_state,
                }
            else:
                params = {
                    "n_estimators": 500,
                    "max_depth": 6,
                    "learning_rate": 0.1,
                    "random_state": self.config.random_state,
                }
            return xgb.XGBRegressor(**params), params

        elif self.config.model_type == "lightgbm":
            if trial:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
                    "max_depth": trial.suggest_int("max_depth", 3, 10),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                    "num_leaves": trial.suggest_int("num_leaves", 10, 300),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float(
                        "colsample_bytree", 0.6, 1.0
                    ),
                    "reg_alpha": trial.suggest_float("reg_alpha", 0, 10),
                    "reg_lambda": trial.suggest_float("reg_lambda", 0, 10),
                    "random_state": self.config.random_state,
                    "verbose": -1,
                }
            else:
                params = {
                    "n_estimators": 500,
                    "max_depth": 6,
                    "learning_rate": 0.1,
                    "random_state": self.config.random_state,
                    "verbose": -1,
                }
            return lgb.LGBMRegressor(**params), params

        elif self.config.model_type == "random_forest":
            if trial:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 500),
                    "max_depth": trial.suggest_int("max_depth", 5, 20),
                    "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                    "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
                    "max_features": trial.suggest_categorical(
                        "max_features", ["sqrt", "log2", None]
                    ),
                    "random_state": self.config.random_state,
                }
            else:
                params = {
                    "n_estimators": 200,
                    "max_depth": 10,
                    "random_state": self.config.random_state,
                }
            return RandomForestRegressor(**params), params

        else:
            raise ValueError(f"Unsupported model type: {self.config.model_type}")

    def _objective(self, trial, X_train, y_train) -> float:
        """Optuna objective function for hyperparameter optimization"""
        model, params = self._get_model_and_params(trial)

        # Cross-validation
        cv_scores = cross_val_score(
            model,
            X_train,
            y_train,
            cv=self.config.cv_folds,
            scoring="neg_mean_squared_error",
            n_jobs=-1,
        )

        return -cv_scores.mean()  # Optuna minimizes

    def train_model(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray = None,
        y_val: np.ndarray = None,
    ) -> Dict[str, Any]:
        """Train model with hyperparameter optimization"""

        with mlflow.start_run(run_name=f"training_{self.config.model_type}"):
            logger.info(f"Starting {self.config.model_type} training with optimization")

            # Log configuration
            mlflow.log_params(
                {
                    "model_type": self.config.model_type,
                    "cv_folds": self.config.cv_folds,
                    "n_trials": self.config.n_trials,
                    "training_samples": X_train.shape[0],
                    "features": X_train.shape[1],
                }
            )

            # Hyperparameter optimization
            study = optuna.create_study(direction="minimize")
            study.optimize(
                lambda trial: self._objective(trial, X_train, y_train),
                n_trials=self.config.n_trials,
                show_progress_bar=True,
            )

            # Get best parameters
            self.best_params = study.best_params
            self.best_score = study.best_value

            logger.info(f"Best CV RMSE: {np.sqrt(self.best_score):.4f}")
            logger.info(f"Best parameters: {self.best_params}")

            # Train final model with best parameters
            self.best_model, _ = self._get_model_and_params()
            self.best_model.set_params(**self.best_params)
            self.best_model.fit(X_train, y_train)

            # Validation metrics
            metrics = {}
            if X_val is not None and y_val is not None:
                y_pred = self.best_model.predict(X_val)
                metrics = {
                    "val_rmse": np.sqrt(mean_squared_error(y_val, y_pred)),
                    "val_mae": mean_absolute_error(y_val, y_pred),
                    "val_r2": r2_score(y_val, y_pred),
                }

                # Log validation metrics
                for metric, value in metrics.items():
                    mlflow.log_metric(metric, value)

            # Log best parameters and CV score
            mlflow.log_params(self.best_params)
            mlflow.log_metric("cv_rmse", np.sqrt(self.best_score))

            # Log model
            if self.config.model_type == "xgboost":
                mlflow.xgboost.log_model(self.best_model, "model")
            elif self.config.model_type == "lightgbm":
                mlflow.lightgbm.log_model(self.best_model, "model")
            else:
                mlflow.sklearn.log_model(self.best_model, "model")

            # Feature importance
            if hasattr(self.best_model, "feature_importances_"):
                importance_dict = {
                    f"feature_{i}": imp
                    for i, imp in enumerate(self.best_model.feature_importances_)
                }
                mlflow.log_metrics(importance_dict)

            return {
                "model": self.best_model,
                "best_params": self.best_params,
                "cv_rmse": np.sqrt(self.best_score),
                "validation_metrics": metrics,
            }

    def register_model(self, model_name: str, description: str = None) -> str:
        """Register model in Azure ML Model Registry"""
        if not self.workspace:
            logger.warning(
                "Azure ML workspace not available, skipping model registration"
            )
            return None

        try:
            # Save model locally first
            model_path = f"models/{model_name}.pkl"
            os.makedirs("models", exist_ok=True)
            joblib.dump(self.best_model, model_path)

            # Register in Azure ML
            model = Model.register(
                workspace=self.workspace,
                model_path=model_path,
                model_name=model_name,
                description=description or f"Trained {self.config.model_type} model",
                tags={
                    "model_type": self.config.model_type,
                    "cv_rmse": str(np.sqrt(self.best_score)),
                    "framework": "scikit-learn",
                },
            )

            logger.info(f"Model registered: {model.name} (version {model.version})")
            return f"{model.name}:{model.version}"

        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            return None


class EnsembleTrainer:
    """Ensemble model trainer combining multiple algorithms"""

    def __init__(self, models_config: List[ModelConfig]):
        self.models_config = models_config
        self.trained_models = []
        self.ensemble_weights = None

    def train_ensemble(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
    ) -> Dict[str, Any]:
        """Train ensemble of models"""

        with mlflow.start_run(run_name="ensemble_training"):
            logger.info("Training ensemble of models")

            # Train individual models
            val_predictions = []

            for i, config in enumerate(self.models_config):
                trainer = ModelTrainer(config)
                result = trainer.train_model(X_train, y_train, X_val, y_val)

                self.trained_models.append(result["model"])

                # Get validation predictions
                val_pred = result["model"].predict(X_val)
                val_predictions.append(val_pred)

                mlflow.log_metric(f"model_{i}_cv_rmse", result["cv_rmse"])

            # Optimize ensemble weights
            val_predictions = np.column_stack(val_predictions)
            self.ensemble_weights = self._optimize_weights(val_predictions, y_val)

            # Calculate ensemble metrics
            ensemble_pred = np.average(
                val_predictions, weights=self.ensemble_weights, axis=1
            )
            ensemble_rmse = np.sqrt(mean_squared_error(y_val, ensemble_pred))
            ensemble_r2 = r2_score(y_val, ensemble_pred)

            mlflow.log_metric("ensemble_rmse", ensemble_rmse)
            mlflow.log_metric("ensemble_r2", ensemble_r2)
            mlflow.log_params(
                {f"weight_{i}": w for i, w in enumerate(self.ensemble_weights)}
            )

            logger.info(f"Ensemble RMSE: {ensemble_rmse:.4f}")

            return {
                "models": self.trained_models,
                "weights": self.ensemble_weights,
                "ensemble_rmse": ensemble_rmse,
                "ensemble_r2": ensemble_r2,
            }

    def _optimize_weights(
        self, predictions: np.ndarray, y_true: np.ndarray
    ) -> np.ndarray:
        """Optimize ensemble weights using Optuna"""

        def objective(trial):
            weights = [
                trial.suggest_float(f"weight_{i}", 0, 1)
                for i in range(predictions.shape[1])
            ]
            weights = np.array(weights)
            weights = weights / weights.sum()  # Normalize

            ensemble_pred = np.average(predictions, weights=weights, axis=1)
            return mean_squared_error(y_true, ensemble_pred)

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=200)

        weights = np.array(
            [study.best_params[f"weight_{i}"] for i in range(predictions.shape[1])]
        )
        return weights / weights.sum()

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make ensemble predictions"""
        predictions = np.column_stack(
            [model.predict(X) for model in self.trained_models]
        )
        return np.average(predictions, weights=self.ensemble_weights, axis=1)


# Example usage
if __name__ == "__main__":
    # Single model training
    config = ModelConfig(model_type="xgboost", cv_folds=5, n_trials=50)

    trainer = ModelTrainer(config)

    # Load your data here
    # X_train, y_train, X_val, y_val = load_data()
    # result = trainer.train_model(X_train, y_train, X_val, y_val)
    # trainer.register_model("house_price_model_v1")
