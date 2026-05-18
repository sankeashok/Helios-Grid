"""
DagsHub Integration for Helios-Grid MLOps
Enhanced model tracking with DagsHub platform
"""

import os
import logging
import json
from typing import Dict, Any, Optional
import mlflow
import dagshub
import pandas as pd
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HeliosGridDagsHubIntegration:
    """DagsHub integration for enhanced MLOps tracking"""
    
    def __init__(self, 
                 repo_owner: str = "sankeashok", 
                 repo_name: str = "Helios-Grid",
                 dagshub_token: Optional[str] = None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.dagshub_token = dagshub_token or os.getenv("DAGSHUB_TOKEN")
        self.setup_dagshub()
    
    def setup_dagshub(self):
        """Setup DagsHub integration"""
        try:
            # Initialize DagsHub
            dagshub.init(
                repo_owner=self.repo_owner,
                repo_name=self.repo_name,
                mlflow=True
            )
            
            # Set MLflow tracking URI to DagsHub
            dagshub_uri = f"https://dagshub.com/{self.repo_owner}/{self.repo_name}.mlflow"
            mlflow.set_tracking_uri(dagshub_uri)
            
            # Set experiment
            experiment_name = "helios-grid-production"
            try:
                mlflow.create_experiment(experiment_name)
            except:
                pass  # Experiment already exists
            
            mlflow.set_experiment(experiment_name)
            
            logger.info(f"✅ DagsHub integration initialized")
            logger.info(f"📊 MLflow URI: {dagshub_uri}")
            
        except Exception as e:
            logger.warning(f"⚠️ DagsHub setup failed, falling back to local MLflow: {e}")
            # Fallback to local MLflow
            mlflow.set_tracking_uri("file:./mlruns")
            mlflow.set_experiment("helios-grid-local")
    
    def log_model_training(self, 
                          model, 
                          model_type: str,
                          metrics: Dict[str, float],
                          parameters: Dict[str, Any],
                          dataset_info: Dict[str, Any]) -> str:
        """Log model training to DagsHub"""
        
        with mlflow.start_run(run_name=f"{model_type}_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            
            # Log parameters
            mlflow.log_params(parameters)
            mlflow.log_param("model_type", model_type)
            mlflow.log_param("training_date", datetime.now().isoformat())
            
            # Log dataset information
            for key, value in dataset_info.items():
                mlflow.log_param(f"dataset_{key}", value)
            
            # Log metrics
            mlflow.log_metrics(metrics)
            
            # Log model
            mlflow.sklearn.log_model(
                model, 
                "model",
                registered_model_name=f"helios_grid_{model_type}"
            )
            
            # Log additional artifacts
            model_info = {
                "model_type": model_type,
                "training_timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "parameters": parameters,
                "dataset_info": dataset_info
            }
            
            # Save and log model info
            with open("model_info.json", "w") as f:
                json.dump(model_info, f, indent=2)
            mlflow.log_artifact("model_info.json")
            
            # Log feature importance if available
            if hasattr(model, 'feature_importances_'):
                feature_names = dataset_info.get('feature_names', [])
                if feature_names:
                    importance_df = pd.DataFrame({
                        'feature': feature_names,
                        'importance': model.feature_importances_
                    }).sort_values('importance', ascending=False)
                    
                    importance_df.to_csv("feature_importance.csv", index=False)
                    mlflow.log_artifact("feature_importance.csv")
            
            run_id = mlflow.active_run().info.run_id
            logger.info(f"✅ Model logged to DagsHub with run_id: {run_id}")
            
            return run_id
    
    def log_prediction_batch(self, 
                           predictions: list,
                           inputs: list,
                           model_version: str,
                           processing_time: float):
        """Log prediction batch for monitoring"""
        
        with mlflow.start_run(run_name=f"prediction_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            
            # Log batch metrics
            mlflow.log_metrics({
                "batch_size": len(predictions),
                "avg_prediction": np.mean(predictions),
                "std_prediction": np.std(predictions),
                "min_prediction": np.min(predictions),
                "max_prediction": np.max(predictions),
                "processing_time_ms": processing_time
            })
            
            # Log parameters
            mlflow.log_params({
                "model_version": model_version,
                "prediction_type": "batch",
                "timestamp": datetime.now().isoformat()
            })
            
            # Create and log prediction summary
            prediction_summary = pd.DataFrame({
                'prediction': predictions,
                'input_hash': [hash(str(inp)) for inp in inputs]
            })
            
            prediction_summary.to_csv("prediction_batch.csv", index=False)
            mlflow.log_artifact("prediction_batch.csv")
    
    def log_system_metrics(self, 
                          api_metrics: Dict[str, float],
                          model_metrics: Dict[str, float]):
        """Log system performance metrics"""
        
        with mlflow.start_run(run_name=f"system_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            
            # Log API performance
            for metric, value in api_metrics.items():
                mlflow.log_metric(f"api_{metric}", value)
            
            # Log model performance
            for metric, value in model_metrics.items():
                mlflow.log_metric(f"model_{metric}", value)
            
            # Log timestamp
            mlflow.log_param("metrics_timestamp", datetime.now().isoformat())
    
    def compare_models(self, experiment_name: str = "helios-grid-production"):
        """Compare models in DagsHub experiment"""
        
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if not experiment:
                logger.warning(f"Experiment {experiment_name} not found")
                return None
            
            runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
            
            if runs.empty:
                logger.warning("No runs found in experiment")
                return None
            
            # Filter training runs (exclude prediction/metrics runs)
            training_runs = runs[runs['tags.mlflow.runName'].str.contains('training', na=False)]
            
            if training_runs.empty:
                logger.warning("No training runs found")
                return None
            
            # Sort by test R² score
            if 'metrics.test_r2' in training_runs.columns:
                best_runs = training_runs.nlargest(5, 'metrics.test_r2')
            else:
                best_runs = training_runs.head(5)
            
            logger.info("🏆 Top 5 Model Runs:")
            for idx, run in best_runs.iterrows():
                model_type = run.get('params.model_type', 'unknown')
                test_r2 = run.get('metrics.test_r2', 'N/A')
                test_rmse = run.get('metrics.test_rmse', 'N/A')
                run_id = run['run_id']
                
                logger.info(f"   {model_type:15} | R²: {test_r2:6} | RMSE: {test_rmse:8} | ID: {run_id[:8]}")
            
            return best_runs
            
        except Exception as e:
            logger.error(f"❌ Model comparison failed: {e}")
            return None
    
    def get_production_model_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current production model"""
        
        try:
            # Get latest model version
            client = mlflow.tracking.MlflowClient()
            
            # Try to get registered models
            try:
                models = client.search_registered_models()
                if models:
                    latest_model = models[0]  # Get first registered model
                    latest_version = client.get_latest_versions(
                        latest_model.name, 
                        stages=["Production", "Staging", "None"]
                    )[0]
                    
                    return {
                        "model_name": latest_model.name,
                        "version": latest_version.version,
                        "stage": latest_version.current_stage,
                        "run_id": latest_version.run_id,
                        "creation_timestamp": latest_version.creation_timestamp
                    }
            except:
                pass
            
            # Fallback: get latest run
            experiment = mlflow.get_experiment_by_name("helios-grid-production")
            if experiment:
                runs = mlflow.search_runs(
                    experiment_ids=[experiment.experiment_id],
                    filter_string="tags.mlflow.runName LIKE '%training%'",
                    order_by=["start_time DESC"],
                    max_results=1
                )
                
                if not runs.empty:
                    latest_run = runs.iloc[0]
                    return {
                        "run_id": latest_run['run_id'],
                        "model_type": latest_run.get('params.model_type', 'unknown'),
                        "test_r2": latest_run.get('metrics.test_r2', 'N/A'),
                        "test_rmse": latest_run.get('metrics.test_rmse', 'N/A'),
                        "start_time": latest_run['start_time']
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get production model info: {e}")
            return None


def setup_dagshub_credentials():
    """Setup DagsHub credentials"""
    
    print("🔧 DagsHub Setup Instructions:")
    print("=" * 50)
    print("1. Go to https://dagshub.com")
    print("2. Sign up/Login with your GitHub account")
    print("3. Create a new repository or connect existing one")
    print("4. Go to Settings > Access Tokens")
    print("5. Create a new token with MLflow permissions")
    print("6. Set environment variable:")
    print("   export DAGSHUB_TOKEN=your_token_here")
    print()
    print("📋 Repository Configuration:")
    print(f"   Owner: sankeashok")
    print(f"   Repo: Helios-Grid")
    print(f"   MLflow URI: https://dagshub.com/sankeashok/Helios-Grid.mlflow")
    print()
    
    # Check if token is already set
    token = os.getenv("DAGSHUB_TOKEN")
    if token:
        print("✅ DAGSHUB_TOKEN is already set!")
        return True
    else:
        print("⚠️ DAGSHUB_TOKEN not found in environment variables")
        print("   You can still use local MLflow tracking")
        return False


def main():
    """Main function to test DagsHub integration"""
    
    print("🚀 Helios-Grid DagsHub Integration")
    print("=" * 40)
    
    # Setup credentials
    setup_dagshub_credentials()
    
    # Initialize integration
    dagshub_integration = HeliosGridDagsHubIntegration()
    
    # Test model comparison
    print("\n📊 Comparing existing models...")
    best_models = dagshub_integration.compare_models()
    
    # Get production model info
    print("\n🎯 Production model information...")
    prod_info = dagshub_integration.get_production_model_info()
    if prod_info:
        print("✅ Production model found:")
        for key, value in prod_info.items():
            print(f"   {key}: {value}")
    else:
        print("⚠️ No production model found. Run training first.")
    
    print("\n🎉 DagsHub integration ready!")
    print("📊 Access your experiments at:")
    print(f"   https://dagshub.com/sankeashok/Helios-Grid")


if __name__ == "__main__":
    main()