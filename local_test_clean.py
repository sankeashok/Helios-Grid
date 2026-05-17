#!/usr/bin/env python3
"""
Local Test Runner for Helios-Grid Project
Simplified version for local testing without Azure dependencies
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Optional

import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic import Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Simplified Pydantic Models
class PredictionRequest(BaseModel):
    """Simplified request model for local testing"""

    features: Dict[str, float] = Field(..., description="Feature values for prediction")


class PredictionResponse(BaseModel):
    """Simplified response model for local testing"""

    prediction: float
    confidence: float
    model_version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Simplified health check response"""

    status: str
    timestamp: datetime
    version: str
    message: str


class SimpleModelManager:
    """Simplified model manager for local testing"""

    def __init__(self):
        self.model_version = "local_test_v1.0"
        self.is_healthy = True

    def predict(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Simple rule-based prediction for testing"""
        start_time = datetime.utcnow()

        # Simple energy consumption prediction based on features
        base_consumption = 100.0  # Base energy consumption

        # Hour of day effect (peak hours consume more)
        hour = features.get("hour", 12)
        if 8 <= hour <= 10 or 18 <= hour <= 20:  # Peak hours
            hour_factor = 1.5
        elif 22 <= hour <= 6:  # Night hours
            hour_factor = 0.7
        else:
            hour_factor = 1.0

        # Temperature effect
        temperature = features.get("temperature", 20)
        if temperature > 25:  # Hot weather (AC usage)
            temp_factor = 1.3
        elif temperature < 10:  # Cold weather (heating)
            temp_factor = 1.2
        else:
            temp_factor = 1.0

        # Day of week effect
        day_of_week = features.get("day_of_week", 1)
        if day_of_week in [6, 7]:  # Weekend
            day_factor = 0.9
        else:
            day_factor = 1.1

        # Calculate prediction
        prediction = base_consumption * hour_factor * temp_factor * day_factor

        # Add some randomness for realism
        prediction += np.random.normal(0, 5)

        # Ensure positive prediction
        prediction = max(prediction, 10.0)

        # Calculate confidence (higher for typical values)
        confidence = min(0.95, max(0.6, 1.0 - abs(prediction - 100) / 200))

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return {
            "prediction": round(prediction, 2),
            "confidence": round(confidence, 3),
            "model_version": self.model_version,
            "processing_time_ms": round(processing_time, 2),
        }

    def health_check(self) -> bool:
        """Simple health check"""
        return self.is_healthy


# Initialize model manager
model_manager = SimpleModelManager()

# Create FastAPI app
app = FastAPI(
    title="Helios-Grid Local Test API",
    description="Local testing version of the Helios-Grid energy consumption MLOps pipeline",
    version="1.0.0-local",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for UI
try:
    app.mount("/static", StaticFiles(directory="src/ui"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header"""
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds()
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard UI or a simple HTML page"""
    try:
        with open("src/ui/dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback HTML if dashboard.html is not found
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Helios-Grid Local Test</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { text-align: center; margin-bottom: 30px; }
                .logo { font-size: 2.5em; color: #2563eb; margin-bottom: 10px; }
                .status { display: flex; justify-content: space-around; margin: 30px 0; }
                .status-card { text-align: center; padding: 20px; background: #f8fafc; border-radius: 8px; }
                .test-section { margin: 30px 0; padding: 20px; background: #f0f9ff; border-radius: 8px; }
                .btn { background: #2563eb; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
                .btn:hover { background: #1d4ed8; }
                input { padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }
                #result { margin-top: 20px; padding: 15px; background: #ecfdf5; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">☀️ Helios-Grid</div>
                    <h1>Energy Consumption MLOps Pipeline</h1>
                    <p>Local Test Environment</p>
                </div>
                
                <div class="status">
                    <div class="status-card">
                        <h3>API Status</h3>
                        <p id="api-status">🟢 Online</p>
                    </div>
                    <div class="status-card">
                        <h3>Model Version</h3>
                        <p>local_test_v1.0</p>
                    </div>
                    <div class="status-card">
                        <h3>Environment</h3>
                        <p>Local Development</p>
                    </div>
                </div>
                
                <div class="test-section">
                    <h3>🧪 Test Energy Prediction</h3>
                    <p>Enter values to test the energy consumption prediction model:</p>
                    
                    <div>
                        <label>Hour (0-23): </label>
                        <input type="number" id="hour" value="14" min="0" max="23">
                        
                        <label>Temperature (°C): </label>
                        <input type="number" id="temperature" value="22" min="-20" max="50">
                        
                        <label>Day of Week (1-7): </label>
                        <input type="number" id="day_of_week" value="3" min="1" max="7">
                        
                        <button class="btn" onclick="testPrediction()">Predict Energy Consumption</button>
                    </div>
                    
                    <div id="result" style="display: none;"></div>
                </div>
                
                <div class="test-section">
                    <h3>📊 API Endpoints</h3>
                    <ul>
                        <li><a href="/health">Health Check</a></li>
                        <li><a href="/docs">API Documentation (Swagger)</a></li>
                        <li><a href="/redoc">API Documentation (ReDoc)</a></li>
                    </ul>
                </div>
            </div>
            
            <script>
                async function testPrediction() {
                    const hour = document.getElementById('hour').value;
                    const temperature = document.getElementById('temperature').value;
                    const day_of_week = document.getElementById('day_of_week').value;
                    
                    const features = {
                        hour: parseFloat(hour),
                        temperature: parseFloat(temperature),
                        day_of_week: parseFloat(day_of_week)
                    };
                    
                    try {
                        const response = await fetch('/predict', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ features: features })
                        });
                        
                        const result = await response.json();
                        
                        document.getElementById('result').style.display = 'block';
                        document.getElementById('result').innerHTML = `
                            <h4>🔮 Prediction Result</h4>
                            <p><strong>Energy Consumption:</strong> ${result.prediction} kWh</p>
                            <p><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</p>
                            <p><strong>Model Version:</strong> ${result.model_version}</p>
                            <p><strong>Processing Time:</strong> ${result.processing_time_ms}ms</p>
                        `;
                    } catch (error) {
                        document.getElementById('result').style.display = 'block';
                        document.getElementById('result').innerHTML = `
                            <h4>❌ Error</h4>
                            <p>Failed to get prediction: ${error.message}</p>
                        `;
                    }
                }
                
                // Check API status on load
                fetch('/health')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('api-status').innerHTML = `🟢 ${data.status}`;
                    })
                    .catch(error => {
                        document.getElementById('api-status').innerHTML = '🔴 Offline';
                    });
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Simple health check endpoint"""
    is_healthy = model_manager.health_check()

    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        timestamp=datetime.utcnow(),
        version="1.0.0-local",
        message="Helios-Grid local test environment is running",
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Simple prediction endpoint for local testing"""

    try:
        result = model_manager.predict(request.features)
        return PredictionResponse(**result)

    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {
        "message": "Helios-Grid local test API is working!",
        "timestamp": datetime.utcnow(),
        "version": "1.0.0-local",
        "endpoints": {
            "dashboard": "/",
            "health": "/health",
            "predict": "/predict",
            "docs": "/docs",
        },
    }


if __name__ == "__main__":
    print("Starting Helios-Grid Local Test Server...")
    print("Dashboard: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("\nPress Ctrl+C to stop the server")

    uvicorn.run(
        "local_test_clean:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
