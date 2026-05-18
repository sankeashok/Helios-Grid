"""
Helios-Grid MLflow Model Training and Tracking
Complete MLOps pipeline with experiment tracking
"""

import os
import logging
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Tuple

import mlflow
import mlflow.sklearn
from mlflow.models.signature import infer_signature

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HeliosGridMLflowTrainer:
    """MLflow-integrated model trainer for Helios-Grid energy prediction"""

    def __init__(self, experiment_name: str = "helios-grid-energy-prediction"):
        self.experiment_name = experiment_name
        self.setup_mlflow()

    def setup_mlflow(self):
        """Setup MLflow tracking"""
        try:
            # Set tracking URI
            mlflow.set_tracking_uri("file:./mlruns")

            # Create or get experiment
            try:
                experiment_id = mlflow.create_experiment(self.experiment_name)
            except:
                experiment_id = mlflow.get_experiment_by_name(
                    self.experiment_name
                ).experiment_id

            mlflow.set_experiment(self.experiment_name)
            logger.info(f"✅ MLflow experiment set: {self.experiment_name}")

        except Exception as e:
            logger.error(f"❌ MLflow setup failed: {e}")
            raise

    def create_synthetic_dataset(
        self, n_samples: int = 10000
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Create realistic energy consumption dataset"""

        logger.info(f"🏗️ Creating synthetic energy dataset with {n_samples} samples...")

        np.random.seed(42)

        # Generate realistic energy features
        temperature = np.random.normal(20, 15, n_samples)  # Temperature in Celsius
        humidity = np.random.uniform(20, 95, n_samples)  # Humidity percentage
        wind_speed = np.random.exponential(7, n_samples)  # Wind speed in m/s
        solar_radiation = np.random.uniform(0, 1200, n_samples)  # Solar radiation W/m²

        # Time-based features
        hour = np.random.randint(0, 24, n_samples)
        day_of_week = np.random.randint(0, 7, n_samples)
        month = np.random.randint(1, 13, n_samples)
        is_weekend = (day_of_week >= 5).astype(int)

        # Create feature matrix
        X = pd.DataFrame(
            {
                "temperature": temperature,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "solar_radiation": solar_radiation,
                "hour": hour,
                "day_of_week": day_of_week,
                "month": month,
                "is_weekend": is_weekend,
            }
        )

        # Create realistic energy consumption target
        base_consumption = 1200  # Base load in kWh

        # Temperature effect (U-shaped - more energy for extreme temps)
        temp_effect = 80 * np.abs(temperature - 22) / 10

        # Time of day effect (higher during day, peak in evening)
        hour_normalized = hour / 24 * 2 * np.pi
        time_effect = 300 * (0.5 + 0.3 * np.sin(hour_normalized - np.pi / 2)) + 200 * (
            (hour >= 18) & (hour <= 22)
        )

        # Seasonal effect (higher in summer and winter)
        seasonal_effect = 150 * np.abs(month - 6.5) / 6.5

        # Weekend effect (slightly lower consumption)
        weekend_effect = -80 * is_weekend

        # Solar radiation effect (less energy needed when sunny)
        solar_effect = -0.15 * solar_radiation

        # Wind effect (slight cooling effect)
        wind_effect = -5 * wind_speed

        # Humidity effect (affects comfort, thus energy usage)
        humidity_effect = 2 * np.abs(humidity - 50)

        # Combine all effects with realistic noise
        y = (
            base_consumption
            + temp_effect
            + time_effect
            + seasonal_effect
            + weekend_effect
            + solar_effect
            + wind_effect
            + humidity_effect
            + np.random.normal(0, 80, n_samples)
        )

        # Ensure positive values (energy consumption can't be negative)
        y = np.maximum(y, 50)

        logger.info(f"📊 Dataset created:")
        logger.info(f"   Features: {X.shape[1]}")
        logger.info(f"   Samples: {X.shape[0]}")
        logger.info(f"   Energy range: {y.min():.1f} - {y.max():.1f} kWh")
        logger.info(f"   Mean consumption: {y.mean():.1f} kWh")

        return X, pd.Series(y, name="energy_consumption")

    def train_model(
        self,
        model_type: str,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
    ) -> Dict[str, Any]:
        """Train a specific model type with MLflow tracking"""

        with mlflow.start_run(run_name=f"{model_type}_training"):
            logger.info(f"🤖 Training {model_type} model...")

            # Log dataset info
            mlflow.log_params(
                {
                    "model_type": model_type,
                    "train_samples": len(X_train),
                    "test_samples": len(X_test),
                    "features": X_train.shape[1],
                    "feature_names": list(X_train.columns),
                }
            )

            # Initialize model based on type
            if model_type == "random_forest":
                model = RandomForestRegressor(
                    n_estimators=200,
                    max_depth=15,
                    min_samples_split=5,
                    min_samples_leaf=2,
                    max_features="sqrt",
                    random_state=42,
                    n_jobs=-1,
                )
                model_params = {
                    "n_estimators": 200,
                    "max_depth": 15,
                    "min_samples_split": 5,
                    "min_samples_leaf": 2,
                    "max_features": "sqrt",
                }

            elif model_type == "gradient_boosting":
                model = GradientBoostingRegressor(
                    n_estimators=150,
                    max_depth=8,
                    learning_rate=0.1,
                    subsample=0.8,
                    random_state=42,
                )
                model_params = {
                    "n_estimators": 150,
                    "max_depth": 8,
                    "learning_rate": 0.1,
                    "subsample": 0.8,
                }

            elif model_type == "linear_regression":
                model = LinearRegression()
                model_params = {"fit_intercept": True}

            elif model_type == "ridge_regression":
                model = Ridge(alpha=1.0, random_state=42)
                model_params = {"alpha": 1.0}

            else:
                raise ValueError(f"Unsupported model type: {model_type}")

            # Log model parameters
            mlflow.log_params(model_params)

            # Train model
            start_time = datetime.now()
            model.fit(X_train, y_train)
            training_time = (datetime.now() - start_time).total_seconds()

            # Make predictions
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)

            # Calculate metrics
            metrics = {
                "train_rmse": np.sqrt(mean_squared_error(y_train, y_pred_train)),
                "test_rmse": np.sqrt(mean_squared_error(y_test, y_pred_test)),
                "train_mae": mean_absolute_error(y_train, y_pred_train),
                "test_mae": mean_absolute_error(y_test, y_pred_test),
                "train_r2": r2_score(y_train, y_pred_train),
                "test_r2": r2_score(y_test, y_pred_test),
                "training_time_seconds": training_time,
            }

            # Calculate MAPE (Mean Absolute Percentage Error)
            metrics["train_mape"] = (
                np.mean(np.abs((y_train - y_pred_train) / y_train)) * 100
            )
            metrics["test_mape"] = (
                np.mean(np.abs((y_test - y_pred_test) / y_test)) * 100
            )

            # Cross-validation score
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="r2")
            metrics["cv_r2_mean"] = cv_scores.mean()
            metrics["cv_r2_std"] = cv_scores.std()

            # Log all metrics
            mlflow.log_metrics(metrics)

            # Log feature importance if available
            if hasattr(model, "feature_importances_"):
                feature_importance = dict(
                    zip(X_train.columns, model.feature_importances_)
                )

                # Log top 5 feature importances
                sorted_features = sorted(
                    feature_importance.items(), key=lambda x: x[1], reverse=True
                )
                for i, (feature, importance) in enumerate(sorted_features[:5]):
                    mlflow.log_metric(f"feature_importance_{i+1}", importance)
                    mlflow.log_param(f"top_feature_{i+1}", feature)

            # Create model signature
            signature = infer_signature(X_train, y_pred_train)

            # Log model
            mlflow.sklearn.log_model(
                model, "model", signature=signature, input_example=X_train.iloc[:5]
            )

            # Log model artifacts
            model_info = {
                "model_type": model_type,
                "training_date": datetime.now().isoformat(),
                "metrics": metrics,
                "feature_names": list(X_train.columns),
                "model_version": f"{model_type}_v1.0",
            }

            mlflow.log_dict(model_info, "model_info.json")

            logger.info(f"✅ {model_type} training completed:")
            logger.info(f"   Test R²: {metrics['test_r2']:.4f}")
            logger.info(f"   Test RMSE: {metrics['test_rmse']:.2f} kWh")
            logger.info(f"   Test MAE: {metrics['test_mae']:.2f} kWh")

            return {
                "model": model,
                "metrics": metrics,
                "model_info": model_info,
                "run_id": mlflow.active_run().info.run_id,
            }

    def compare_models(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Compare multiple models and select the best one"""

        logger.info("🏆 Starting model comparison experiment...")

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Models to compare
        model_types = [
            "random_forest",
            "gradient_boosting",
            "ridge_regression",
            "linear_regression",
        ]

        results = {}

        # Train each model
        for model_type in model_types:
            try:
                result = self.train_model(model_type, X_train, y_train, X_test, y_test)
                results[model_type] = result
            except Exception as e:
                logger.error(f"❌ Failed to train {model_type}: {e}")

        # Find best model based on test R²
        best_model_type = max(
            results.keys(), key=lambda k: results[k]["metrics"]["test_r2"]
        )
        best_result = results[best_model_type]

        logger.info(f"🏆 Best model: {best_model_type}")
        logger.info(f"   Test R²: {best_result['metrics']['test_r2']:.4f}")
        logger.info(f"   Test RMSE: {best_result['metrics']['test_rmse']:.2f} kWh")

        # Save best model for production
        self.save_production_model(best_result, X_train.columns)

        return {
            "best_model_type": best_model_type,
            "best_result": best_result,
            "all_results": results,
            "comparison_summary": {
                model_type: {
                    "test_r2": result["metrics"]["test_r2"],
                    "test_rmse": result["metrics"]["test_rmse"],
                    "test_mae": result["metrics"]["test_mae"],
                }
                for model_type, result in results.items()
            },
        }

    def save_production_model(self, best_result: Dict[str, Any], feature_names: list):
        """Save the best model for production use"""

        logger.info("💾 Saving production model...")

        # Create model package
        model_package = {
            "model": best_result["model"],
            "target_transformer": lambda x: x,
            "inverse_transformer": lambda x: x,
            "feature_names": list(feature_names),
            "model_type": best_result["model_info"]["model_type"],
            "metrics": best_result["metrics"],
            "model_version": "production_v1.0",
            "training_date": datetime.now().isoformat(),
            "mlflow_run_id": best_result["run_id"],
        }

        # Save model
        os.makedirs("models", exist_ok=True)
        model_path = "models/helios_grid_production_model.pkl"
        joblib.dump(model_package, model_path)

        # Save model info
        model_info_path = "models/model_info.json"
        with open(model_info_path, "w") as f:
            json.dump(best_result["model_info"], f, indent=2)

        logger.info(f"✅ Production model saved:")
        logger.info(f"   Model: {model_path}")
        logger.info(f"   Info: {model_info_path}")
        logger.info(f"   MLflow Run ID: {best_result['run_id']}")


def main():
    """Main training pipeline"""

    logger.info("🚀 Starting Helios-Grid MLflow Training Pipeline...")

    # Initialize trainer
    trainer = HeliosGridMLflowTrainer()

    # Create dataset
    X, y = trainer.create_synthetic_dataset(n_samples=15000)

    # Save dataset for reference
    os.makedirs("data", exist_ok=True)
    X.to_csv("data/features.csv", index=False)
    y.to_csv("data/target.csv", index=False)
    logger.info("📊 Dataset saved to data/ directory")

    # Compare models and select best
    comparison_results = trainer.compare_models(X, y)

    # Print summary
    logger.info("\n🎯 Model Comparison Summary:")
    for model_type, metrics in comparison_results["comparison_summary"].items():
        logger.info(
            f"   {model_type:20} | R²: {metrics['test_r2']:.4f} | RMSE: {metrics['test_rmse']:.2f}"
        )

    logger.info(f"\n🏆 Best Model: {comparison_results['best_model_type']}")
    logger.info("✅ Training pipeline completed!")
    logger.info("\n📊 To view results:")
    logger.info("   1. Run: mlflow ui")
    logger.info("   2. Open: http://localhost:5000")
    logger.info("   3. Start production server: python production_server.py")


if __name__ == "__main__":
    main()
