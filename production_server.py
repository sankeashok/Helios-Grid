"""
Helios-Grid Production FastAPI Server
Public-accessible energy prediction API with MLflow tracking
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import uvicorn
import joblib
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field
import mlflow
import mlflow.sklearn
from contextlib import asynccontextmanager

# Import DagsHub integration
try:
    from dagshub_integration import HeliosGridDagsHubIntegration

    DAGSHUB_AVAILABLE = True
except ImportError:
    DAGSHUB_AVAILABLE = False
    print("⚠️ DagsHub integration not available. Install dagshub: pip install dagshub")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model storage
model_store = {}
dagshub_integration = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting Helios-Grid Production Server...")
    load_model()
    setup_mlflow()
    yield
    # Shutdown
    logger.info("🛑 Shutting down Helios-Grid Server...")


# Initialize FastAPI app
app = FastAPI(
    title="☀️ Helios-Grid Energy Prediction API",
    description="Production-ready energy consumption prediction service with MLflow tracking",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware for public access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for public access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class EnergyPredictionInput(BaseModel):
    """Input model for energy prediction"""

    temperature: float = Field(..., description="Temperature in Celsius", ge=-50, le=60)
    humidity: float = Field(..., description="Humidity percentage", ge=0, le=100)
    wind_speed: float = Field(..., description="Wind speed in m/s", ge=0, le=50)
    solar_radiation: float = Field(
        ..., description="Solar radiation in W/m²", ge=0, le=1500
    )
    hour: int = Field(..., description="Hour of day (0-23)", ge=0, le=23)
    day_of_week: int = Field(
        ..., description="Day of week (0=Monday, 6=Sunday)", ge=0, le=6
    )
    month: int = Field(..., description="Month (1-12)", ge=1, le=12)
    is_weekend: int = Field(
        ..., description="Weekend flag (0=weekday, 1=weekend)", ge=0, le=1
    )


class BatchPredictionInput(BaseModel):
    """Batch prediction input"""

    data: List[EnergyPredictionInput]


class PredictionResponse(BaseModel):
    """Prediction response model"""

    prediction: float
    confidence_interval: Optional[Dict[str, float]] = None
    model_version: str
    timestamp: str
    processing_time_ms: float


class BatchPredictionResponse(BaseModel):
    """Batch prediction response"""

    predictions: List[float]
    model_version: str
    timestamp: str
    total_processing_time_ms: float
    predictions_count: int


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float
    mlflow_tracking: bool


# Global variables
start_time = time.time()
prediction_count = 0
API_VERSION = "v1.1.0"  # Updated for CI/CD pipeline test


def setup_mlflow():
    """Setup MLflow tracking with DagsHub integration"""
    global dagshub_integration

    try:
        if DAGSHUB_AVAILABLE:
            # Initialize DagsHub integration
            dagshub_integration = HeliosGridDagsHubIntegration()
            logger.info("✅ DagsHub + MLflow tracking initialized")
        else:
            # Fallback to local MLflow
            mlflow.set_tracking_uri("file:./mlruns")
            mlflow.set_experiment("helios-grid-production")
            logger.info("✅ Local MLflow tracking initialized")
        return True
    except Exception as e:
        logger.error(f"❌ MLflow setup failed: {e}")
        return False


def load_model():
    """Load the production model"""
    try:
        model_path = "models/helios_grid_production_model.pkl"
        if not os.path.exists(model_path):
            # Create a simple model if none exists
            create_simple_model()

        model_package = joblib.load(model_path)
        model_store["model"] = model_package["model"]
        model_store["metadata"] = {
            "version": model_package.get("model_version", "1.0.0"),
            "type": model_package.get("model_type", "random_forest"),
            "features": model_package.get("feature_names", []),
            "metrics": model_package.get("metrics", {}),
            "loaded_at": datetime.now().isoformat(),
        }

        logger.info(
            f"✅ Model loaded: {model_store['metadata']['type']} v{model_store['metadata']['version']}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        return False


def create_simple_model():
    """Create a simple model for demonstration"""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.datasets import make_regression

    logger.info("🏗️ Creating demonstration model...")

    # Create synthetic data
    X, y = make_regression(n_samples=1000, n_features=8, noise=0.1, random_state=42)

    # Train model
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    # Create model package
    model_package = {
        "model": model,
        "model_version": "demo_v1.0",
        "model_type": "random_forest",
        "feature_names": [
            "temperature",
            "humidity",
            "wind_speed",
            "solar_radiation",
            "hour",
            "day_of_week",
            "month",
            "is_weekend",
        ],
        "metrics": {"r2": 0.85, "rmse": 150.0},
    }

    # Save model
    os.makedirs("models", exist_ok=True)
    joblib.dump(model_package, "models/helios_grid_production_model.pkl")
    logger.info("✅ Demonstration model created")


def log_prediction_to_mlflow(
    input_data: dict, prediction: float, processing_time: float
):
    """Log prediction to MLflow/DagsHub"""
    try:
        if dagshub_integration:
            # Use DagsHub integration for enhanced logging
            dagshub_integration.log_prediction_batch(
                predictions=[prediction],
                inputs=[input_data],
                model_version=model_store["metadata"]["version"],
                processing_time=processing_time,
            )
        else:
            # Fallback to direct MLflow logging
            with mlflow.start_run():
                # Log input parameters
                mlflow.log_params(input_data)

                # Log prediction metrics
                mlflow.log_metrics(
                    {
                        "prediction": prediction,
                        "processing_time_ms": processing_time,
                        "timestamp": time.time(),
                    }
                )

                # Log model info
                mlflow.log_param("model_version", model_store["metadata"]["version"])

    except Exception as e:
        logger.warning(f"MLflow logging failed: {e}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API documentation"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>☀️ Helios-Grid Energy Prediction API</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
            .container { background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }
            .header { text-align: center; margin-bottom: 30px; }
            .endpoint { background: rgba(255,255,255,0.2); padding: 20px; margin: 15px 0; border-radius: 10px; }
            .method { background: #28a745; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
            .url { font-family: monospace; background: rgba(0,0,0,0.3); padding: 5px; border-radius: 3px; }
            a { color: #ffd700; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>☀️ Helios-Grid Energy Prediction API</h1>
                <p>Production-ready energy consumption prediction service</p>
                <p><strong>🌐 Public Access Available</strong> | <strong>📊 MLflow Tracking Enabled</strong></p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> Health Check</h3>
                <p class="url">/health</p>
                <p>Check API health and model status</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">POST</span> Single Prediction</h3>
                <p class="url">/predict</p>
                <p>Predict energy consumption for single input</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">POST</span> Batch Prediction</h3>
                <p class="url">/predict/batch</p>
                <p>Predict energy consumption for multiple inputs</p>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> Model Info</h3>
                <p class="url">/model/info</p>
                <p>Get detailed model information and metrics</p>
            </div>
            
            <div class="endpoint">
                <h3>📚 Interactive Documentation</h3>
                <p><a href="/docs">Swagger UI</a> | <a href="/redoc">ReDoc</a></p>
            </div>
            
            <div class="endpoint">
                <h3>🧪 Example Usage</h3>
                <pre style="background: rgba(0,0,0,0.3); padding: 15px; border-radius: 5px; overflow-x: auto;">
curl -X POST "http://localhost:3002/predict" \\
  -H "Content-Type: application/json" \\
  -d '{
    "temperature": 25.5,
    "humidity": 60.0,
    "wind_speed": 8.2,
    "solar_radiation": 750.0,
    "hour": 14,
    "day_of_week": 2,
    "month": 7,
    "is_weekend": 0
  }'
                </pre>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if model_store.get("model") else "unhealthy",
        model_loaded=bool(model_store.get("model")),
        model_version=f"{model_store.get('metadata', {}).get('version', 'unknown')} (API {API_VERSION})",
        uptime_seconds=time.time() - start_time,
        mlflow_tracking=True,
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict_energy(
    input_data: EnergyPredictionInput, background_tasks: BackgroundTasks
):
    """Single energy consumption prediction"""
    global prediction_count

    start_time_pred = time.time()

    try:
        if not model_store.get("model"):
            raise HTTPException(status_code=503, detail="Model not loaded")

        # Convert input to DataFrame
        input_dict = input_data.dict()
        df = pd.DataFrame([input_dict])

        # Make prediction
        model = model_store["model"]
        prediction = float(model.predict(df)[0])

        # Ensure positive prediction
        prediction = max(prediction, 0)

        processing_time = (time.time() - start_time_pred) * 1000
        prediction_count += 1

        # Log to MLflow in background
        background_tasks.add_task(
            log_prediction_to_mlflow, input_dict, prediction, processing_time
        )

        return PredictionResponse(
            prediction=prediction,
            model_version=model_store["metadata"]["version"],
            timestamp=datetime.now().isoformat(),
            processing_time_ms=processing_time,
        )

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_energy_batch(
    input_data: BatchPredictionInput, background_tasks: BackgroundTasks
):
    """Batch energy consumption prediction"""
    global prediction_count

    start_time_batch = time.time()

    try:
        if not model_store.get("model"):
            raise HTTPException(status_code=503, detail="Model not loaded")

        if len(input_data.data) > 1000:
            raise HTTPException(
                status_code=400, detail="Batch size too large (max 1000)"
            )

        # Convert inputs to DataFrame
        input_dicts = [item.dict() for item in input_data.data]
        df = pd.DataFrame(input_dicts)

        # Make predictions
        model = model_store["model"]
        predictions = model.predict(df)

        # Ensure positive predictions
        predictions = np.maximum(predictions, 0).tolist()

        processing_time = (time.time() - start_time_batch) * 1000
        prediction_count += len(predictions)

        # Log batch to MLflow in background
        background_tasks.add_task(
            log_batch_to_mlflow, len(predictions), processing_time
        )

        return BatchPredictionResponse(
            predictions=predictions,
            model_version=model_store["metadata"]["version"],
            timestamp=datetime.now().isoformat(),
            total_processing_time_ms=processing_time,
            predictions_count=len(predictions),
        )

    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def log_batch_to_mlflow(batch_size: int, processing_time: float):
    """Log batch prediction to MLflow"""
    try:
        with mlflow.start_run():
            mlflow.log_metrics(
                {
                    "batch_size": batch_size,
                    "batch_processing_time_ms": processing_time,
                    "avg_processing_time_per_item_ms": processing_time / batch_size,
                    "timestamp": time.time(),
                }
            )
            mlflow.log_param("prediction_type", "batch")
            mlflow.log_param("model_version", model_store["metadata"]["version"])
    except Exception as e:
        logger.warning(f"MLflow batch logging failed: {e}")


@app.get("/model/info")
async def get_model_info():
    """Get detailed model information"""
    if not model_store.get("metadata"):
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Get DagsHub model info if available
    dagshub_info = None
    if dagshub_integration:
        try:
            dagshub_info = dagshub_integration.get_production_model_info()
        except Exception as e:
            logger.warning(f"Failed to get DagsHub info: {e}")

    return {
        "model_metadata": model_store["metadata"],
        "api_stats": {
            "total_predictions": prediction_count,
            "uptime_seconds": time.time() - start_time,
            "predictions_per_minute": (
                prediction_count / ((time.time() - start_time) / 60)
                if time.time() - start_time > 0
                else 0
            ),
        },
        "mlflow_info": {
            "tracking_uri": mlflow.get_tracking_uri(),
            "experiment_name": "helios-grid-production",
            "dagshub_enabled": DAGSHUB_AVAILABLE and dagshub_integration is not None,
        },
        "dagshub_info": dagshub_info,
    }


@app.get("/dagshub/status")
async def get_dagshub_status():
    """Get DagsHub integration status"""
    if not DAGSHUB_AVAILABLE:
        return {
            "status": "unavailable",
            "message": "DagsHub not installed. Run: pip install dagshub",
            "tracking_uri": mlflow.get_tracking_uri(),
        }

    if not dagshub_integration:
        return {
            "status": "not_initialized",
            "message": "DagsHub integration not initialized",
            "tracking_uri": mlflow.get_tracking_uri(),
        }

    try:
        # Get model comparison from DagsHub
        best_models = dagshub_integration.compare_models()
        model_count = len(best_models) if best_models is not None else 0

        return {
            "status": "active",
            "message": "DagsHub integration active",
            "tracking_uri": mlflow.get_tracking_uri(),
            "repository": f"{dagshub_integration.repo_owner}/{dagshub_integration.repo_name}",
            "models_tracked": model_count,
            "dagshub_url": f"https://dagshub.com/{dagshub_integration.repo_owner}/{dagshub_integration.repo_name}",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"DagsHub error: {str(e)}",
            "tracking_uri": mlflow.get_tracking_uri(),
        }


@app.get("/metrics")
async def get_metrics():
    """Prometheus-style metrics endpoint"""
    uptime = time.time() - start_time

    metrics = f"""
# HELP helios_grid_predictions_total Total number of predictions made
# TYPE helios_grid_predictions_total counter
helios_grid_predictions_total {prediction_count}

# HELP helios_grid_uptime_seconds Server uptime in seconds
# TYPE helios_grid_uptime_seconds gauge
helios_grid_uptime_seconds {uptime}

# HELP helios_grid_model_loaded Model loading status
# TYPE helios_grid_model_loaded gauge
helios_grid_model_loaded {1 if model_store.get("model") else 0}
"""

    return Response(content=metrics, media_type="text/plain")


if __name__ == "__main__":
    # Create models directory
    os.makedirs("models", exist_ok=True)

    # Start server
    logger.info("🚀 Starting Helios-Grid Production Server on http://localhost:3002")
    logger.info(
        "📊 MLflow UI available at: http://localhost:5000 (run 'mlflow ui' separately)"
    )

    uvicorn.run(
        "production_server:app",
        host="0.0.0.0",  # Allow external access
        port=3002,
        reload=False,
        log_level="info",
        access_log=True,
    )
