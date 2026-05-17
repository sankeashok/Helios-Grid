"""
Energy Consumption Model Training Pipeline
Specialized for time series energy prediction with multiple algorithms
"""

import os
import logging
from typing import Dict, Any, Tuple, List, Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    mean_absolute_percentage_error,
)
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
import xgboost as xgb
import lightgbm as lgb
from lightgbm import LGBMRegressor
import optuna
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import mlflow.lightgbm
from azureml.core import Workspace, Experiment, Run
from azureml.core.model import Model
import joblib
from dataclasses import dataclass
import json
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EnergyModelConfig:
    """Configuration for energy consumption model training"""

    model_type: str  # 'xgboost', 'lightgbm', 'random_forest', 'ensemble', 'lstm'
    cv_folds: int = 5
    n_trials: int = 100
    test_size: float = 0.2
    random_state: int = 42
    early_stopping_rounds: int = 50

    # Time series specific
    use_time_series_cv: bool = True
    forecast_horizon: int = 24  # Hours to forecast ahead

    # Energy specific parameters
    target_transform: str = "log"  # 'none', 'log', 'sqrt'
    handle_seasonality: bool = True
    handle_trend: bool = True


class EnergyModelTrainer:
    """Specialized model trainer for energy consumption prediction"""

    def __init__(self, config: EnergyModelConfig):
        self.config = config
        self.best_model = None
        self.best_params = None
        self.best_score = None
        self.workspace = self._setup_azure_ml()
        self.target_transformer = None

    def _setup_azure_ml(self) -> Optional[Workspace]:
        """Setup Azure ML workspace connection"""
        try:
            ws = Workspace.from_config()
            logger.info(f"Connected to workspace: {ws.name}")
            return ws
        except Exception as e:
            logger.warning(f"Could not connect to Azure ML workspace: {e}")
            return None

    def _get_model_and_params(self, trial=None) -> Tuple[Any, Dict]:
        """Get model instance and parameter space for energy consumption"""

        if self.config.model_type == "xgboost":
            if trial:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 2000),
                    "max_depth": trial.suggest_int("max_depth", 3, 12),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float(
                        "colsample_bytree", 0.6, 1.0
                    ),
                    "reg_alpha": trial.suggest_float("reg_alpha", 0, 10),
                    "reg_lambda": trial.suggest_float("reg_lambda", 0, 10),
                    "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                    "random_state": self.config.random_state,
                    "n_jobs": -1,
                }
            else:
                params = {
                    "n_estimators": 1000,
                    "max_depth": 8,
                    "learning_rate": 0.1,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "random_state": self.config.random_state,
                    "n_jobs": -1,
                }
            return xgb.XGBRegressor(**params), params

        elif self.config.model_type == "lightgbm":
            if trial:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 2000),
                    "max_depth": trial.suggest_int("max_depth", 3, 12),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                    "num_leaves": trial.suggest_int("num_leaves", 10, 500),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "colsample_bytree": trial.suggest_float(
                        "colsample_bytree", 0.6, 1.0
                    ),
                    "reg_alpha": trial.suggest_float("reg_alpha", 0, 10),
                    "reg_lambda": trial.suggest_float("reg_lambda", 0, 10),
                    "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
                    "random_state": self.config.random_state,
                    "verbose": -1,
                    "n_jobs": -1,
                }
            else:
                params = {
                    "n_estimators": 1000,
                    "max_depth": 8,
                    "learning_rate": 0.1,
                    "num_leaves": 100,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "random_state": self.config.random_state,
                    "verbose": -1,
                    "n_jobs": -1,
                }
            return LGBMRegressor(**params), params

        elif self.config.model_type == "random_forest":
            if trial:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
                    "max_depth": trial.suggest_int("max_depth", 5, 25),
                    "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                    "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
                    "max_features": trial.suggest_categorical(
                        "max_features", ["sqrt", "log2", 0.8]
                    ),
                    "random_state": self.config.random_state,
                    "n_jobs": -1,
                }
            else:
                params = {
                    "n_estimators": 500,
                    "max_depth": 15,
                    "min_samples_split": 5,
                    "min_samples_leaf": 2,
                    "max_features": "sqrt",
                    "random_state": self.config.random_state,
                    "n_jobs": -1,
                }
            return RandomForestRegressor(**params), params

        elif self.config.model_type == "gradient_boosting":
            if trial:
                params = {
                    "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
                    "max_depth": trial.suggest_int("max_depth", 3, 10),
                    "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                    "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                    "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                    "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
                    "random_state": self.config.random_state,
                }
            else:
                params = {
                    "n_estimators": 500,
                    "max_depth": 6,
                    "learning_rate": 0.1,
                    "subsample": 0.8,
                    "random_state": self.config.random_state,
                }
            return GradientBoostingRegressor(**params), params

        else:
            raise ValueError(f"Unsupported model type: {self.config.model_type}")

    def _setup_target_transformer(self, y: pd.Series):
        """Setup target transformation for energy consumption"""
        if self.config.target_transform == "log":
            # Ensure positive values for log transform
            min_val = y.min()
            if min_val <= 0:
                self.target_transformer = lambda x: np.log1p(x - min_val + 1)
                self.inverse_transformer = lambda x: np.expm1(x) + min_val - 1
            else:
                self.target_transformer = np.log1p
                self.inverse_transformer = np.expm1
        elif self.config.target_transform == "sqrt":
            min_val = y.min()
            if min_val < 0:
                self.target_transformer = lambda x: np.sqrt(x - min_val)
                self.inverse_transformer = lambda x: x**2 + min_val
            else:
                self.target_transformer = np.sqrt
                self.inverse_transformer = lambda x: x**2
        else:
            self.target_transformer = lambda x: x
            self.inverse_transformer = lambda x: x

    def _get_cv_strategy(self, X: pd.DataFrame):
        """Get cross-validation strategy for time series"""
        if self.config.use_time_series_cv:
            return TimeSeriesSplit(n_splits=self.config.cv_folds)
        else:
            from sklearn.model_selection import KFold

            return KFold(
                n_splits=self.config.cv_folds,
                shuffle=True,
                random_state=self.config.random_state,
            )

    def _objective(self, trial, X_train, y_train) -> float:
        """Optuna objective function for hyperparameter optimization"""
        model, params = self._get_model_and_params(trial)

        # Time series cross-validation
        cv_strategy = self._get_cv_strategy(X_train)

        try:
            cv_scores = cross_val_score(
                model,
                X_train,
                y_train,
                cv=cv_strategy,
                scoring="neg_mean_squared_error",
                n_jobs=1,  # Avoid nested parallelism
            )
            return -cv_scores.mean()
        except Exception as e:
            logger.warning(f"Trial failed: {e}")
            return float("inf")

    def train_energy_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame = None,
        y_val: pd.Series = None,
    ) -> Dict[str, Any]:
        """Train energy consumption model with specialized optimization"""

        with mlflow.start_run(run_name=f"energy_training_{self.config.model_type}"):
            logger.info(
                f"Starting {self.config.model_type} training for energy consumption"
            )

            # Setup target transformation
            self._setup_target_transformer(y_train)
            y_train_transformed = self.target_transformer(y_train)

            # Log configuration
            mlflow.log_params(
                {
                    "model_type": self.config.model_type,
                    "cv_folds": self.config.cv_folds,
                    "n_trials": self.config.n_trials,
                    "training_samples": X_train.shape[0],
                    "features": X_train.shape[1],
                    "target_transform": self.config.target_transform,
                    "use_time_series_cv": self.config.use_time_series_cv,
                }
            )

            # Hyperparameter optimization
            study = optuna.create_study(direction="minimize")
            study.optimize(
                lambda trial: self._objective(trial, X_train, y_train_transformed),
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

            # Train with early stopping if supported
            if (
                hasattr(self.best_model, "fit")
                and "early_stopping_rounds" in self.best_model.get_params()
            ):
                if X_val is not None and y_val is not None:
                    y_val_transformed = self.target_transformer(y_val)
                    self.best_model.fit(
                        X_train,
                        y_train_transformed,
                        eval_set=[(X_val, y_val_transformed)],
                        early_stopping_rounds=self.config.early_stopping_rounds,
                        verbose=False,
                    )
                else:
                    self.best_model.fit(X_train, y_train_transformed)
            else:
                self.best_model.fit(X_train, y_train_transformed)

            # Validation metrics
            metrics = {}
            if X_val is not None and y_val is not None:
                y_pred_transformed = self.best_model.predict(X_val)
                y_pred = self.inverse_transformer(y_pred_transformed)

                metrics = self._calculate_energy_metrics(y_val, y_pred)

                # Log validation metrics
                for metric, value in metrics.items():
                    mlflow.log_metric(f"val_{metric}", value)

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

            # Feature importance for tree-based models
            if hasattr(self.best_model, "feature_importances_"):
                importance_dict = dict(
                    zip(X_train.columns, self.best_model.feature_importances_)
                )

                # Log top 20 feature importances
                top_features = sorted(
                    importance_dict.items(), key=lambda x: x[1], reverse=True
                )[:20]
                for i, (feat, imp) in enumerate(top_features):
                    mlflow.log_metric(f"feature_importance_{i+1}", imp)
                    mlflow.log_param(f"top_feature_{i+1}", feat)

            return {
                "model": self.best_model,
                "best_params": self.best_params,
                "cv_rmse": np.sqrt(self.best_score),
                "validation_metrics": metrics,
                "target_transformer": self.target_transformer,
                "inverse_transformer": self.inverse_transformer,
            }

    def _calculate_energy_metrics(
        self, y_true: pd.Series, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Calculate energy-specific evaluation metrics"""
        metrics = {
            "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
            "mae": mean_absolute_error(y_true, y_pred),
            "mape": mean_absolute_percentage_error(y_true, y_pred) * 100,
            "r2": r2_score(y_true, y_pred),
        }

        # Energy-specific metrics
        # Peak hour accuracy (assuming hour information is available)
        try:
            # This would require datetime information - simplified for now
            metrics["normalized_rmse"] = metrics["rmse"] / y_true.mean()
            metrics["normalized_mae"] = metrics["mae"] / y_true.mean()
        except:
            pass

        return metrics

    def predict_energy(self, X: pd.DataFrame) -> np.ndarray:
        """Make energy consumption predictions"""
        if self.best_model is None:
            raise ValueError("Model not trained yet")

        y_pred_transformed = self.best_model.predict(X)
        return self.inverse_transformer(y_pred_transformed)

    def register_model(self, model_name: str, description: str = None) -> Optional[str]:
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

            # Save model with transformers
            model_package = {
                "model": self.best_model,
                "target_transformer": self.target_transformer,
                "inverse_transformer": self.inverse_transformer,
                "config": self.config,
                "best_params": self.best_params,
            }

            joblib.dump(model_package, model_path)

            # Register in Azure ML
            model = Model.register(
                workspace=self.workspace,
                model_path=model_path,
                model_name=model_name,
                description=description
                or f"Energy consumption {self.config.model_type} model",
                tags={
                    "model_type": self.config.model_type,
                    "cv_rmse": str(np.sqrt(self.best_score)),
                    "framework": "scikit-learn",
                    "domain": "energy_consumption",
                    "target_transform": self.config.target_transform,
                },
            )

            logger.info(f"Model registered: {model.name} (version {model.version})")
            return f"{model.name}:{model.version}"

        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            return None


class EnergyEnsembleTrainer:
    """Ensemble trainer for energy consumption models"""

    def __init__(self, models_config: List[EnergyModelConfig]):
        self.models_config = models_config
        self.trained_models = []
        self.ensemble_weights = None
        self.target_transformer = None
        self.inverse_transformer = None

    def train_ensemble(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> Dict[str, Any]:
        """Train ensemble of energy consumption models"""

        with mlflow.start_run(run_name="energy_ensemble_training"):
            logger.info("Training ensemble of energy consumption models")

            # Train individual models
            val_predictions = []
            model_results = []

            for i, config in enumerate(self.models_config):
                logger.info(
                    f"Training model {i+1}/{len(self.models_config)}: {config.model_type}"
                )

                trainer = EnergyModelTrainer(config)
                result = trainer.train_energy_model(X_train, y_train, X_val, y_val)

                self.trained_models.append(
                    {
                        "model": result["model"],
                        "target_transformer": result["target_transformer"],
                        "inverse_transformer": result["inverse_transformer"],
                    }
                )

                model_results.append(result)

                # Get validation predictions
                val_pred = trainer.predict_energy(X_val)
                val_predictions.append(val_pred)

                mlflow.log_metric(
                    f"model_{i}_{config.model_type}_cv_rmse", result["cv_rmse"]
                )

            # Optimize ensemble weights
            val_predictions = np.column_stack(val_predictions)
            self.ensemble_weights = self._optimize_ensemble_weights(
                val_predictions, y_val
            )

            # Calculate ensemble metrics
            ensemble_pred = np.average(
                val_predictions, weights=self.ensemble_weights, axis=1
            )
            ensemble_metrics = self._calculate_ensemble_metrics(y_val, ensemble_pred)

            # Log ensemble results
            for metric, value in ensemble_metrics.items():
                mlflow.log_metric(f"ensemble_{metric}", value)

            for i, weight in enumerate(self.ensemble_weights):
                mlflow.log_param(f"ensemble_weight_{i}", weight)

            logger.info(f"Ensemble RMSE: {ensemble_metrics['rmse']:.4f}")

            return {
                "models": self.trained_models,
                "weights": self.ensemble_weights,
                "ensemble_metrics": ensemble_metrics,
                "individual_results": model_results,
            }

    def _optimize_ensemble_weights(
        self, predictions: np.ndarray, y_true: pd.Series
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

    def _calculate_ensemble_metrics(
        self, y_true: pd.Series, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Calculate ensemble performance metrics"""
        return {
            "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
            "mae": mean_absolute_error(y_true, y_pred),
            "mape": mean_absolute_percentage_error(y_true, y_pred) * 100,
            "r2": r2_score(y_true, y_pred),
        }

    def predict_ensemble(self, X: pd.DataFrame) -> np.ndarray:
        """Make ensemble predictions"""
        predictions = []

        for model_info in self.trained_models:
            model = model_info["model"]
            inverse_transformer = model_info["inverse_transformer"]

            pred_transformed = model.predict(X)
            pred = inverse_transformer(pred_transformed)
            predictions.append(pred)

        predictions = np.column_stack(predictions)
        return np.average(predictions, weights=self.ensemble_weights, axis=1)


# Example usage
if __name__ == "__main__":
    try:
        # Load processed features
        X_train = pd.read_csv("data/processed/X_train_energy.csv")
        y_train = pd.read_csv("data/processed/y_train_energy.csv").iloc[:, 0]
        X_test = pd.read_csv("data/processed/X_test_energy.csv")

        # Split training data for validation
        split_idx = int(0.8 * len(X_train))
        X_train_split = X_train[:split_idx]
        y_train_split = y_train[:split_idx]
        X_val = X_train[split_idx:]
        y_val = y_train[split_idx:]

        # Single model training
        config = EnergyModelConfig(
            model_type="lightgbm",
            cv_folds=5,
            n_trials=50,
            target_transform="log",
            use_time_series_cv=True,
        )

        trainer = EnergyModelTrainer(config)
        result = trainer.train_energy_model(X_train_split, y_train_split, X_val, y_val)

        print(f"Model training completed:")
        print(f"CV RMSE: {result['cv_rmse']:.4f}")
        print(f"Validation metrics: {result['validation_metrics']}")

        # Register model
        model_version = trainer.register_model("energy_consumption_model_v1")
        print(f"Model registered: {model_version}")

        # Save model locally
        joblib.dump(result, "models/energy_model_complete.pkl")

        # Make predictions on test set
        test_predictions = trainer.predict_energy(X_test)

        # Save predictions
        pd.DataFrame({"predictions": test_predictions}).to_csv(
            "data/processed/test_predictions_energy.csv", index=False
        )

        print("Training and prediction completed successfully!")

    except FileNotFoundError:
        print(
            "Please run energy_feature_engineering.py first to create processed features"
        )
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure all preprocessing steps have been completed")
