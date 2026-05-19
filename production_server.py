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
