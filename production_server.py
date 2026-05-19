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
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from src.training.automated_retrain import run_automated_retraining

# Import DagsHub integration
try:
    from src.core.dagshub_integration import HeliosGridDagsHubIntegration

    DAGSHUB_AVAILABLE = True
except ImportError as e:
    DAGSHUB_AVAILABLE = False
    print(f"⚠️ DagsHub integration not available: {e}")

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

# Prometheus Observability Metrics
from prometheus_client import REGISTRY
for metric_name in ["helios_grid_predictions_total", "helios_grid_prediction_latency_milliseconds", "helios_grid_model_accuracy_r2", "helios_grid_model_version", "helios_grid_feature_drift_p_value", "helios_grid_drift_detected", "helios_grid_predicted_energy_consumption_mw"]:
    if metric_name in REGISTRY._names_to_collectors:
        try:
            REGISTRY.unregister(REGISTRY._names_to_collectors[metric_name])
        except KeyError:
            pass

PREDICTION_COUNTER = Counter("helios_grid_predictions_total", "Total predictions made", ["status", "endpoint"])
PREDICTION_LATENCY = Histogram("helios_grid_prediction_latency_milliseconds", "Time spent making predictions")
ACTIVE_MODEL_R2 = Gauge("helios_grid_model_accuracy_r2", "R2 accuracy score of active model")
ACTIVE_MODEL_VERSION = Gauge("helios_grid_model_version", "Active model version sequence")
DRIFT_P_VALUE = Gauge("helios_grid_feature_drift_p_value", "Statistical drift p-value", ["feature"])
DRIFT_DETECTED = Gauge("helios_grid_drift_detected", "Drift status (1 if detected, 0 if stable)")
ENERGY_PREDICTED_GAUGE = Gauge("helios_grid_predicted_energy_consumption_mw", "Predicted energy consumption value")

