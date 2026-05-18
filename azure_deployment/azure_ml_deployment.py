"""
Azure ML Model Deployment for Helios-Grid Energy Prediction
Production-ready deployment with REST API endpoint
"""

import json
import logging
import os
from typing import Dict, Any, Optional
import joblib
import pandas as pd
import numpy as np
from azureml.core import Workspace, Model, Environment, InferenceConfig
from azureml.core.webservice import AciWebservice, Webservice
from azureml.core.model import InferenceConfig
from azureml.exceptions import WebserviceException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HeliosGridAzureDeployment:
    """Azure ML deployment manager for Helios-Grid energy prediction model"""
    
    def __init__(self, subscription_id: str, resource_group: str, workspace_name: str):
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.workspace_name = workspace_name
        self.workspace = None
        self.model = None
        self.service = None
        self.version = "v1.1.0"  # Updated version for CI/CD test
        
    def connect_workspace(self) -> bool:
        """Connect to Azure ML workspace"""
        try:
            self.workspace = Workspace(
                subscription_id=self.subscription_id,
                resource_group=self.resource_group,
                workspace_name=self.workspace_name
            )
            logger.info(f"Connected to workspace: {self.workspace.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to workspace: {e}")
            return False
    
    def create_workspace_config(self):
        """Create workspace configuration file"""
        config = {
            "subscription_id": self.subscription_id,
            "resource_group": self.resource_group,
            "workspace_name": self.workspace_name
        }
        
        os.makedirs(".azureml", exist_ok=True)
        with open(".azureml/config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        logger.info("Workspace config created at .azureml/config.json")
    
    def register_model(self, model_path: str, model_name: str = "helios-grid-energy-model") -> bool:
        """Register the trained model in Azure ML"""
        try:
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False
            
            self.model = Model.register(
                workspace=self.workspace,
                model_path=model_path,
                model_name=model_name,
                description="Helios-Grid Energy Consumption Prediction Model",
                tags={
                    "framework": "scikit-learn",
                    "type": "regression",
                    "domain": "energy_prediction",
                    "version": "production_v1"
                }
            )
            
            logger.info(f"Model registered: {self.model.name} (version {self.model.version})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            return False
    
    def create_scoring_script(self):
        """Create the scoring script for model inference"""
        scoring_script = '''
import json
import joblib
import pandas as pd
import numpy as np
from azureml.core.model import Model

def init():
    """Initialize the model for scoring"""
    global model, target_transformer, inverse_transformer
    
    try:
        # Get model path
        model_path = Model.get_model_path("helios-grid-energy-model")
        
        # Load the complete model package
        model_package = joblib.load(model_path)
        
        model = model_package["model"]
        target_transformer = model_package.get("target_transformer", lambda x: x)
        inverse_transformer = model_package.get("inverse_transformer", lambda x: x)
        
        print("Model loaded successfully")
        
    except Exception as e:
        print(f"Error loading model: {e}")
        raise

def run(raw_data):
    """Score the model with input data"""
    try:
        # Parse input data
        data = json.loads(raw_data)
        
        # Handle different input formats
        if isinstance(data, dict):
            if "data" in data:
                input_data = data["data"]
            else:
                input_data = [data]
        else:
            input_data = data
        
        # Convert to DataFrame
        df = pd.DataFrame(input_data)
        
        # Ensure required columns exist (basic energy features)
        required_features = [
            "temperature", "humidity", "wind_speed", "solar_radiation",
            "hour", "day_of_week", "month", "is_weekend"
        ]
        
        # Add missing features with default values if needed
        for feature in required_features:
            if feature not in df.columns:
                if feature == "temperature":
                    df[feature] = 20.0  # Default temperature
                elif feature == "humidity":
                    df[feature] = 50.0  # Default humidity
                elif feature == "wind_speed":
                    df[feature] = 5.0   # Default wind speed
                elif feature == "solar_radiation":
                    df[feature] = 500.0 # Default solar radiation
                elif feature == "hour":
                    df[feature] = 12    # Default hour (noon)
                elif feature == "day_of_week":
                    df[feature] = 1     # Default weekday
                elif feature == "month":
                    df[feature] = 6     # Default month (June)
                elif feature == "is_weekend":
                    df[feature] = 0     # Default weekday
        
        # Make predictions
        predictions = model.predict(df)
        
        # Apply inverse transformation if available
        if inverse_transformer:
            predictions = inverse_transformer(predictions)
        
        # Ensure predictions are positive (energy consumption can't be negative)
        predictions = np.maximum(predictions, 0)
        
        # Format response
        result = {
            "predictions": predictions.tolist(),
            "model_version": "production_v1",
            "status": "success"
        }
        
        return json.dumps(result)
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "status": "error"
        }
        return json.dumps(error_result)
'''
        
        with open("azure_deployment/score.py", "w") as f:
            f.write(scoring_script)
        
        logger.info("Scoring script created at azure_deployment/score.py")
    
    def deploy_model(self, 
                    cpu_cores: float = 1.0, 
                    memory_gb: float = 2.0,
                    service_name: str = "helios-grid-api") -> Optional[str]:
        """Deploy model as Azure Container Instance web service"""
        try:
            # Create environment
            env = Environment(name="helios-grid-env")
            conda_deps = {
                "channels": ["conda-forge"],
                "dependencies": [
                    "python=3.9",
                    "pip",
                    {
                        "pip": [
                            "azureml-defaults",
                            "scikit-learn==1.3.0",
                            "pandas==2.0.3",
                            "numpy==1.24.3",
                            "joblib==1.3.1"
                        ]
                    }
                ]
            }
            env.python.conda_dependencies = conda_deps
            
            # Create inference configuration
            inference_config = InferenceConfig(
                entry_script="score.py",
                source_directory="azure_deployment",
                environment=env
            )
            
            # Create deployment configuration
            deployment_config = AciWebservice.deploy_configuration(
                cpu_cores=cpu_cores,
                memory_gb=memory_gb,
                tags={
                    "model": "helios-grid-energy",
                    "framework": "scikit-learn",
                    "type": "energy_prediction"
                },
                description="Helios-Grid Energy Consumption Prediction API",
                enable_app_insights=True,
                auth_enabled=False
            )
            
            # Deploy the service
            logger.info(f"Deploying model as web service: {service_name}")
            self.service = Model.deploy(
                workspace=self.workspace,
                name=service_name,
                models=[self.model],
                inference_config=inference_config,
                deployment_config=deployment_config,
                overwrite=True
            )
            
            # Wait for deployment to complete
            self.service.wait_for_deployment(show_output=True)
            
            if self.service.state == "Healthy":
                scoring_uri = self.service.scoring_uri
                logger.info(f"✅ Model deployed successfully!")
                logger.info(f"🌐 Scoring URI: {scoring_uri}")
                return scoring_uri
            else:
                logger.error(f"❌ Deployment failed. State: {self.service.state}")
                return None
                
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return None


def create_simple_model():
    """Create a simple model for deployment testing"""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.datasets import make_regression
    
    # Create synthetic training data
    X, y = make_regression(n_samples=1000, n_features=8, noise=0.1, random_state=42)
    
    # Train simple model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Create model package
    model_package = {
        "model": model,
        "target_transformer": lambda x: x,
        "inverse_transformer": lambda x: x,
        "feature_names": [
            "temperature", "humidity", "wind_speed", "solar_radiation",
            "hour", "day_of_week", "month", "is_weekend"
        ],
        "model_type": "random_forest"
    }
    
    # Save model
    os.makedirs("models", exist_ok=True)
    model_path = "models/helios_grid_production_model.pkl"
    joblib.dump(model_package, model_path)
    
    logger.info(f"Simple model created and saved to {model_path}")
    return model_path


if __name__ == "__main__":
    # Create a simple model for testing
    model_path = create_simple_model()
    print(f"Model ready for deployment: {model_path}")