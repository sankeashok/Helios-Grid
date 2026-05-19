"""
Helios-Grid Cloud Production Server
Optimized for Railway/Render/Heroku deployment
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import uvicorn
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestRegressor
from sklearn.datasets import make_regression
import joblib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
model_store = {}
start_time = time.time()
prediction_count = 0

# Pydantic models
class EnergyPredictionInput(BaseModel):
    temperature: float = Field(..., description="Temperature in Celsius", ge=-50, le=60)
    humidity: float = Field(..., description="Humidity percentage", ge=0, le=100)
    wind_speed: float = Field(..., description="Wind speed in m/s", ge=0, le=50)
    solar_radiation: float = Field(..., description="Solar radiation in W/m²", ge=0, le=1500)
    hour: int = Field(..., description="Hour of day (0-23)", ge=0, le=23)
    day_of_week: int = Field(..., description="Day of week (0=Monday, 6=Sunday)", ge=0, le=6)
    month: int = Field(..., description="Month (1-12)", ge=1, le=12)
    is_weekend: int = Field(..., description="Weekend flag (0=weekday, 1=weekend)", ge=0, le=1)

class PredictionResponse(BaseModel):
    prediction: float
    model_version: str
    timestamp: str
    processing_time_ms: float

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    uptime_seconds: float
    predictions_made: int

def create_production_model():
    """Create and train a production-ready model"""
    logger.info("🏗️ Creating production energy prediction model...")
    
    # Create synthetic training data that mimics real energy consumption patterns
    np.random.seed(42)
    n_samples = 10000
    
    # Generate realistic features
    temperature = np.random.normal(20, 10, n_samples)  # Temperature in Celsius
    humidity = np.random.uniform(30, 90, n_samples)    # Humidity %
    wind_speed = np.random.exponential(8, n_samples)   # Wind speed m/s
    solar_radiation = np.random.uniform(0, 1200, n_samples)  # Solar radiation W/m²
    hour = np.random.randint(0, 24, n_samples)         # Hour of day
    day_of_week = np.random.randint(0, 7, n_samples)   # Day of week
    month = np.random.randint(1, 13, n_samples)        # Month
    is_weekend = (day_of_week >= 5).astype(int)        # Weekend flag
    
    # Create realistic energy consumption based on features
    base_consumption = 2000  # Base load in MW
    
    # Temperature effect (heating/cooling)
    temp_effect = np.where(temperature > 25, (temperature - 25) * 30, 0)  # Cooling
    temp_effect += np.where(temperature < 15, (15 - temperature) * 25, 0)  # Heating
    
    # Time of day effect (peak hours)
    hour_effect = np.where((hour >= 17) & (hour <= 20), 400, 0)  # Evening peak
    hour_effect += np.where((hour >= 8) & (hour <= 10), 200, 0)   # Morning peak
    hour_effect += np.where((hour >= 0) & (hour <= 6), -300, 0)   # Night low
    
    # Weekend effect (lower commercial demand)
    weekend_effect = np.where(is_weekend == 1, -200, 0)
    
    # Seasonal effect
    seasonal_effect = np.where((month >= 6) & (month <= 8), 150, 0)  # Summer AC
    seasonal_effect += np.where((month >= 12) | (month <= 2), 100, 0)  # Winter heating
    
    # Solar effect (more solar = less grid demand during day)
    solar_effect = np.where((hour >= 10) & (hour <= 16), -solar_radiation * 0.1, 0)
    
    # Wind effect (wind power reduces grid demand)
    wind_effect = -wind_speed * 5
    
    # Calculate target consumption
    y = (base_consumption + temp_effect + hour_effect + weekend_effect + 
         seasonal_effect + solar_effect + wind_effect + 
         np.random.normal(0, 50, n_samples))  # Add noise
    
    # Ensure positive values
    y = np.maximum(y, 500)
    
    # Prepare feature matrix
    X = np.column_stack([
        temperature, humidity, wind_speed, solar_radiation,
        hour, day_of_week, month, is_weekend
    ])
    
    # Train Random Forest model
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X, y)
    
    # Calculate model metrics
    train_score = model.score(X, y)
    predictions = model.predict(X)
    rmse = np.sqrt(np.mean((y - predictions) ** 2))
    
    logger.info(f"✅ Model trained - R²: {train_score:.3f}, RMSE: {rmse:.1f} MW")
    
    return {
        "model": model,
        "model_version": "production_v2.0",
        "model_type": "random_forest_optimized",
        "feature_names": [
            "temperature", "humidity", "wind_speed", "solar_radiation",
            "hour", "day_of_week", "month", "is_weekend"
        ],
        "metrics": {
            "r2_score": float(train_score),
            "rmse": float(rmse),
            "training_samples": n_samples
        },
        "created_at": datetime.now().isoformat()
    }

def load_or_create_model():
    """Load existing model or create new one"""
    try:
        # Try to load existing model
        if os.path.exists("production_model.pkl"):
            logger.info("📦 Loading existing model...")
            model_package = joblib.load("production_model.pkl")
        else:
            logger.info("🏗️ No existing model found, creating new one...")
            model_package = create_production_model()
            # Save the model
            joblib.dump(model_package, "production_model.pkl")
            logger.info("💾 Model saved to production_model.pkl")
        
        model_store["model"] = model_package["model"]
        model_store["metadata"] = {
            "version": model_package["model_version"],
            "type": model_package["model_type"],
            "features": model_package["feature_names"],
            "metrics": model_package["metrics"],
            "loaded_at": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Model ready: {model_store['metadata']['type']} v{model_store['metadata']['version']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model loading failed: {e}")
        return False

# Initialize FastAPI app
app = FastAPI(
    title="☀️ Helios-Grid Production Energy API",
    description="Production-ready energy consumption prediction service",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize model on startup"""
    logger.info("🚀 Starting Helios-Grid Production Server...")
    load_or_create_model()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with beautiful API documentation"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>☀️ Helios-Grid Production API</title>
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; min-height: 100vh;
            }}
            .container {{ 
                max-width: 1200px; margin: 0 auto;
                background: rgba(255,255,255,0.1); 
                padding: 40px; border-radius: 20px; 
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .header h1 {{ font-size: 3rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
            .status {{ 
                display: flex; justify-content: center; gap: 30px; 
                margin: 30px 0; flex-wrap: wrap;
            }}
            .status-item {{ 
                background: rgba(255,255,255,0.2); 
                padding: 15px 25px; border-radius: 15px;
                text-align: center; min-width: 120px;
            }}
            .status-value {{ font-size: 1.5rem; font-weight: bold; display: block; }}
            .endpoint {{ 
                background: rgba(255,255,255,0.15); 
                padding: 25px; margin: 20px 0; 
                border-radius: 15px; border-left: 5px solid #ffd700;
            }}
            .method {{ 
                background: #28a745; color: white; 
                padding: 8px 15px; border-radius: 8px; 
                font-weight: bold; display: inline-block; margin-right: 15px;
            }}
            .url {{ 
                font-family: 'Courier New', monospace; 
                background: rgba(0,0,0,0.4); 
                padding: 8px 12px; border-radius: 6px; 
                display: inline-block; margin: 10px 0;
            }}
            .example {{ 
                background: rgba(0,0,0,0.4); 
                padding: 20px; border-radius: 10px; 
                overflow-x: auto; margin: 15px 0;
                font-family: 'Courier New', monospace;
                font-size: 0.9rem; line-height: 1.4;
            }}
            a {{ color: #ffd700; text-decoration: none; font-weight: bold; }}
            a:hover {{ text-decoration: underline; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>☀️ Helios-Grid</h1>
                <p style="font-size: 1.3rem; margin-bottom: 10px;">Production Energy Prediction API</p>
                <p style="opacity: 0.9;">Enterprise-grade ML service for energy consumption forecasting</p>
            </div>
            
            <div class="status">
                <div class="status-item">
                    <span class="status-value">🟢</span>
                    <span>API Status</span>
                </div>
                <div class="status-item">
                    <span class="status-value">{model_store.get('metadata', {}).get('version', 'Loading...')}</span>
                    <span>Model Version</span>
                </div>
                <div class="status-item">
                    <span class="status-value">{prediction_count}</span>
                    <span>Predictions Made</span>
                </div>
                <div class="status-item">
                    <span class="status-value">{int((time.time() - start_time) / 60)}m</span>
                    <span>Uptime</span>
                </div>
            </div>
            
            <div class="grid">
                <div class="endpoint">
                    <h3><span class="method">GET</span> Health Check</h3>
                    <div class="url">/health</div>
                    <p>Check API health, model status, and system metrics</p>
                </div>
                
                <div class="endpoint">
                    <h3><span class="method">POST</span> Energy Prediction</h3>
                    <div class="url">/predict</div>
                    <p>Predict energy consumption based on weather and time parameters</p>
                </div>
                
                <div class="endpoint">
                    <h3><span class="method">GET</span> Model Information</h3>
                    <div class="url">/model/info</div>
                    <p>Get detailed model metrics, features, and performance data</p>
                </div>
            </div>
            
            <div class="endpoint">
                <h3>📚 Interactive Documentation</h3>
                <p>
                    <a href="/docs">🔗 Swagger UI (OpenAPI)</a> | 
                    <a href="/redoc">📖 ReDoc Documentation</a>
                </p>
            </div>
            
            <div class="endpoint">
                <h3>🧪 Example API Call</h3>
                <div class="example">curl -X POST "{os.getenv('RAILWAY_STATIC_URL', 'https://your-app.railway.app')}/predict" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "temperature": 25.5,
    "humidity": 65.0,
    "wind_speed": 12.3,
    "solar_radiation": 800.0,
    "hour": 14,
    "day_of_week": 2,
    "month": 7,
    "is_weekend": 0
  }}'</div>
            </div>
            
            <div style="text-align: center; margin-top: 40px; opacity: 0.8;">
                <p>🚀 Powered by FastAPI + Scikit-learn + Railway</p>
                <p>⚡ Enterprise MLOps Pipeline by Helios-Grid</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check"""
    return HealthResponse(
        status="healthy" if model_store.get("model") else "unhealthy",
        model_loaded=bool(model_store.get("model")),
        model_version=model_store.get("metadata", {}).get("version", "unknown"),
        uptime_seconds=time.time() - start_time,
        predictions_made=prediction_count
    )

@app.post("/predict", response_model=PredictionResponse)
async def predict_energy(input_data: EnergyPredictionInput):
    """Predict energy consumption"""
    global prediction_count
    
    start_time_pred = time.time()
    
    try:
        if not model_store.get("model"):
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Convert input to array
        features = np.array([[
            input_data.temperature,
            input_data.humidity,
            input_data.wind_speed,
            input_data.solar_radiation,
            input_data.hour,
            input_data.day_of_week,
            input_data.month,
            input_data.is_weekend
        ]])
        
        # Make prediction
        model = model_store["model"]
        prediction = float(model.predict(features)[0])
        
        # Ensure positive prediction
        prediction = max(prediction, 100)
        
        processing_time = (time.time() - start_time_pred) * 1000
        prediction_count += 1
        
        return PredictionResponse(
            prediction=round(prediction, 2),
            model_version=model_store["metadata"]["version"],
            timestamp=datetime.now().isoformat(),
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/model/info")
async def get_model_info():
    """Get detailed model information"""
    if not model_store.get("metadata"):
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    uptime = time.time() - start_time
    
    return {
        "model_metadata": model_store["metadata"],
        "api_stats": {
            "total_predictions": prediction_count,
            "uptime_seconds": round(uptime, 2),
            "predictions_per_minute": round(prediction_count / (uptime / 60), 2) if uptime > 0 else 0,
            "avg_response_time_estimate": "< 100ms"
        },
        "deployment_info": {
            "platform": "Railway/Cloud",
            "environment": os.getenv("RAILWAY_ENVIRONMENT", "production"),
            "url": os.getenv("RAILWAY_STATIC_URL", "https://your-app.railway.app")
        }
    }

if __name__ == "__main__":
    # Get port from environment (Railway sets this)
    port = int(os.getenv("PORT", 3002))
    
    logger.info(f"🚀 Starting Helios-Grid Production Server on port {port}")
    
    uvicorn.run(
        "cloud_production_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )