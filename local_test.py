#!/usr/bin/env python3
"""
Local Test Runner for Helios-Grid Project
Simplified version for local testing without Azure dependencies
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

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
        # Assume features like hour, temperature, day_of_week, etc.
        
        base_consumption = 100.0  # Base energy consumption
        
        # Hour of day effect (peak hours consume more)
        hour = features.get('hour', 12)
        if 8 <= hour <= 10 or 18 <= hour <= 20:  # Peak hours
            hour_factor = 1.5
        elif 22 <= hour <= 6:  # Night hours
            hour_factor = 0.7
        else:
            hour_factor = 1.0
        
        # Temperature effect
        temperature = features.get('temperature', 20)
        if temperature > 25:  # Hot weather (AC usage)
            temp_factor = 1.3
        elif temperature < 10:  # Cold weather (heating)
            temp_factor = 1.2
        else:
            temp_factor = 1.0
        
        # Day of week effect
        day_of_week = features.get('day_of_week', 1)
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
            'prediction': round(prediction, 2),
            'confidence': round(confidence, 3),
            'model_version': self.model_version,
            'processing_time_ms': round(processing_time, 2)
        }\n    \n    def health_check(self) -> bool:\n        \"\"\"Simple health check\"\"\"\n        return self.is_healthy\n\n# Initialize model manager\nmodel_manager = SimpleModelManager()\n\n# Create FastAPI app\napp = FastAPI(\n    title=\"Helios-Grid Local Test API\",\n    description=\"Local testing version of the Helios-Grid energy consumption MLOps pipeline\",\n    version=\"1.0.0-local\",\n    docs_url=\"/docs\",\n    redoc_url=\"/redoc\"\n)\n\n# Add CORS middleware for local development\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=[\"*\"],  # Allow all origins for local testing\n    allow_credentials=True,\n    allow_methods=[\"*\"],\n    allow_headers=[\"*\"],\n)\n\n# Mount static files for UI\ntry:\n    app.mount(\"/static\", StaticFiles(directory=\"src/ui\"), name=\"static\")\nexcept Exception as e:\n    logger.warning(f\"Could not mount static files: {e}\")\n\n@app.middleware(\"http\")\nasync def add_process_time_header(request: Request, call_next):\n    \"\"\"Add processing time header\"\"\"\n    start_time = datetime.utcnow()\n    response = await call_next(request)\n    process_time = (datetime.utcnow() - start_time).total_seconds()\n    response.headers[\"X-Process-Time\"] = str(process_time)\n    return response\n\n@app.get(\"/\", response_class=HTMLResponse)\nasync def dashboard():\n    \"\"\"Serve the dashboard UI or a simple HTML page\"\"\"\n    try:\n        with open(\"src/ui/dashboard.html\", \"r\", encoding=\"utf-8\") as f:\n            return HTMLResponse(content=f.read())\n    except FileNotFoundError:\n        # Fallback HTML if dashboard.html is not found\n        html_content = \"\"\"\n        <!DOCTYPE html>\n        <html>\n        <head>\n            <title>Helios-Grid Local Test</title>\n            <style>\n                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }\n                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }\n                .header { text-align: center; margin-bottom: 30px; }\n                .logo { font-size: 2.5em; color: #2563eb; margin-bottom: 10px; }\n                .status { display: flex; justify-content: space-around; margin: 30px 0; }\n                .status-card { text-align: center; padding: 20px; background: #f8fafc; border-radius: 8px; }\n                .test-section { margin: 30px 0; padding: 20px; background: #f0f9ff; border-radius: 8px; }\n                .btn { background: #2563eb; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }\n                .btn:hover { background: #1d4ed8; }\n                input { padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 4px; }\n                #result { margin-top: 20px; padding: 15px; background: #ecfdf5; border-radius: 5px; }\n            </style>\n        </head>\n        <body>\n            <div class=\"container\">\n                <div class=\"header\">\n                    <div class=\"logo\">☀️ Helios-Grid</div>\n                    <h1>Energy Consumption MLOps Pipeline</h1>\n                    <p>Local Test Environment</p>\n                </div>\n                \n                <div class=\"status\">\n                    <div class=\"status-card\">\n                        <h3>API Status</h3>\n                        <p id=\"api-status\">🟢 Online</p>\n                    </div>\n                    <div class=\"status-card\">\n                        <h3>Model Version</h3>\n                        <p>local_test_v1.0</p>\n                    </div>\n                    <div class=\"status-card\">\n                        <h3>Environment</h3>\n                        <p>Local Development</p>\n                    </div>\n                </div>\n                \n                <div class=\"test-section\">\n                    <h3>🧪 Test Energy Prediction</h3>\n                    <p>Enter values to test the energy consumption prediction model:</p>\n                    \n                    <div>\n                        <label>Hour (0-23): </label>\n                        <input type=\"number\" id=\"hour\" value=\"14\" min=\"0\" max=\"23\">\n                        \n                        <label>Temperature (°C): </label>\n                        <input type=\"number\" id=\"temperature\" value=\"22\" min=\"-20\" max=\"50\">\n                        \n                        <label>Day of Week (1-7): </label>\n                        <input type=\"number\" id=\"day_of_week\" value=\"3\" min=\"1\" max=\"7\">\n                        \n                        <button class=\"btn\" onclick=\"testPrediction()\">Predict Energy Consumption</button>\n                    </div>\n                    \n                    <div id=\"result\" style=\"display: none;\"></div>\n                </div>\n                \n                <div class=\"test-section\">\n                    <h3>📊 API Endpoints</h3>\n                    <ul>\n                        <li><a href=\"/health\">Health Check</a></li>\n                        <li><a href=\"/docs\">API Documentation (Swagger)</a></li>\n                        <li><a href=\"/redoc\">API Documentation (ReDoc)</a></li>\n                    </ul>\n                </div>\n            </div>\n            \n            <script>\n                async function testPrediction() {\n                    const hour = document.getElementById('hour').value;\n                    const temperature = document.getElementById('temperature').value;\n                    const day_of_week = document.getElementById('day_of_week').value;\n                    \n                    const features = {\n                        hour: parseFloat(hour),\n                        temperature: parseFloat(temperature),\n                        day_of_week: parseFloat(day_of_week)\n                    };\n                    \n                    try {\n                        const response = await fetch('/predict', {\n                            method: 'POST',\n                            headers: {\n                                'Content-Type': 'application/json',\n                            },\n                            body: JSON.stringify({ features: features })\n                        });\n                        \n                        const result = await response.json();\n                        \n                        document.getElementById('result').style.display = 'block';\n                        document.getElementById('result').innerHTML = `\n                            <h4>🔮 Prediction Result</h4>\n                            <p><strong>Energy Consumption:</strong> ${result.prediction} kWh</p>\n                            <p><strong>Confidence:</strong> ${(result.confidence * 100).toFixed(1)}%</p>\n                            <p><strong>Model Version:</strong> ${result.model_version}</p>\n                            <p><strong>Processing Time:</strong> ${result.processing_time_ms}ms</p>\n                        `;\n                    } catch (error) {\n                        document.getElementById('result').style.display = 'block';\n                        document.getElementById('result').innerHTML = `\n                            <h4>❌ Error</h4>\n                            <p>Failed to get prediction: ${error.message}</p>\n                        `;\n                    }\n                }\n                \n                // Check API status on load\n                fetch('/health')\n                    .then(response => response.json())\n                    .then(data => {\n                        document.getElementById('api-status').innerHTML = `🟢 ${data.status}`;\n                    })\n                    .catch(error => {\n                        document.getElementById('api-status').innerHTML = '🔴 Offline';\n                    });\n            </script>\n        </body>\n        </html>\n        \"\"\"\n        return HTMLResponse(content=html_content)\n\n@app.get(\"/health\", response_model=HealthResponse)\nasync def health_check():\n    \"\"\"Simple health check endpoint\"\"\"\n    is_healthy = model_manager.health_check()\n    \n    return HealthResponse(\n        status=\"healthy\" if is_healthy else \"unhealthy\",\n        timestamp=datetime.utcnow(),\n        version=\"1.0.0-local\",\n        message=\"Helios-Grid local test environment is running\"\n    )\n\n@app.post(\"/predict\", response_model=PredictionResponse)\nasync def predict(request: PredictionRequest):\n    \"\"\"Simple prediction endpoint for local testing\"\"\"\n    \n    try:\n        result = model_manager.predict(request.features)\n        return PredictionResponse(**result)\n        \n    except Exception as e:\n        logger.error(f\"Prediction error: {e}\")\n        raise HTTPException(status_code=500, detail=f\"Prediction failed: {str(e)}\")\n\n@app.get(\"/test\")\nasync def test_endpoint():\n    \"\"\"Simple test endpoint\"\"\"\n    return {\n        \"message\": \"Helios-Grid local test API is working!\",\n        \"timestamp\": datetime.utcnow(),\n        \"version\": \"1.0.0-local\",\n        \"endpoints\": {\n            \"dashboard\": \"/\",\n            \"health\": \"/health\",\n            \"predict\": \"/predict\",\n            \"docs\": \"/docs\"\n        }\n    }\n\nif __name__ == \"__main__\":\n    print(\"🚀 Starting Helios-Grid Local Test Server...\")\n    print(\"📊 Dashboard: http://localhost:8000\")\n    print(\"🔍 API Docs: http://localhost:8000/docs\")\n    print(\"❤️ Health Check: http://localhost:8000/health\")\n    print(\"\\n🔥 Press Ctrl+C to stop the server\")\n    \n    uvicorn.run(\n        \"local_test:app\",\n        host=\"127.0.0.1\",\n        port=8000,\n        reload=True,\n        log_level=\"info\"\n    )