def log_serving_data(input_dict: dict):
    """Log incoming serving feature payloads to serving_logs.csv (sliding window)"""
    try:
        os.makedirs("data", exist_ok=True)
        serving_path = "data/serving_logs.csv"
        
        # Load existing or create new
        if os.path.exists(serving_path):
            try:
                df = pd.read_csv(serving_path)
            except:
                df = pd.DataFrame(columns=["temperature", "humidity", "wind_speed", "solar_radiation", "hour", "day_of_week", "month", "is_weekend"])
        else:
            df = pd.DataFrame(columns=["temperature", "humidity", "wind_speed", "solar_radiation", "hour", "day_of_week", "month", "is_weekend"])
            
        new_row = pd.DataFrame([input_dict])
        df = pd.concat([df, new_row], ignore_index=True)
        
        # Keep only the last 1000 logs (sliding window to prevent infinite disk space growth)
        if len(df) > 1000:
            df = df.iloc[-1000:]
            
        df.to_csv(serving_path, index=False)
    except Exception as e:
        logger.warning(f"Failed to log serving data: {e}")


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

        # Set Prometheus metrics for active model
        metrics_dict = model_package.get("metrics", {})
        ACTIVE_MODEL_R2.set(float(metrics_dict.get("r2", 0.85)))
        
        # Parse numerical version for Prometheus metric
        version_str = model_store["metadata"]["version"]
        if "demo_" in version_str:
            ACTIVE_MODEL_VERSION.set(1.0)
        elif "retrained_" in version_str:
            try:
                parts = version_str.split("_")
                ACTIVE_MODEL_VERSION.set(float(parts[1] + "." + parts[2]))
            except:
                ACTIVE_MODEL_VERSION.set(2.0)
        else:
            ACTIVE_MODEL_VERSION.set(1.0)

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
    """Root endpoint with React-style prediction UI"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>☀️ Helios-Grid Energy Prediction</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
        <style>
            .gradient-bg {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .glass-card {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .neon-glow {
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
                border: 1px solid rgba(0, 255, 136, 0.5);
            }
            .pulse {
                animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: .5; }
            }
        </style>
    </head>
    <body class="gradient-bg min-h-screen text-white">
        <div class="container mx-auto px-4 py-8">
            <!-- Header -->
            <div class="text-center mb-8">
                <div class="flex items-center justify-center mb-4">
                    <div class="text-6xl animate-spin-slow">☀️</div>
                </div>
                <h1 class="text-5xl font-bold mb-4 bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500 bg-clip-text text-transparent">
                    Helios-Grid
                </h1>
                <p class="text-2xl opacity-90 mb-2">Energy Consumption MLOps Platform</p>
                <p class="text-lg opacity-70 mb-4">Production-grade machine learning for sustainable energy management</p>
                
                <!-- Status Indicators -->
                <div class="flex justify-center space-x-6 mb-6">
                    <div class="flex items-center space-x-2">
                        <div class="w-3 h-3 bg-green-400 rounded-full pulse"></div>
                        <span class="text-sm">API Live</span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <div class="w-3 h-3 bg-blue-400 rounded-full pulse"></div>
                        <span class="text-sm">Model Ready</span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <div class="w-3 h-3 bg-purple-400 rounded-full pulse"></div>
                        <span class="text-sm">MLOps Active</span>
                    </div>
                </div>
            </div>

            <!-- Main Prediction Card -->
            <div class="max-w-4xl mx-auto glass-card rounded-3xl p-8 mb-8">
                <h2 class="text-3xl font-bold mb-8 text-center">⚡ AI Energy Predictor</h2>
                
                <!-- Input Form -->
                <form id="predictionForm" class="space-y-8">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                        <!-- Temperature -->
                        <div class="space-y-4">
                            <label class="block text-lg font-medium">🌡️ Temperature</label>
                            <input type="range" id="temperature" min="-10" max="45" value="25" 
                                   class="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                            <div class="flex justify-between text-sm">
                                <span>-10°C</span>
                                <span id="tempValue" class="font-bold text-xl text-yellow-400">25°C</span>
                                <span>45°C</span>
                            </div>
                        </div>

                        <!-- Humidity -->
                        <div class="space-y-4">
                            <label class="block text-lg font-medium">💧 Humidity</label>
                            <input type="range" id="humidity" min="0" max="100" value="60" 
                                   class="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                            <div class="flex justify-between text-sm">
                                <span>0%</span>
                                <span id="humidityValue" class="font-bold text-xl text-blue-400">60%</span>
                                <span>100%</span>
                            </div>
                        </div>

                        <!-- Wind Speed -->
                        <div class="space-y-4">
                            <label class="block text-lg font-medium">💨 Wind Speed</label>
                            <input type="range" id="windSpeed" min="0" max="50" value="10" 
                                   class="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                            <div class="flex justify-between text-sm">
                                <span>0 m/s</span>
                                <span id="windValue" class="font-bold text-xl text-green-400">10 m/s</span>
                                <span>50 m/s</span>
                            </div>
                        </div>

                        <!-- Solar Radiation -->
                        <div class="space-y-4">
                            <label class="block text-lg font-medium">☀️ Solar Radiation</label>
                            <input type="range" id="solarRadiation" min="0" max="1500" value="750" 
                                   class="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                            <div class="flex justify-between text-sm">
                                <span>0 W/m²</span>
                                <span id="solarValue" class="font-bold text-xl text-orange-400">750 W/m²</span>
                                <span>1500 W/m²</span>
                            </div>
                        </div>

                        <!-- Hour -->
                        <div class="space-y-4">
                            <label class="block text-lg font-medium">🕐 Hour of Day</label>
                            <input type="range" id="hour" min="0" max="23" value="14" 
                                   class="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer">
                            <div class="flex justify-between text-sm">
                                <span>0:00</span>
                                <span id="hourValue" class="font-bold text-xl text-purple-400">14:00</span>
                                <span>23:00</span>
                            </div>
                        </div>

                        <!-- Month -->
                        <div class="space-y-4">
                            <label class="block text-lg font-medium">📅 Month</label>
                            <select id="month" class="w-full p-3 rounded-lg bg-white/20 border border-white/30 text-white">
                                <option value="1">January</option>
                                <option value="2">February</option>
                                <option value="3">March</option>
                                <option value="4">April</option>
                                <option value="5">May</option>
                                <option value="6">June</option>
                                <option value="7" selected>July</option>
                                <option value="8">August</option>
                                <option value="9">September</option>
                                <option value="10">October</option>
                                <option value="11">November</option>
                                <option value="12">December</option>
                            </select>
                        </div>
                    </div>

                    <!-- Day of Week -->
                    <div class="space-y-4">
                        <label class="block text-lg font-medium text-center">📅 Day of Week</label>
                        <div class="grid grid-cols-7 gap-3">
                            <button type="button" class="day-btn p-4 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300 transform hover:scale-105" data-day="0">
                                <div class="text-2xl mb-1">🌅</div>
                                <div class="text-sm">Mon</div>
                            </button>
                            <button type="button" class="day-btn p-4 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300 transform hover:scale-105 neon-glow" data-day="1">
                                <div class="text-2xl mb-1">💼</div>
                                <div class="text-sm">Tue</div>
                            </button>
                            <button type="button" class="day-btn p-4 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300 transform hover:scale-105" data-day="2">
                                <div class="text-2xl mb-1">⚡</div>
                                <div class="text-sm">Wed</div>
                            </button>
                            <button type="button" class="day-btn p-4 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300 transform hover:scale-105" data-day="3">
                                <div class="text-2xl mb-1">🚀</div>
                                <div class="text-sm">Thu</div>
                            </button>
                            <button type="button" class="day-btn p-4 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300 transform hover:scale-105" data-day="4">
                                <div class="text-2xl mb-1">🎉</div>
                                <div class="text-sm">Fri</div>
                            </button>
                            <button type="button" class="day-btn p-4 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300 transform hover:scale-105" data-day="5">
                                <div class="text-2xl mb-1">🏖️</div>
                                <div class="text-sm">Sat</div>
                            </button>
                            <button type="button" class="day-btn p-4 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300 transform hover:scale-105" data-day="6">
                                <div class="text-2xl mb-1">😴</div>
                                <div class="text-sm">Sun</div>
                            </button>
                        </div>
                    </div>

                    <!-- Predict Button -->
                    <div class="text-center">
                        <button type="submit" id="predictBtn" 
                                class="bg-gradient-to-r from-blue-500 via-purple-600 to-pink-500 hover:from-blue-600 hover:via-purple-700 hover:to-pink-600 
                                       text-white font-bold py-6 px-12 rounded-2xl text-xl transition-all duration-300 transform hover:scale-105 shadow-2xl">
                            <span id="btnText">🔮 Predict Energy Consumption</span>
                        </button>
                    </div>
                </form>
            </div>

            <!-- Results -->
            <div id="results" class="hidden max-w-4xl mx-auto">
                <div class="glass-card neon-glow rounded-3xl p-8 text-center">
                    <h3 class="text-3xl font-bold mb-6">🎉 AI Prediction Result</h3>
                    <div id="predictionValue" class="text-6xl font-bold mb-6 bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">
                        0 MW
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 text-lg">
                        <div class="bg-white/10 rounded-2xl p-4">
                            <div class="text-green-400 font-bold text-2xl" id="modelVersion">v1.0</div>
                            <div class="opacity-80">Model Version</div>
                        </div>
                        <div class="bg-white/10 rounded-2xl p-4">
                            <div class="text-blue-400 font-bold text-2xl" id="responseTime">0ms</div>
                            <div class="opacity-80">Response Time</div>
                        </div>
                        <div class="bg-white/10 rounded-2xl p-4">
                            <div class="text-purple-400 font-bold text-2xl" id="timestamp">Now</div>
                            <div class="opacity-80">Timestamp</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="text-center mt-12 opacity-70">
                <p class="text-lg mb-2">Powered by Helios-Grid Enterprise MLOps Pipeline</p>
                <div class="flex justify-center space-x-6 text-sm">
                    <a href="/docs" class="hover:underline hover:text-yellow-400 transition-colors">📚 API Documentation</a>
                    <a href="/health" class="hover:underline hover:text-green-400 transition-colors">🔍 Health Check</a>
                    <a href="/model/info" class="hover:underline hover:text-blue-400 transition-colors">📊 Model Info</a>
                </div>
            </div>
        </div>

        <script>
            let selectedDay = 1; // Tuesday by default

            // Update slider values
            document.getElementById('temperature').addEventListener('input', function() {
                document.getElementById('tempValue').textContent = this.value + '°C';
            });

            document.getElementById('humidity').addEventListener('input', function() {
                document.getElementById('humidityValue').textContent = this.value + '%';
            });

            document.getElementById('windSpeed').addEventListener('input', function() {
                document.getElementById('windValue').textContent = this.value + ' m/s';
            });

            document.getElementById('solarRadiation').addEventListener('input', function() {
                document.getElementById('solarValue').textContent = this.value + ' W/m²';
            });

            document.getElementById('hour').addEventListener('input', function() {
                document.getElementById('hourValue').textContent = this.value + ':00';
            });

            // Day selection
            document.querySelectorAll('.day-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.day-btn').forEach(b => b.classList.remove('neon-glow'));
                    this.classList.add('neon-glow');
                    selectedDay = parseInt(this.dataset.day);
                });
            });

            // Form submission
            document.getElementById('predictionForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const btn = document.getElementById('predictBtn');
                const btnText = document.getElementById('btnText');
                const results = document.getElementById('results');
                
                // Show loading
                btn.disabled = true;
                btnText.textContent = '⏳ AI is analyzing energy patterns...';
                btn.classList.add('animate-pulse');
                
                try {
                    const temperature = parseFloat(document.getElementById('temperature').value);
                    const humidity = parseFloat(document.getElementById('humidity').value);
                    const windSpeed = parseFloat(document.getElementById('windSpeed').value);
                    const solarRadiation = parseFloat(document.getElementById('solarRadiation').value);
                    const hour = parseInt(document.getElementById('hour').value);
                    const month = parseInt(document.getElementById('month').value);
                    const isWeekend = selectedDay >= 5 ? 1 : 0;

                    // Call localhost:3002 API
                    const response = await axios.post('http://localhost:3002/predict', {
                        temperature: temperature,
                        humidity: humidity,
                        wind_speed: windSpeed,
                        solar_radiation: solarRadiation,
                        hour: hour,
                        day_of_week: selectedDay,
                        month: month,
                        is_weekend: isWeekend
                    });

                    // Show results with animation
                    const data = response.data;
                    document.getElementById('predictionValue').textContent = data.prediction.toFixed(1) + ' MW';
                    document.getElementById('modelVersion').textContent = data.model_version || 'v1.0';
                    document.getElementById('responseTime').textContent = data.processing_time_ms.toFixed(1) + 'ms';
                    document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleTimeString();
                    
                    results.classList.remove('hidden');
                    results.scrollIntoView({ behavior: 'smooth' });
                    
                } catch (error) {
                    alert('❌ Prediction failed. Make sure the server is running on localhost:3002');
                    console.error('Error:', error);
                } finally {
                    btn.disabled = false;
                    btnText.textContent = '🔮 Predict Energy Consumption';
                    btn.classList.remove('animate-pulse');
                }
            });
        </script>
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

        # Log to Prometheus Metrics
        PREDICTION_COUNTER.labels(status="success", endpoint="predict").inc()
        PREDICTION_LATENCY.observe(processing_time)
        ENERGY_PREDICTED_GAUGE.set(prediction)

        # Log serving logs & MLflow in background
        background_tasks.add_task(log_serving_data, input_dict)
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
        PREDICTION_COUNTER.labels(status="error", endpoint="predict").inc()
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


class RetrainRequest(BaseModel):
    """Admin retraining request parameters"""
    force: bool = Field(False, description="Force retraining even if drift not detected")
    simulated_drift: bool = Field(False, description="Simulate input drift for demonstration")

@app.post("/admin/retrain")
async def admin_retrain(request: RetrainRequest, background_tasks: BackgroundTasks):
    """Admin trigger for statistical drift analysis and zero-downtime model retraining"""
    
    # Run retraining logic
    logger.info("🛠️ Administrative trigger received for model retraining...")
    
    try:
        # Run retraining synchronously to get immediate output
        retrain_results = run_automated_retraining(
            force=request.force, 
            simulated_drift=request.simulated_drift
        )
        
        # If new champion model is promoted, execute a dynamic zero-downtime hot-reload!
        if retrain_results.get("promoted", False):
            logger.info("🔥 Champion model promoted! Dynamic zero-downtime hot-reloading model...")
            load_model()
            retrain_results["message"] = "Retraining completed successfully. Champion model HOT-RELOADED into serving memory."
            DRIFT_DETECTED.set(1.0 if retrain_results.get("drift_detected", False) else 0.0)
        else:
            DRIFT_DETECTED.set(0.0)

        # Log feature p-values to Prometheus Gauges
        for feature, f_res in retrain_results.get("drift_results", {}).items():
            DRIFT_P_VALUE.labels(feature=feature).set(f_res.get("p_value", 1.0))

        return JSONResponse(content=retrain_results)
        
    except Exception as e:
        logger.error(f"❌ Automated retraining pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

@app.get("/admin", response_class=HTMLResponse)
async def get_admin_portal():
    """Serves the premium, interactive glassmorphism MLOps Control Center Admin Portal"""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Helios-Grid // MLOps Admin Console</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Fira+Code:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0c0d14;
            --surface-color: rgba(20, 22, 37, 0.6);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary-glow: linear-gradient(135deg, #00f2fe, #4facfe);
            --neon-purple: #bd00ff;
            --cyber-green: #00ff87;
            --hazard-red: #ff0055;
            --text-main: #f3f4f6;
            --text-muted: #8e9bb0;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: radial-gradient(circle at 10% 20%, rgba(90, 120, 250, 0.05) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(189, 0, 255, 0.05) 0%, transparent 40%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        header {
            padding: 24px 40px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(12, 13, 20, 0.8);
            backdrop-filter: blur(12px);
            z-index: 100;
            position: sticky;
            top: 0;
        }

        .logo {
            font-weight: 800;
            font-size: 22px;
            letter-spacing: 2px;
            background: linear-gradient(135deg, #00f2fe, #bd00ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .system-badge {
            background: rgba(0, 255, 135, 0.1);
            color: var(--cyber-green);
            border: 1px solid rgba(0, 255, 135, 0.2);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 1px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .main-container {
            flex: 1;
            max-width: 1400px;
            width: 100%;
            margin: 0 auto;
            padding: 40px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }

        @media (max-width: 1024px) {
            .main-container { grid-template-columns: 1fr; }
        }

        .card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(20px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            gap: 20px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .card:hover {
            border-color: rgba(0, 242, 254, 0.25);
            transform: translateY(-2px);
        }

        .card-title {
            font-size: 18px;
            font-weight: 600;
            letter-spacing: 1px;
            display: flex;
            align-items: center;
            gap: 10px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
            text-transform: uppercase;
        }

        .portal-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .portal-item {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            text-decoration: none;
            color: inherit;
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }

        .portal-item::before {
            content: '';
            position: absolute;
            top: 0; left: 0; width: 4px; height: 100%;
            background: var(--primary-glow);
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        .portal-item:hover::before { opacity: 1; }

        .portal-item:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(0, 242, 254, 0.2);
            transform: scale(1.02);
        }

        .portal-name { font-weight: 600; font-size: 16px; display: flex; align-items: center; gap: 8px; }
        .portal-desc { font-size: 13px; color: var(--text-muted); line-height: 1.4; }
        .portal-port { font-family: 'Fira Code', monospace; font-size: 12px; color: #00f2fe; background: rgba(0, 242, 254, 0.08); padding: 2px 6px; border-radius: 4px; width: fit-content; }

        .status-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .status-widget {
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 15px 20px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .widget-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
        .widget-value { font-weight: 800; font-size: 20px; color: var(--text-main); }
        .widget-sub { font-size: 11px; color: var(--text-muted); }

        .form-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            padding: 14px 20px;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.2s ease;
        }

        .form-row:hover { background: rgba(255, 255, 255, 0.04); }

        .checkbox-container {
            position: relative;
            display: flex;
            align-items: center;
        }

        .checkbox-container input { display: none; }
        .checkbox-custom {
            width: 44px;
            height: 24px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            position: relative;
            transition: background 0.3s ease;
        }

        .checkbox-custom::after {
            content: '';
            position: absolute;
            top: 2px; left: 2px;
            width: 20px; height: 20px;
            border-radius: 50%;
            background: #fff;
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .checkbox-container input:checked + .checkbox-custom { background: var(--cyber-green); }
        .checkbox-container input:checked + .checkbox-custom::after { transform: translateX(20px); }

        .btn {
            background: linear-gradient(135deg, #00f2fe, #4facfe);
            border: none;
            border-radius: 12px;
            color: #0b0c10;
            padding: 16px 24px;
            font-weight: 700;
            font-size: 15px;
            letter-spacing: 1px;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 15px rgba(0, 242, 254, 0.3);
            text-transform: uppercase;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 242, 254, 0.5);
        }

        .btn:active { transform: translateY(0); }

        .btn:disabled {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-muted);
            box-shadow: none;
            cursor: not-allowed;
            transform: none;
        }

        .console-container {
            background: #06070a;
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 20px;
            font-family: 'Fira Code', monospace;
            font-size: 13px;
            color: var(--cyber-green);
            min-height: 250px;
            max-height: 350px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
            white-space: pre-wrap;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.8);
        }

        .console-line { line-height: 1.5; }
        .console-system { color: var(--text-muted); }
        .console-info { color: #00f2fe; }
        .console-warn { color: #facc15; }
        .console-error { color: var(--hazard-red); }

        .spinner {
            width: 18px;
            height: 18px;
            border: 3px solid rgba(11, 12, 16, 0.2);
            border-top: 3px solid #0b0c10;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            display: none;
        }

        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <header>
        <div class="logo">
            ☀️ HELIOS-GRID MLOPS CONTROL CENTER
        </div>
        <div class="system-badge">
            <span class="pulse" style="width: 8px; height: 8px; background: var(--cyber-green); border-radius: 50%; display: inline-block; box-shadow: 0 0 8px var(--cyber-green);"></span>
            PRODUCTION ENGINE LIVE
        </div>
    </header>

    <div class="main-container">
        <!-- LEFT: Operations Dashboard -->
        <div class="card">
            <div class="card-title">🔌 Active Portals & Observability</div>
            <div class="portal-grid">
                <a href="http://localhost:3000" target="_blank" class="portal-item">
                    <div class="portal-name">📊 Grafana Dashboard</div>
                    <div class="portal-desc">Real-time prediction rates, feature statistics, system latencies, and drift alerts.</div>
                    <div class="portal-port">Port 3000</div>
                </a>
                <a href="http://localhost:5000" target="_blank" class="portal-item">
                    <div class="portal-name">🔬 MLflow Tracking Workspace</div>
                    <div class="portal-desc">View parameter configurations, metrics validation charts, and registered champion models.</div>
                    <div class="portal-port">Port 5000</div>
                </a>
                <a href="http://localhost:9090" target="_blank" class="portal-item">
                    <div class="portal-name">📡 Prometheus Telemetry Server</div>
                    <div class="portal-desc">Scrapes raw endpoint statistics, request rates, and custom client metric logs.</div>
                    <div class="portal-port">Port 9090</div>
                </a>
                <a href="/metrics" target="_blank" class="portal-item">
                    <div class="portal-name">📃 Live Raw Scraped Metrics</div>
                    <div class="portal-desc">Raw payload format containing standard prometheus client metrics.</div>
                    <div class="portal-port">Port 3002 /metrics</div>
                </a>
            </div>

            <div class="card-title">🤖 Active Production Model Metadata</div>
            <div class="status-grid">
                <div class="status-widget">
                    <div class="widget-label">Champion Version</div>
                    <div id="model-version" class="widget-value">---</div>
                    <div id="model-loaded" class="widget-sub">Loaded: ---</div>
                </div>
                <div class="status-widget">
                    <div class="widget-label">R² Validation Score</div>
                    <div id="model-r2" class="widget-value">---</div>
                    <div class="widget-sub">Random Forest Estimator</div>
                </div>
                <div class="status-widget">
                    <div class="widget-label">Total Serving Queries</div>
                    <div id="serving-queries" class="widget-value">---</div>
                    <div class="widget-sub">Count since startup</div>
                </div>
                <div class="status-widget">
                    <div class="widget-label">Engine Uptime</div>
                    <div id="uptime" class="widget-value">---</div>
                    <div class="widget-sub">System Online Time</div>
                </div>
            </div>
        </div>

        <!-- RIGHT: Interactive Retraining Loop Control -->
        <div class="card">
            <div class="card-title">🔄 Retraining Pipeline Console</div>
            
            <label class="form-row">
                <div>
                    <div style="font-weight:600; font-size:14px; margin-bottom:4px;">Force Pipeline Run</div>
                    <div style="font-size:12px; color:var(--text-muted);">Execute retraining even if features are statistically stable</div>
                </div>
                <div class="checkbox-container">
                    <input type="checkbox" id="force-checkbox">
                    <span class="checkbox-custom"></span>
                </div>
            </label>

            <label class="form-row">
                <div>
                    <div style="font-weight:600; font-size:14px; margin-bottom:4px;">Simulate Climate Data Drift</div>
                    <div style="font-size:12px; color:var(--text-muted);">Deliberately skew temperature and radiation to trigger alert</div>
                </div>
                <div class="checkbox-container">
                    <input type="checkbox" id="drift-checkbox">
                    <span class="checkbox-custom"></span>
                </div>
            </label>

            <button id="retrain-btn" class="btn">
                <span class="spinner" id="btn-spinner"></span>
                🚀 Execute Automated Retraining
            </button>

            <div class="console-container" id="console">
                <div class="console-line console-system">[SYSTEM] Console active. Ready for retraining instructions...</div>
            </div>
        </div>
    </div>

    <script>
        // Fetch active model parameters and stats
        async function fetchSystemStats() {
            try {
                const response = await fetch('/model/info');
                if (!response.ok) throw new Error('API down');
                const data = await response.json();
                
                document.getElementById('model-version').innerText = data.model_metadata.version;
                // Parse loaded time
                const loadedAt = new Date(data.model_metadata.loaded_at).toLocaleTimeString();
                document.getElementById('model-loaded').innerText = `Loaded: ${loadedAt}`;
                
                const r2Val = parseFloat(data.model_metadata.metrics.r2 || 0.85);
                document.getElementById('model-r2').innerText = r2Val.toFixed(4);
                
                document.getElementById('serving-queries').innerText = data.api_stats.total_predictions;
                
                // Uptime format
                const uptimeSec = parseFloat(data.api_stats.uptime_seconds);
                const hrs = Math.floor(uptimeSec / 3600);
                const mins = Math.floor((uptimeSec % 3600) / 60);
                const secs = Math.floor(uptimeSec % 60);
                document.getElementById('uptime').innerText = `${hrs}h ${mins}m ${secs}s`;
                
            } catch (err) {
                console.warn('System status check warning:', err);
            }
        }

        // Trigger stats loop
        setInterval(fetchSystemStats, 2000);
        fetchSystemStats();

        // Console logger
        const consoleEl = document.getElementById('console');
        function log(message, type = 'system') {
            const time = new Date().toLocaleTimeString();
            const line = document.createElement('div');
            line.className = `console-line console-${type}`;
            line.innerText = `[${time}] ${message}`;
            consoleEl.appendChild(line);
            consoleEl.scrollTop = consoleEl.scrollHeight;
        }

        // Trigger retraining request
        document.getElementById('retrain-btn').addEventListener('click', async () => {
            const btn = document.getElementById('retrain-btn');
            const spinner = document.getElementById('btn-spinner');
            const force = document.getElementById('force-checkbox').checked;
            const simulateDrift = document.getElementById('drift-checkbox').checked;

            btn.disabled = true;
            spinner.style.display = 'inline-block';
            
            log(`Triggering automated MLOps retraining request... (force=${force}, simulated_drift=${simulateDrift})`, 'info');
            log(`Invoking Kolmogorov-Smirnov statistical calculations...`, 'info');

            try {
                const response = await fetch('/admin/retrain', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ force: force, simulated_drift: simulateDrift })
                });

                const data = await response.json();
                
                if (data.status === 'success' || data.status === 'skipped') {
                    if (data.drift_detected) {
                        log(`🚨 STATISTICAL DATA DRIFT DETECTED IN ROLLING SERVING LOGS!`, 'error');
                        // Show drift parameters
                        for (const [feat, res] of Object.entries(data.drift_results)) {
                            if (res.drift_detected) {
                                log(`   ➔ Feature [${feat}]: Drift detected (p-value = ${res.p_value.toFixed(6)})`, 'error');
                            } else {
                                log(`   ➔ Feature [${feat}]: Stable (p-value = ${res.p_value.toFixed(4)})`, 'system');
                            }
                        }
                    } else {
                        log(`✅ Kolmogorov-Smirnov test complete. Serving feature distributions stable.`, 'system');
                    }

                    if (data.promoted) {
                        log(`🔥 Champion model promoted!`, 'info');
                        log(`   ➔ R² Accuracy: ${data.candidate_metrics.r2.toFixed(4)}`, 'info');
                        log(`   ➔ RMSE: ${data.candidate_metrics.rmse.toFixed(2)}`, 'info');
                        log(`💥 dynamic in-memory Zero-Downtime model hot-reload complete!`, 'info');
                    } else {
                        log(`😴 Skipping model promotion. Candidate model rejected (validation performance is inferior).`, 'warn');
                    }
                    
                    log(`Pipeline run completed successfully in ${data.execution_time_seconds ? data.execution_time_seconds.toFixed(2) : 2.5}s.`, 'system');
                } else {
                    log(`❌ Pipeline execution failed: ${data.message}`, 'error');
                }

            } catch (err) {
                log(`❌ Administrative API request failed: ${err.message}`, 'error');
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
                fetchSystemStats();
            }
        });
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint utilizing prometheus-client registry"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
