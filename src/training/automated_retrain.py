"""
Helios-Grid Automated Retraining and Statistical Drift Detection Pipeline
Monitors serving inputs, performs statistical tests, and promotional gating.
"""

import os
import sys
import json
import logging
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Tuple
from scipy.stats import ks_2samp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add workspace to path just in case
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# MLflow imports
try:
    import mlflow
    import mlflow.sklearn
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("⚠️ MLflow not available. Setups will run locally without remote logging.")

class HeliosGridRetrainer:
    """Enterprise Statistical Drift Detector and Automated Model Retrainer"""

    def __init__(self, experiment_name: str = "helios-grid-production"):
        self.experiment_name = experiment_name
        self.baseline_path_x = "data/features.csv"
        self.baseline_path_y = "data/target.csv"
        self.serving_path = "data/serving_logs.csv"
        self.model_path = "models/helios_grid_production_model.pkl"
        self.setup_mlflow()

    def setup_mlflow(self):
        """Setup MLflow tracking uri"""
        if not MLFLOW_AVAILABLE:
            return
        try:
            # Re-use project-configured DagsHub tracking or fallback to local
            if not mlflow.get_tracking_uri().startswith("http"):
                mlflow.set_tracking_uri("file:./mlruns")
            mlflow.set_experiment(self.experiment_name)
        except Exception as e:
            logger.warning(f"⚠️ MLflow setup warning: {e}")

    def detect_drift(self, alpha: float = 0.05) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform statistical Kolmogorov-Smirnov test to detect data drift between
        baseline training features and recent real-world serving logs.
        """
        logger.info("🔬 Running statistical data drift detection...")
        
        # Check baseline features
        if not os.path.exists(self.baseline_path_x):
            logger.warning("⚠️ Baseline features not found in data/. Generating baseline...")
            self.generate_baseline_data()

        # Load baseline
        df_base = pd.read_csv(self.baseline_path_x)
        
        # Load serving logs
        if not os.path.exists(self.serving_path):
            logger.info("ℹ️ No serving logs found yet. Initializing serving logs with baseline profile.")
            # Create a simple placeholder logs
            df_base.head(100).to_csv(self.serving_path, index=False)
            df_serving = df_base.head(100)
        else:
            try:
                df_serving = pd.read_csv(self.serving_path)
            except Exception as e:
                logger.error(f"❌ Failed to read serving logs: {e}")
                df_serving = df_base.head(100)

        drift_detected = False
        drift_results = {}
        features_to_check = ["temperature", "humidity", "wind_speed", "solar_radiation"]

        # Run KS-Test for numerical features
        for feature in features_to_check:
            if feature in df_base.columns and feature in df_serving.columns:
                stat, p_val = ks_2samp(df_base[feature], df_serving[feature])
                feature_drifted = p_val < alpha
                drift_results[feature] = {
                    "ks_statistic": float(stat),
                    "p_value": float(p_val),
                    "drift_detected": bool(feature_drifted)
                }
                if feature_drifted:
                    drift_detected = True
                    logger.warning(f"🚨 Significant Data Drift detected in '{feature}'! p-value: {p_val:.6f}")
                else:
                    logger.info(f"✅ Feature '{feature}' profile is stable. p-value: {p_val:.6f}")

        return drift_detected, drift_results

    def generate_baseline_data(self):
        """Helper to generate standard baseline if missing"""
        os.makedirs("data", exist_ok=True)
        np.random.seed(42)
        samples = 5000
        df = pd.DataFrame({
            "temperature": np.random.normal(20, 10, samples),
            "humidity": np.random.uniform(30, 90, samples),
            "wind_speed": np.random.exponential(5, samples),
            "solar_radiation": np.random.uniform(0, 1000, samples),
            "hour": np.random.randint(0, 24, samples),
            "day_of_week": np.random.randint(0, 7, samples),
            "month": np.random.randint(1, 13, samples),
            "is_weekend": np.random.randint(0, 2, samples)
        })
        y = 1200 + 40 * np.abs(df["temperature"] - 22) + 200 * np.sin(df["hour"] * np.pi / 12) + np.random.normal(0, 50, samples)
        df.to_csv(self.baseline_path_x, index=False)
        pd.Series(y, name="energy_consumption").to_csv(self.baseline_path_y, index=False)
        logger.info("✅ Baseline datasets generated successfully.")

    def run_retraining(self, force: bool = False, simulated_drift: bool = False) -> Dict[str, Any]:
        """
        Main execution loop:
        1. Run statistical drift tests
        2. If drift exists or force is True, train new candidate model
        3. Evaluate performance against current production model
        4. Promote candidate model if performance exceeds production
        """
        start_time = datetime.now()
        
        # Step 1: Detect Drift
        drift_detected, drift_results = self.detect_drift()
        
        # Simulate drift by shifting serving logs to force retraining for demonstration
        if simulated_drift:
            logger.info("🧪 Simulated Drift flag is ACTIVE. Deliberately shifting serving distribution.")
            # Read serving logs, shift temperature and solar radiation
            if os.path.exists(self.serving_path):
                df_s = pd.read_csv(self.serving_path)
                df_s["temperature"] += 8.0  # Shift temperature distribution up by 8 degrees
                df_s["solar_radiation"] *= 1.25  # Shift solar radiation up by 25%
                df_s.to_csv(self.serving_path, index=False)
                # Re-run drift test
                drift_detected, drift_results = self.detect_drift()

        if not drift_detected and not force:
            logger.info("😴 No statistical drift detected. Skipping automated retraining.")
            return {
                "status": "skipped",
                "message": "Model is stable. Drift not detected.",
                "drift_results": drift_results
            }

        logger.info("⚡ Triggering model retraining pipeline...")

        # Load training baseline data
        X_base = pd.read_csv(self.baseline_path_x)
        y_base = pd.read_csv(self.baseline_path_y).iloc[:, 0]

        # Load serving logs (to represent new environment data)
        X_serving = pd.read_csv(self.serving_path)
        
        # Simulate targets for serving logs with slightly updated parameters
        y_serving = 1200 + 42 * np.abs(X_serving["temperature"] - 22) + 210 * np.sin(X_serving["hour"] * np.pi / 12) + np.random.normal(0, 40, len(X_serving))

        # Combine old training data with newly collected serving data for retraining
        X_combined = pd.concat([X_base, X_serving], ignore_index=True)
        y_combined = pd.concat([y_base, pd.Series(y_serving)], ignore_index=True)

        # Train standard RandomForestRegressor
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import r2_score, mean_squared_error

        X_train, X_val, y_train, y_val = train_test_split(X_combined, y_combined, test_size=0.2, random_state=42)
        
        logger.info(f"🤖 Training fresh RandomForestRegressor candidate model on {len(X_train)} samples...")
        model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)

        # Calculate metrics
        y_pred = model.predict(X_val)
        val_r2 = float(r2_score(y_val, y_pred))
        val_rmse = float(np.sqrt(mean_squared_error(y_val, y_pred)))

        logger.info(f"📊 Candidate Validation Metrics: R² = {val_r2:.4f}, RMSE = {val_rmse:.2f}")

        # Step 3: Perform Promotion Gating against Production Model
        production_promoted = False
        prod_r2 = 0.0

        if os.path.exists(self.model_path):
            try:
                prod_pkg = joblib.load(self.model_path)
                prod_r2 = prod_pkg.get("metrics", {}).get("r2", 0.0)
                logger.info(f"🏆 Production Model R² score: {prod_r2:.4f}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to read production model metrics: {e}")

        # Gate promotion: Promote if R2 improves or if we are forced
        if val_r2 >= prod_r2 or force or not os.path.exists(self.model_path):
            logger.info("🚀 Gating checks passed! Candidate model matches or exceeds Production performance. Promoting model...")
            production_promoted = True
            
            # Serialize the new model
            new_version = f"retrained_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            model_package = {
                "model": model,
                "model_version": new_version,
                "model_type": "random_forest_retrained",
                "feature_names": list(X_base.columns),
                "metrics": {
                    "r2": val_r2,
                    "rmse": val_rmse
                },
                "retrained_at": datetime.now().isoformat()
            }
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(model_package, self.model_path)
            logger.info(f"💾 Saved new production model package: {self.model_path}")
        else:
            logger.info("❌ Candidate performance is inferior to active Production model. Rejecting promotion.")

        # Log training parameters, drift stats, and metrics to MLflow
        if MLFLOW_AVAILABLE:
            try:
                with mlflow.start_run(run_name="automated_retraining"):
                    mlflow.log_params({
                        "retraining_type": "automated_drift_triggered",
                        "drift_detected": str(drift_detected),
                        "promoted_to_production": str(production_promoted),
                        "total_training_samples": len(X_combined)
                    })
                    mlflow.log_metrics({
                        "candidate_r2": val_r2,
                        "candidate_rmse": val_rmse,
                        "production_r2_baseline": prod_r2
                    })
                    # Log KS test p-values
                    for feature, result in drift_results.items():
                        mlflow.log_metric(f"drift_p_value_{feature}", result["p_value"])
                        mlflow.log_metric(f"drift_stat_{feature}", result["ks_statistic"])
                    
                    # Log model if promoted
                    if production_promoted:
                        mlflow.sklearn.log_model(model, "retrained_production_model")
                        logger.info("✅ Retrained model registered with MLflow Tracking.")
            except Exception as e:
                logger.warning(f"⚠️ Failed to log run parameters to MLflow: {e}")

        execution_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "success",
            "message": "Retraining executed successfully." if production_promoted else "Retraining executed; candidate rejected.",
            "drift_detected": drift_detected,
            "promoted": production_promoted,
            "candidate_metrics": {
                "r2": val_r2,
                "rmse": val_rmse
            },
            "drift_results": drift_results,
            "execution_time_seconds": execution_time
        }

def run_automated_retraining(force: bool = False, simulated_drift: bool = False) -> Dict[str, Any]:
    """Module entry point for external calls"""
    retrainer = HeliosGridRetrainer()
    return retrainer.run_retraining(force=force, simulated_drift=simulated_drift)

if __name__ == "__main__":
    logger.info("🚀 Initiating local command line automated retraining check...")
    results = run_automated_retraining(force=True)
    print(json.dumps(results, indent=2))
