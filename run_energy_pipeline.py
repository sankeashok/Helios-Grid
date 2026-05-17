"""
Energy Consumption MLOps Pipeline Runner
Complete end-to-end pipeline for energy consumption prediction
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Import our modules
from src.data.energy_ingestion import EnergyConsumptionIngestion, EnergyDatasetConfig
from src.features.energy_feature_engineering import (
    EnergyFeatureConfig,
    EnergyFeaturePipeline,
)
from src.training.energy_model_training import (
    EnergyEnsembleTrainer,
    EnergyModelConfig,
    EnergyModelTrainer,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EnergyMLOpsPipeline:
    """Complete MLOps pipeline for energy consumption prediction"""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.results = {}

    def _load_config(self, config_path: str) -> dict:
        """Load pipeline configuration"""
        default_config = {
            "data": {
                "dataset_name": "robikscube/hourly-energy-consumption",
                "validation_rules": {
                    "missing_threshold": 0.05,
                    "min_records": 5000,
                    "date_range_years": 3,
                },
            },
            "features": {
                "target_column": "energy_consumption",
                "create_cyclical_features": True,
                "create_lag_features": True,
                "lag_periods": [1, 2, 3, 6, 12, 24, 48, 168],
                "rolling_windows": [6, 12, 24, 48, 168],
                "feature_selection_method": "mutual_info",
                "max_features": 50,
                "scaling_method": "robust",
            },
            "training": {
                "model_type": "lightgbm",
                "cv_folds": 5,
                "n_trials": 100,
                "target_transform": "log",
                "use_time_series_cv": True,
                "ensemble_models": ["lightgbm", "xgboost", "random_forest"],
            },
            "deployment": {
                "model_name": "energy_consumption_model",
                "register_model": True,
                "create_endpoint": False,
            },
        }

        if config_path and os.path.exists(config_path):
            with open(config_path, "r") as f:
                user_config = json.load(f)
            # Merge configs
            for section, values in user_config.items():
                if section in default_config:
                    default_config[section].update(values)
                else:
                    default_config[section] = values

        return default_config

    def run_data_ingestion(self) -> dict:
        """Run data ingestion pipeline"""
        logger.info("=" * 60)
        logger.info("STEP 1: DATA INGESTION")
        logger.info("=" * 60)

        try:
            # Configure data ingestion
            data_config = EnergyDatasetConfig(
                dataset_name=self.config["data"]["dataset_name"],
                validation_rules=self.config["data"]["validation_rules"],
            )

            # Run ingestion
            ingestion = EnergyConsumptionIngestion(data_config)
            result = ingestion.process_energy_pipeline()

            self.results["data_ingestion"] = result

            logger.info("✅ Data ingestion completed successfully")
            logger.info(f"   📊 Dataset: {result['dataset_name']}")
            logger.info(f"   📈 Records: {result['total_rows']:,}")
            logger.info(f"   🎯 Target: {result['target_column']}")
            logger.info(
                f"   📅 Date Range: {result['date_range']['start']} to {result['date_range']['end']}"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Data ingestion failed: {e}")
            raise

    def run_feature_engineering(self) -> dict:
        """Run feature engineering pipeline"""
        logger.info("=" * 60)
        logger.info("STEP 2: FEATURE ENGINEERING")
        logger.info("=" * 60)

        try:
            # Load training data
            train_df = pd.read_csv("data/processed/train_energy.csv")
            test_df = pd.read_csv("data/processed/test_energy.csv")

            # Configure feature engineering
            feature_config = EnergyFeatureConfig(
                target_column=self.config["features"]["target_column"],
                create_cyclical_features=self.config["features"][
                    "create_cyclical_features"
                ],
                create_lag_features=self.config["features"]["create_lag_features"],
                lag_periods=self.config["features"]["lag_periods"],
                rolling_windows=self.config["features"]["rolling_windows"],
                feature_selection_method=self.config["features"][
                    "feature_selection_method"
                ],
                max_features=self.config["features"]["max_features"],
                scaling_method=self.config["features"]["scaling_method"],
            )

            # Run feature engineering
            pipeline = EnergyFeaturePipeline(feature_config)
            X_train, X_test, y_train = pipeline.process_features(train_df, test_df)

            # Save processed features
            X_train.to_csv("data/processed/X_train_energy.csv", index=False)
            y_train.to_csv("data/processed/y_train_energy.csv", index=False)
            if X_test is not None:
                X_test.to_csv("data/processed/X_test_energy.csv", index=False)

            # Save pipeline
            pipeline.save_pipeline("models/energy_feature_pipeline.pkl")

            result = {
                "train_shape": X_train.shape,
                "test_shape": X_test.shape if X_test is not None else None,
                "target_shape": y_train.shape,
                "feature_names": list(X_train.columns),
                "pipeline_saved": "models/energy_feature_pipeline.pkl",
            }

            self.results["feature_engineering"] = result

            logger.info("✅ Feature engineering completed successfully")
            logger.info(f"   🔧 Training features: {X_train.shape}")
            logger.info(
                f"   🔧 Test features: {X_test.shape if X_test is not None else 'None'}"
            )
            logger.info(f"   🎯 Target shape: {y_train.shape}")
            logger.info(f"   💾 Pipeline saved: models/energy_feature_pipeline.pkl")

            return result

        except Exception as e:
            logger.error(f"❌ Feature engineering failed: {e}")
            raise

    def run_model_training(self) -> dict:
        """Run model training pipeline"""
        logger.info("=" * 60)
        logger.info("STEP 3: MODEL TRAINING")
        logger.info("=" * 60)

        try:
            # Load processed features
            X_train = pd.read_csv("data/processed/X_train_energy.csv")
            y_train = pd.read_csv("data/processed/y_train_energy.csv").iloc[:, 0]

            # Split for validation
            split_idx = int(0.8 * len(X_train))
            X_train_split = X_train[:split_idx]
            y_train_split = y_train[:split_idx]
            X_val = X_train[split_idx:]
            y_val = y_train[split_idx:]

            training_results = {}

            # Single model training
            if self.config["training"]["model_type"] != "ensemble":
                model_config = EnergyModelConfig(
                    model_type=self.config["training"]["model_type"],
                    cv_folds=self.config["training"]["cv_folds"],
                    n_trials=self.config["training"]["n_trials"],
                    target_transform=self.config["training"]["target_transform"],
                    use_time_series_cv=self.config["training"]["use_time_series_cv"],
                )

                trainer = EnergyModelTrainer(model_config)
                result = trainer.train_energy_model(
                    X_train_split, y_train_split, X_val, y_val
                )

                training_results["single_model"] = {
                    "model_type": self.config["training"]["model_type"],
                    "cv_rmse": result["cv_rmse"],
                    "validation_metrics": result["validation_metrics"],
                    "best_params": result["best_params"],
                }

                # Register model if configured
                if self.config["deployment"]["register_model"]:
                    model_version = trainer.register_model(
                        self.config["deployment"]["model_name"],
                        f"Energy consumption {self.config['training']['model_type']} model",
                    )
                    training_results["single_model"][
                        "registered_version"
                    ] = model_version

                # Save model
                import joblib

                joblib.dump(result, "models/energy_model_complete.pkl")

                logger.info("✅ Single model training completed")
                logger.info(f"   🤖 Model: {self.config['training']['model_type']}")
                logger.info(f"   📊 CV RMSE: {result['cv_rmse']:.4f}")
                logger.info(
                    f"   📈 Val RMSE: {result['validation_metrics'].get('rmse', 'N/A')}"
                )

            # Ensemble training
            else:
                ensemble_configs = []
                for model_type in self.config["training"]["ensemble_models"]:
                    config = EnergyModelConfig(
                        model_type=model_type,
                        cv_folds=self.config["training"]["cv_folds"],
                        n_trials=max(
                            50,
                            self.config["training"]["n_trials"]
                            // len(self.config["training"]["ensemble_models"]),
                        ),
                        target_transform=self.config["training"]["target_transform"],
                        use_time_series_cv=self.config["training"][
                            "use_time_series_cv"
                        ],
                    )
                    ensemble_configs.append(config)

                ensemble_trainer = EnergyEnsembleTrainer(ensemble_configs)
                ensemble_result = ensemble_trainer.train_ensemble(
                    X_train_split, y_train_split, X_val, y_val
                )

                training_results["ensemble"] = {
                    "models": [config.model_type for config in ensemble_configs],
                    "weights": ensemble_result["weights"].tolist(),
                    "ensemble_metrics": ensemble_result["ensemble_metrics"],
                }

                # Save ensemble
                import joblib

                joblib.dump(ensemble_result, "models/energy_ensemble_complete.pkl")

                logger.info("✅ Ensemble training completed")
                logger.info(
                    f"   🤖 Models: {[config.model_type for config in ensemble_configs]}"
                )
                logger.info(f"   ⚖️ Weights: {ensemble_result['weights']}")
                logger.info(
                    f"   📊 Ensemble RMSE: {ensemble_result['ensemble_metrics']['rmse']:.4f}"
                )

            self.results["model_training"] = training_results
            return training_results

        except Exception as e:
            logger.error(f"❌ Model training failed: {e}")
            raise

    def run_model_evaluation(self) -> dict:
        """Run comprehensive model evaluation"""
        logger.info("=" * 60)
        logger.info("STEP 4: MODEL EVALUATION")
        logger.info("=" * 60)

        try:
            # Load test data
            X_test = pd.read_csv("data/processed/X_test_energy.csv")

            # Load trained model
            import joblib

            if os.path.exists("models/energy_model_complete.pkl"):
                model_result = joblib.load("models/energy_model_complete.pkl")
                trainer = EnergyModelTrainer(EnergyModelConfig(model_type="lightgbm"))
                trainer.best_model = model_result["model"]
                trainer.target_transformer = model_result["target_transformer"]
                trainer.inverse_transformer = model_result["inverse_transformer"]

                # Make predictions
                test_predictions = trainer.predict_energy(X_test)

            elif os.path.exists("models/energy_ensemble_complete.pkl"):
                ensemble_result = joblib.load("models/energy_ensemble_complete.pkl")
                ensemble_trainer = EnergyEnsembleTrainer([])
                ensemble_trainer.trained_models = ensemble_result["models"]
                ensemble_trainer.ensemble_weights = ensemble_result["weights"]

                # Make predictions
                test_predictions = ensemble_trainer.predict_ensemble(X_test)

            else:
                raise FileNotFoundError("No trained model found")

            # Save predictions
            predictions_df = pd.DataFrame(
                {
                    "predictions": test_predictions,
                    "timestamp": pd.date_range(
                        start="2023-01-01", periods=len(test_predictions), freq="H"
                    ),
                }
            )
            predictions_df.to_csv(
                "data/processed/test_predictions_energy.csv", index=False
            )

            evaluation_results = {
                "predictions_saved": "data/processed/test_predictions_energy.csv",
                "prediction_stats": {
                    "mean": float(np.mean(test_predictions)),
                    "std": float(np.std(test_predictions)),
                    "min": float(np.min(test_predictions)),
                    "max": float(np.max(test_predictions)),
                },
            }

            self.results["model_evaluation"] = evaluation_results

            logger.info("✅ Model evaluation completed")
            logger.info(f"   📊 Predictions: {len(test_predictions):,}")
            logger.info(f"   📈 Mean prediction: {np.mean(test_predictions):.2f}")
            logger.info(f"   📉 Std prediction: {np.std(test_predictions):.2f}")

            return evaluation_results

        except Exception as e:
            logger.error(f"❌ Model evaluation failed: {e}")
            raise

    def generate_report(self) -> dict:
        """Generate comprehensive pipeline report"""
        logger.info("=" * 60)
        logger.info("PIPELINE REPORT")
        logger.info("=" * 60)

        report = {
            "pipeline_timestamp": datetime.now().isoformat(),
            "pipeline_config": self.config,
            "results": self.results,
            "status": "completed",
        }

        # Save report
        os.makedirs("reports", exist_ok=True)
        report_path = f"reports/energy_mlops_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info("📋 PIPELINE SUMMARY:")
        logger.info(
            f"   ✅ Data Ingestion: {self.results.get('data_ingestion', {}).get('total_rows', 'N/A')} records"
        )
        logger.info(
            f"   ✅ Feature Engineering: {self.results.get('feature_engineering', {}).get('train_shape', 'N/A')} features"
        )
        logger.info(
            f"   ✅ Model Training: {list(self.results.get('model_training', {}).keys())}"
        )
        logger.info(
            f"   ✅ Model Evaluation: {self.results.get('model_evaluation', {}).get('predictions_saved', 'N/A')}"
        )
        logger.info(f"   📄 Report saved: {report_path}")

        return report

    def run_complete_pipeline(self):
        """Run the complete MLOps pipeline"""
        logger.info("🚀 Starting Energy Consumption MLOps Pipeline")
        logger.info(f"⏰ Start time: {datetime.now()}")

        try:
            start_time = datetime.now()

            # Run pipeline steps
            self.run_data_ingestion()
            self.run_feature_engineering()
            self.run_model_training()
            self.run_model_evaluation()

            # Generate report
            report = self.generate_report()

            end_time = datetime.now()
            duration = end_time - start_time

            logger.info("=" * 60)
            logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info(f"⏱️  Total duration: {duration}")
            logger.info(f"📊 Final report: {report}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"💥 Pipeline failed: {e}")
            raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Energy Consumption MLOps Pipeline")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument(
        "--step",
        type=str,
        choices=["data", "features", "training", "evaluation", "all"],
        default="all",
        help="Pipeline step to run",
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = EnergyMLOpsPipeline(args.config)

    # Run specified step(s)
    if args.step == "data":
        pipeline.run_data_ingestion()
    elif args.step == "features":
        pipeline.run_feature_engineering()
    elif args.step == "training":
        pipeline.run_model_training()
    elif args.step == "evaluation":
        pipeline.run_model_evaluation()
    else:
        pipeline.run_complete_pipeline()


if __name__ == "__main__":
    main()
