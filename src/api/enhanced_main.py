"""
Enterprise FastAPI Application - Staff-Level Engineering Implementation
Integrates all council recommendations: Security, UI, Edge Cases, Performance
"""

import asyncio
import logging
import os

# Import our enterprise modules
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import joblib
import mlflow
import mlflow.pyfunc
import numpy as np
import pandas as pd
import prometheus_client
import uvicorn
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram
from pydantic import BaseModel
from pydantic import Field
from pydantic import validator

sys.path.append(".")
from src.core.enterprise_architecture import BaseMLOpsComponent
from src.core.enterprise_architecture import SystemState
from src.security.enterprise_security import JWTManager
from src.security.enterprise_security import SecurityValidator
from src.security.enterprise_security import require_mfa
from src.security.enterprise_security import require_permission
from src.testing.edge_case_handler import CircuitBreaker
from src.testing.edge_case_handler import EdgeCaseHandler
from src.testing.edge_case_handler import RetryPolicy

# Configure logging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
configure_azure_monitor()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "ml_api_requests_total", "Total API requests", ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram("ml_api_request_duration_seconds", "Request duration")
PREDICTION_COUNT = Counter("ml_predictions_total", "Total predictions made")
MODEL_LOAD_TIME = Gauge("ml_model_load_time_seconds", "Model loading time")
ACTIVE_CONNECTIONS = Gauge("ml_api_active_connections", "Active connections")
ERROR_RATE = Gauge("ml_api_error_rate", "API error rate")

# Security
security = HTTPBearer()


# Pydantic Models with Enhanced Validation
class PredictionRequest(BaseModel):
    """Enhanced request model with comprehensive validation"""

    features: Dict[str, float] = Field(..., description="Feature values for prediction")
    model_version: Optional[str] = Field("latest", description="Model version to use")
    confidence_threshold: Optional[float] = Field(
        0.5, ge=0.0, le=1.0, description="Confidence threshold"
    )
    explain_prediction: Optional[bool] = Field(
        False, description="Include prediction explanation"
    )

    @validator("features")
    def validate_features(cls, v):
        if not v:
            raise ValueError("Features cannot be empty")

        # Check for reasonable feature values
        for key, value in v.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Feature {key} must be numeric")
            if abs(value) > 1e10:  # Prevent extremely large values
                raise ValueError(f"Feature {key} value {value} is too large")

        return v

    @validator("model_version")
    def validate_model_version(cls, v):
        if v and not v.replace(".", "").replace("_", "").isalnum():
            raise ValueError("Invalid model version format")
        return v


