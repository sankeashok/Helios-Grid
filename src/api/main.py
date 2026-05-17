"""
Production FastAPI Application for ML Model Serving
Includes Azure integration, monitoring, and security features
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Depends, Security, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, validator
import joblib
import mlflow
import mlflow.pyfunc
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.monitor.opentelemetry import configure_azure_monitor
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Azure Monitor (Application Insights)
configure_azure_monitor()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "ml_api_requests_total", "Total API requests", ["method", "endpoint"]
)
REQUEST_DURATION = Histogram("ml_api_request_duration_seconds", "Request duration")
PREDICTION_COUNT = Counter("ml_predictions_total", "Total predictions made")
MODEL_LOAD_TIME = Gauge("ml_model_load_time_seconds", "Model loading time")

# Security
security = HTTPBearer()


class PredictionRequest(BaseModel):
    """Request model for predictions"""

    features: Dict[str, float] = Field(..., description="Feature values for prediction")
    model_version: Optional[str] = Field("latest", description="Model version to use")

    @validator("features")
    def validate_features(cls, v):
        if not v:
            raise ValueError("Features cannot be empty")
        return v


class PredictionResponse(BaseModel):
    """Response model for predictions"""

    prediction: float = Field(..., description="Model prediction")
    model_version: str = Field(..., description="Model version used")
    confidence_interval: Optional[Dict[str, float]] = Field(
        None, description="Prediction confidence interval"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    timestamp: datetime
    model_loaded: bool
    model_version: str


class ModelManager:
    """Manages model loading and predictions with caching"""

    def __init__(self):
        self.model = None
        self.model_version = None
        self.feature_names = None
        self.scaler = None
        self._load_model()

    def _load_model(self):
        """Load model from MLflow or local storage"""
        try:
            start_time = datetime.utcnow()

            # Try loading from MLflow first
            model_name = os.getenv("MODEL_NAME", "house_price_model")
            model_version = os.getenv("MODEL_VERSION", "latest")

            try:
                if model_version == "latest":
                    model_uri = f"models:/{model_name}/Production"
                else:
                    model_uri = f"models:/{model_name}/{model_version}"

                self.model = mlflow.pyfunc.load_model(model_uri)
                self.model_version = model_version
                logger.info(f"Loaded model from MLflow: {model_uri}")

            except Exception as e:
                logger.warning(f"Failed to load from MLflow: {e}")
                # Fallback to local model
                model_path = "models/model.pkl"
                if os.path.exists(model_path):
                    self.model = joblib.load(model_path)
                    self.model_version = "local"
                    logger.info("Loaded local model")
                else:
                    raise FileNotFoundError("No model found")

            # Load feature names and scaler if available
            try:
                self.feature_names = joblib.load("models/feature_names.pkl")
                self.scaler = joblib.load("models/scaler.pkl")
            except FileNotFoundError:
                logger.warning("Feature names or scaler not found")

            load_time = (datetime.utcnow() - start_time).total_seconds()
            MODEL_LOAD_TIME.set(load_time)

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Make prediction with the loaded model"""
        if self.model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")

        try:
            # Convert features to DataFrame
            df = pd.DataFrame([features])

            # Apply scaling if available
            if self.scaler:
                df_scaled = pd.DataFrame(self.scaler.transform(df), columns=df.columns)
            else:
                df_scaled = df

            # Make prediction
            if hasattr(self.model, "predict"):
                prediction = self.model.predict(df_scaled)[0]
            else:
                # MLflow model
                prediction = self.model.predict(df_scaled).iloc[0]

            # Calculate confidence interval (simplified)
            confidence_interval = {
                "lower": float(prediction * 0.9),
                "upper": float(prediction * 1.1),
            }

            PREDICTION_COUNT.inc()

            return {
                "prediction": float(prediction),
                "confidence_interval": confidence_interval,
                "model_version": self.model_version,
            }

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise HTTPException(status_code=400, detail=f"Prediction failed: {str(e)}")


# Initialize model manager
model_manager = ModelManager()

# Create FastAPI app
app = FastAPI(
    title="ML Model API",
    description="Production ML model serving API with Azure integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=["*"]  # Configure appropriately for production
)


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token (implement your authentication logic)"""
    # For demo purposes, accept any token
    # In production, verify against Azure AD or your auth provider
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials


@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Add request processing time to headers"""
    start_time = datetime.utcnow()

    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()

    with REQUEST_DURATION.time():
        response = await call_next(request)

    process_time = (datetime.utcnow() - start_time).total_seconds()
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if model_manager.model else "unhealthy",
        timestamp=datetime.utcnow(),
        model_loaded=model_manager.model is not None,
        model_version=model_manager.model_version or "none",
    )


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return prometheus_client.generate_latest()


@app.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token),
):
    """Make prediction using the loaded model"""
    try:
        result = model_manager.predict(request.features)

        # Log prediction for monitoring (background task)
        background_tasks.add_task(
            log_prediction,
            request.features,
            result["prediction"],
            request.model_version,
        )

        return PredictionResponse(
            prediction=result["prediction"],
            model_version=result["model_version"],
            confidence_interval=result["confidence_interval"],
        )

    except Exception as e:
        logger.error(f"Prediction endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/batch_predict")
async def batch_predict(
    requests: List[PredictionRequest], token: str = Depends(verify_token)
):
    """Batch prediction endpoint"""
    if len(requests) > 100:  # Limit batch size
        raise HTTPException(status_code=400, detail="Batch size too large (max 100)")

    results = []
    for req in requests:
        try:
            result = model_manager.predict(req.features)
            results.append(
                PredictionResponse(
                    prediction=result["prediction"],
                    model_version=result["model_version"],
                    confidence_interval=result["confidence_interval"],
                )
            )
        except Exception as e:
            logger.error(f"Batch prediction error: {e}")
            results.append(None)

    return {"predictions": results}


@app.post("/reload_model")
async def reload_model(token: str = Depends(verify_token)):
    """Reload model (admin endpoint)"""
    try:
        model_manager._load_model()
        return {"status": "success", "message": "Model reloaded successfully"}
    except Exception as e:
        logger.error(f"Model reload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload model")


async def log_prediction(features: Dict, prediction: float, model_version: str):
    """Log prediction for monitoring and drift detection"""
    try:
        # Log to Azure Application Insights or your monitoring system
        logger.info(f"Prediction logged: {prediction} for features: {features}")

        # Here you could also:
        # 1. Store in database for drift monitoring
        # 2. Send to event hub for real-time processing
        # 3. Update model performance metrics

    except Exception as e:
        logger.error(f"Failed to log prediction: {e}")


if __name__ == "__main__":
    # Configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    workers = int(os.getenv("API_WORKERS", 1))

    # Run server
    uvicorn.run(
        "main:app", host=host, port=port, workers=workers, reload=False, access_log=True
    )