class PredictionResponse(BaseModel):
    """Enhanced response model with comprehensive information"""

    prediction: float = Field(..., description="Model prediction")
    confidence: float = Field(..., description="Prediction confidence score")
    model_version: str = Field(..., description="Model version used")
    model_type: str = Field(..., description="Type of model used")
    prediction_id: str = Field(..., description="Unique prediction identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )
    explanation: Optional[Dict[str, Any]] = Field(
        None, description="Prediction explanation"
    )
    warnings: Optional[List[str]] = Field(None, description="Any warnings or notices")


class HealthResponse(BaseModel):
    """Comprehensive health check response"""

    status: str
    timestamp: datetime
    version: str
    environment: str
    system_info: Dict[str, Any]
    dependencies: Dict[str, Dict[str, Any]]
    performance_metrics: Dict[str, float]


class EnterpriseModelManager(BaseMLOpsComponent):
    """Enterprise-grade model management with all council improvements"""

    def __init__(self, component_id: str, config: Dict[str, Any]):
        super().__init__(component_id, config)
        self.model = None
        self.model_version = None
        self.feature_names = None
        self.scaler = None
        self.edge_case_handler = EdgeCaseHandler(config)
        self.circuit_breaker = CircuitBreaker()
        self.retry_policy = RetryPolicy()

    async def initialize(self) -> None:
        """Initialize model manager with comprehensive error handling"""
        try:
            await self._load_model_with_fallback()
            await self.update_state(SystemState.HEALTHY)
            logger.info("Model manager initialized successfully")
        except Exception as e:
            logger.error(f"Model manager initialization failed: {e}")
            await self.update_state(SystemState.CRITICAL)
            raise

    async def _load_model_with_fallback(self):
        """Load model with multiple fallback strategies"""
        start_time = datetime.utcnow()

        try:
            # Primary: Load from MLflow
            model_name = os.getenv("MODEL_NAME", "house_price_model")
            model_version = os.getenv("MODEL_VERSION", "latest")

            if model_version == "latest":
                model_uri = f"models:/{model_name}/Production"
            else:
                model_uri = f"models:/{model_name}/{model_version}"

            self.model = mlflow.pyfunc.load_model(model_uri)
            self.model_version = model_version
            logger.info(f"Loaded model from MLflow: {model_uri}")

        except Exception as mlflow_error:
            logger.warning(f"MLflow model loading failed: {mlflow_error}")

            # Fallback 1: Local model file
            try:
                model_path = "models/model.pkl"
                if os.path.exists(model_path):
                    self.model = joblib.load(model_path)
                    self.model_version = "local"
                    logger.info("Loaded local model as fallback")
                else:
                    raise FileNotFoundError("Local model not found")

            except Exception as local_error:
                logger.warning(f"Local model loading failed: {local_error}")

                # Fallback 2: Simple rule-based model
                await self._initialize_rule_based_model()
                logger.info("Initialized rule-based fallback model")

        # Load supporting artifacts
        try:
            self.feature_names = joblib.load("models/feature_names.pkl")
            self.scaler = joblib.load("models/scaler.pkl")
        except FileNotFoundError:
            logger.warning("Feature names or scaler not found, using defaults")

        load_time = (datetime.utcnow() - start_time).total_seconds()
        MODEL_LOAD_TIME.set(load_time)

    async def _initialize_rule_based_model(self):
        """Initialize simple rule-based model as ultimate fallback"""

        class RuleBasedModel:
            def predict(self, X):
                # Simple rule-based prediction (example for house prices)
                if hasattr(X, "iloc"):
                    # Assume first column is area, second is bedrooms
                    area = X.iloc[:, 0] if len(X.columns) > 0 else pd.Series([1000])
                    bedrooms = X.iloc[:, 1] if len(X.columns) > 1 else pd.Series([3])
                    return area * 100 + bedrooms * 10000  # Simple formula
                else:
                    return np.array([150000])  # Default prediction

        self.model = RuleBasedModel()
        self.model_version = "rule_based_fallback"

    async def predict_with_resilience(
        self, features: Dict[str, float], request_id: str
    ) -> Dict[str, Any]:
        """Make prediction with comprehensive error handling and resilience"""

        if self.model is None:
            raise HTTPException(status_code=503, detail="Model not available")

        start_time = datetime.utcnow()

        try:
            # Input validation and preprocessing
            validated_features = await self._validate_and_preprocess_features(features)

            # Convert to DataFrame for model
            df = pd.DataFrame([validated_features])

            # Apply scaling if available
            if self.scaler:
                try:
                    df_scaled = pd.DataFrame(
                        self.scaler.transform(df), columns=df.columns
                    )
                except Exception as scaling_error:
                    logger.warning(
                        f"Scaling failed: {scaling_error}, using raw features"
                    )
                    df_scaled = df
            else:
                df_scaled = df

            # Make prediction with circuit breaker protection
            prediction = await self.circuit_breaker.call(
                self._execute_prediction, df_scaled
            )

            # Post-process prediction
            processed_result = await self._post_process_prediction(
                prediction, validated_features, request_id
            )

            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            processed_result["processing_time_ms"] = processing_time

            PREDICTION_COUNT.inc()

            return processed_result

        except Exception as e:
            logger.error(f"Prediction error for request {request_id}: {e}")

            # Try fallback prediction
            try:
                fallback_result = (
                    await self.edge_case_handler.handle_model_prediction_failure(
                        self.model_version, features
                    )
                )
                if fallback_result.get("success"):
                    return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback prediction failed: {fallback_error}")

            raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    async def _validate_and_preprocess_features(
        self, features: Dict[str, float]
    ) -> Dict[str, float]:
        """Validate and preprocess input features"""

        # Handle missing features with defaults
        expected_features = self.feature_names or list(features.keys())
        validated_features = {}

        for feature_name in expected_features:
            if feature_name in features:
                value = features[feature_name]

                # Handle edge cases
                if pd.isna(value) or np.isinf(value):
                    logger.warning(
                        f"Invalid value for {feature_name}: {value}, using default"
                    )
                    validated_features[feature_name] = 0.0
                else:
                    validated_features[feature_name] = float(value)
            else:
                logger.warning(f"Missing feature {feature_name}, using default value")
                validated_features[feature_name] = 0.0

        return validated_features

    async def _execute_prediction(self, df_scaled: pd.DataFrame) -> float:
        """Execute model prediction"""
        if hasattr(self.model, "predict"):
            prediction = self.model.predict(df_scaled)
            return (
                float(prediction[0])
                if hasattr(prediction, "__iter__")
                else float(prediction)
            )
        else:
            # MLflow model
            prediction = self.model.predict(df_scaled)
            return (
                float(prediction.iloc[0])
                if hasattr(prediction, "iloc")
                else float(prediction)
            )

    async def _post_process_prediction(
        self, prediction: float, features: Dict[str, float], request_id: str
    ) -> Dict[str, Any]:
        """Post-process prediction with validation and explanation"""

        # Validate prediction range (example for house prices)
        if prediction < 0:
            logger.warning(f"Negative prediction {prediction} for request {request_id}")
            prediction = abs(prediction)

        if prediction > 10_000_000:  # $10M seems unreasonable for most houses
            logger.warning(
                f"Extremely high prediction {prediction} for request {request_id}"
            )
            prediction = min(prediction, 2_000_000)  # Cap at $2M

        # Calculate confidence (simplified)
        confidence = min(0.95, max(0.1, 1.0 - abs(prediction - 200000) / 1000000))

        # Generate explanation (simplified SHAP-like)
        explanation = await self._generate_explanation(features, prediction)

        return {
            "prediction": prediction,
            "confidence": confidence,
            "model_version": self.model_version,
            "model_type": "ensemble" if "ensemble" in self.model_version else "single",
            "prediction_id": request_id,
            "explanation": explanation,
            "warnings": await self._generate_warnings(prediction, features),
        }

    async def _generate_explanation(
        self, features: Dict[str, float], prediction: float
    ) -> Dict[str, Any]:
        """Generate simple feature importance explanation"""

        # Simplified feature importance (would use SHAP in production)
        feature_importance = {}
        total_contribution = 0

        for feature, value in features.items():
            # Simple heuristic for house price features
            if "area" in feature.lower():
                contribution = value * 0.3
            elif "bedroom" in feature.lower():
                contribution = value * 0.2
            elif "bathroom" in feature.lower():
                contribution = value * 0.15
            else:
                contribution = value * 0.1

            feature_importance[feature] = {
                "value": value,
                "contribution": contribution,
                "importance_score": abs(contribution) / max(prediction, 1),
            }
            total_contribution += contribution

        return {
            "feature_importance": feature_importance,
            "base_prediction": prediction - total_contribution,
            "total_contribution": total_contribution,
        }

    async def _generate_warnings(
        self, prediction: float, features: Dict[str, float]
    ) -> List[str]:
        """Generate warnings based on prediction and features"""
        warnings = []

        if prediction > 1_000_000:
            warnings.append("High-value prediction - please verify input features")

        if len(features) < 5:
            warnings.append(
                "Limited features provided - prediction may be less accurate"
            )

        return warnings

    async def health_check(self) -> bool:
        """Comprehensive health check"""
        try:
            if self.model is None:
                return False

            # Test prediction with dummy data
            test_features = {"feature1": 1.0, "feature2": 2.0}
            test_df = pd.DataFrame([test_features])

            if hasattr(self.model, "predict"):
                _ = self.model.predict(test_df)
            else:
                _ = self.model.predict(test_df)

            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down model manager...")
        self.model = None
        await self.update_state(SystemState.MAINTENANCE)


# Initialize components
model_manager = None
security_validator = None
jwt_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global model_manager, security_validator, jwt_manager

    # Startup
    logger.info("Starting up Enterprise MLOps API...")

    try:
        # Initialize security components
        security_config = {
            "max_input_length": 10000,
            "rate_limit_window": 3600,
            "max_requests_per_hour": 1000,
        }
        security_validator = SecurityValidator(security_config)
        jwt_manager = JWTManager(os.getenv("JWT_SECRET_KEY", "your-secret-key"))

        # Initialize model manager
        model_config = {
            "alternative_models": {
                "house_price_model": ["house_price_model_v1", "rule_based_fallback"]
            },
            "max_file_size": 100_000_000,
        }
        model_manager = EnterpriseModelManager("primary_model_manager", model_config)
        await model_manager.initialize()

        logger.info("Enterprise MLOps API startup completed successfully")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Enterprise MLOps API...")
    if model_manager:
        await model_manager.shutdown()
    logger.info("Shutdown completed")


# Create FastAPI app with enterprise configuration
app = FastAPI(
    title="Enterprise MLOps API",
    description="Production-grade ML model serving API with comprehensive security and monitoring",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add enterprise middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["yourdomain.com", "*.yourdomain.com", "localhost", "127.0.0.1"],
)

# Mount static files for UI
app.mount("/static", StaticFiles(directory="src/ui"), name="static")


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Enhanced token verification with comprehensive validation"""
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    try:
        security_context = jwt_manager.validate_token(credentials.credentials)
        if not security_context:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        return security_context
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@app.middleware("http")
async def comprehensive_middleware(request: Request, call_next):
    """Comprehensive middleware with security, monitoring, and error handling"""
    start_time = datetime.utcnow()
    request_id = f"req_{int(start_time.timestamp() * 1000)}"

    # Add request ID to headers
    request.state.request_id = request_id

    # Security validation
    try:
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")

        request_data = {
            "ip_address": client_ip,
            "user_agent": user_agent,
            "path": request.url.path,
            "method": request.method,
        }

        is_valid, error_message = await security_validator.validate_request(
            request_data
        )
        if not is_valid:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Security validation failed",
                    "message": error_message,
                },
            )

    except Exception as security_error:
        logger.error(f"Security middleware error: {security_error}")

    # Process request
    try:
        ACTIVE_CONNECTIONS.inc()

        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["X-Request-ID"] = request_id

        # Record metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()

        REQUEST_DURATION.observe(processing_time)

        return response

    except Exception as e:
        logger.error(f"Request processing error: {e}")
        ERROR_RATE.inc()

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
    finally:
        ACTIVE_CONNECTIONS.dec()


# API Endpoints


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the premium dashboard UI"""
    try:
        with open("src/ui/dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Enterprise MLOps Dashboard</h1><p>Dashboard UI not found</p>"
        )


@app.get("/health", response_model=HealthResponse)
async def comprehensive_health_check():
    """Comprehensive health check with detailed system information"""

    health_status = "healthy"
    dependencies = {}

    # Check model manager
    if model_manager:
        model_healthy = await model_manager.health_check()
        dependencies["model_manager"] = {
            "status": "healthy" if model_healthy else "unhealthy",
            "version": model_manager.model_version or "unknown",
            "state": model_manager.state.value,
        }
        if not model_healthy:
            health_status = "degraded"
    else:
        dependencies["model_manager"] = {"status": "unavailable"}
        health_status = "critical"

    # Check security components
    dependencies["security_validator"] = {
        "status": "healthy" if security_validator else "unavailable"
    }

    # System information
    import psutil

    system_info = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    # Performance metrics
    performance_metrics = {
        "active_connections": ACTIVE_CONNECTIONS._value._value,
        "total_requests": REQUEST_COUNT._value.sum(),
        "error_rate": ERROR_RATE._value._value,
    }

    return HealthResponse(
        status=health_status,
        timestamp=datetime.utcnow(),
        version="2.0.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        system_info=system_info,
        dependencies=dependencies,
        performance_metrics=performance_metrics,
    )


@app.post("/predict", response_model=PredictionResponse)
async def enhanced_predict(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    security_context=Depends(verify_token),
):
    """Enhanced prediction endpoint with comprehensive error handling"""

    request_id = http_request.state.request_id

    try:
        # Make prediction with resilience
        result = await model_manager.predict_with_resilience(
            request.features, request_id
        )

        # Log prediction for monitoring (background task)
        background_tasks.add_task(
            log_prediction_async,
            request.features,
            result["prediction"],
            security_context.user_id,
            request_id,
        )

        return PredictionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction endpoint error: {e}")
        raise HTTPException(
            status_code=500, detail="Prediction service temporarily unavailable"
        )


@app.post("/batch_predict")
async def enhanced_batch_predict(
    requests: List[PredictionRequest], security_context=Depends(verify_token)
):
    """Enhanced batch prediction with parallel processing and error handling"""

    if len(requests) > 100:
        raise HTTPException(status_code=400, detail="Batch size exceeds maximum of 100")

    # Process requests in parallel with semaphore for resource control
    semaphore = asyncio.Semaphore(10)

    async def process_single_request(req_data, req_id):
        async with semaphore:
            try:
                result = await model_manager.predict_with_resilience(
                    req_data.features, req_id
                )
                return PredictionResponse(**result)
            except Exception as e:
                logger.error(f"Batch prediction error for request {req_id}: {e}")
                return {
                    "error": str(e),
                    "request_id": req_id,
                    "timestamp": datetime.utcnow(),
                }

    # Execute batch with proper error handling
    tasks = [
        process_single_request(req, f"batch_{i}") for i, req in enumerate(requests)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {"predictions": results, "total_processed": len(results)}


@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(prometheus_client.generate_latest(), media_type="text/plain")


@app.post("/admin/reload_model")
@require_permission("admin")
async def reload_model(security_context=Depends(verify_token)):
    """Admin endpoint to reload model"""
    try:
        await model_manager._load_model_with_fallback()
        return {"status": "success", "message": "Model reloaded successfully"}
    except Exception as e:
        logger.error(f"Model reload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reload model")


async def log_prediction_async(
    features: Dict, prediction: float, user_id: str, request_id: str
):
    """Asynchronous prediction logging for monitoring"""
    try:
        log_data = {
            "request_id": request_id,
            "user_id": user_id,
            "features": features,
            "prediction": prediction,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Log to monitoring system
        logger.info(f"Prediction logged: {log_data}")

        # Store for drift monitoring
        await security_validator.audit_log(
            "prediction_made",
            user_id,
            {"request_id": request_id, "prediction": prediction},
        )

    except Exception as e:
        logger.error(f"Failed to log prediction: {e}")


if __name__ == "__main__":
    # Production configuration
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    workers = int(os.getenv("API_WORKERS", 1))

    # Run with production settings
    uvicorn.run(
        "src.api.enhanced_main:app",
        host=host,
        port=port,
        workers=workers,
        reload=False,
        access_log=True,
        log_level="info",
    )
