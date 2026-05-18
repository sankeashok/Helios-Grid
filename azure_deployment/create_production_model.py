"""
Helios-Grid Production Model Creation
Creates a production-ready energy prediction model for deployment
"""

import json
import logging
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_production_model():
    """Create a production-ready energy prediction model"""
    
    logger.info("🏗️ Creating Helios-Grid Production Energy Model...")
    
    # Create realistic energy consumption dataset
    np.random.seed(42)
    n_samples = 10000
    
    # Generate realistic energy features
    temperature = np.random.normal(20, 10, n_samples)  # Temperature in Celsius
    humidity = np.random.uniform(30, 90, n_samples)    # Humidity percentage
    wind_speed = np.random.exponential(5, n_samples)   # Wind speed in m/s
    solar_radiation = np.random.uniform(0, 1000, n_samples)  # Solar radiation W/m²
    
    # Time-based features
    hour = np.random.randint(0, 24, n_samples)
    day_of_week = np.random.randint(0, 7, n_samples)
    month = np.random.randint(1, 13, n_samples)
    is_weekend = (day_of_week >= 5).astype(int)
    
    # Create feature matrix
    X = pd.DataFrame({
        'temperature': temperature,
        'humidity': humidity,
        'wind_speed': wind_speed,
        'solar_radiation': solar_radiation,
        'hour': hour,
        'day_of_week': day_of_week,
        'month': month,
        'is_weekend': is_weekend
    })
    
    # Create realistic energy consumption target
    # Energy consumption depends on temperature (heating/cooling), time of day, season
    base_consumption = 1000  # Base load in kWh
    
    # Temperature effect (U-shaped curve - more energy needed for extreme temps)
    temp_effect = 50 * (temperature - 20) ** 2 / 100
    
    # Time of day effect (higher during day, peak in evening)
    hour_effect = 200 * np.sin(np.pi * hour / 12) + 300 * (hour >= 18) * (hour <= 22)
    
    # Seasonal effect (higher in summer and winter)
    seasonal_effect = 100 * np.abs(month - 6.5) / 6.5
    
    # Weekend effect (slightly lower consumption)
    weekend_effect = -50 * is_weekend
    
    # Solar radiation effect (less energy needed when sunny)
    solar_effect = -0.1 * solar_radiation
    
    # Combine all effects with some noise
    y = (base_consumption + temp_effect + hour_effect + seasonal_effect + 
         weekend_effect + solar_effect + np.random.normal(0, 50, n_samples))
    
    # Ensure positive values
    y = np.maximum(y, 100)
    
    logger.info(f"📊 Dataset created: {X.shape[0]} samples, {X.shape[1]} features")
    logger.info(f"📈 Energy consumption range: {y.min():.1f} - {y.max():.1f} kWh")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train production model
    logger.info("🤖 Training production Random Forest model...")
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    
    metrics = {
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
        'mae': mean_absolute_error(y_test, y_pred),
        'r2': r2_score(y_test, y_pred),
        'mape': np.mean(np.abs((y_test - y_pred) / y_test)) * 100
    }
    
    logger.info("📊 Model Performance:")
    logger.info(f"   RMSE: {metrics['rmse']:.2f} kWh")
    logger.info(f"   MAE: {metrics['mae']:.2f} kWh")
    logger.info(f"   R²: {metrics['r2']:.4f}")
    logger.info(f"   MAPE: {metrics['mape']:.2f}%")
    
    # Feature importance
    feature_importance = dict(zip(X.columns, model.feature_importances_))
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    
    logger.info("🎯 Top Feature Importances:")
    for feature, importance in sorted_features[:5]:
        logger.info(f"   {feature}: {importance:.4f}")
    
    # Create model package for deployment
    model_package = {
        "model": model,
        "target_transformer": lambda x: x,  # No transformation for this model
        "inverse_transformer": lambda x: x,
        "feature_names": list(X.columns),
        "model_type": "random_forest",
        "metrics": metrics,
        "feature_importance": feature_importance,
        "training_samples": len(X_train),
        "model_version": "production_v1.0"
    }
    
    # Save model
    os.makedirs("../models", exist_ok=True)
    model_path = "../models/helios_grid_production_model.pkl"
    joblib.dump(model_package, model_path)
    
    logger.info(f"💾 Model saved to: {model_path}")
    
    # Create sample test data
    sample_data = {
        "temperature": 25.5,
        "humidity": 60.0,
        "wind_speed": 8.2,
        "solar_radiation": 750.0,
        "hour": 14,
        "day_of_week": 2,
        "month": 7,
        "is_weekend": 0
    }
    
    # Test prediction
    sample_df = pd.DataFrame([sample_data])
    sample_prediction = model.predict(sample_df)[0]
    
    logger.info(f"🧪 Sample prediction: {sample_prediction:.2f} kWh")
    
    # Save deployment info
    deployment_info = {
        "model_path": model_path,
        "model_version": "production_v1.0",
        "model_type": "random_forest",
        "features": list(X.columns),
        "metrics": metrics,
        "sample_input": sample_data,
        "sample_output": float(sample_prediction),
        "created_date": pd.Timestamp.now().isoformat()
    }
    
    with open("deployment_info.json", "w") as f:
        json.dump(deployment_info, f, indent=2)
    
    logger.info("✅ Production model ready for deployment!")
    return model_path, deployment_info

def test_model_api():
    """Test the model with API-like interface"""
    
    logger.info("🧪 Testing model API interface...")
    
    # Load model
    model_path = "../models/helios_grid_production_model.pkl"
    if not os.path.exists(model_path):
        logger.error("Model not found. Run create_production_model() first.")
        return
    
    model_package = joblib.load(model_path)
    model = model_package["model"]
    
    # Test data (simulating API request)
    test_cases = [
        {
            "name": "Summer Day Peak",
            "data": {
                "temperature": 35.0,
                "humidity": 70.0,
                "wind_speed": 5.0,
                "solar_radiation": 900.0,
                "hour": 19,
                "day_of_week": 2,
                "month": 7,
                "is_weekend": 0
            }
        },
        {
            "name": "Winter Night",
            "data": {
                "temperature": -5.0,
                "humidity": 80.0,
                "wind_speed": 15.0,
                "solar_radiation": 0.0,
                "hour": 2,
                "day_of_week": 6,
                "month": 1,
                "is_weekend": 1
            }
        },
        {
            "name": "Spring Morning",
            "data": {
                "temperature": 15.0,
                "humidity": 55.0,
                "wind_speed": 8.0,
                "solar_radiation": 400.0,
                "hour": 8,
                "day_of_week": 1,
                "month": 4,
                "is_weekend": 0
            }
        }
    ]
    
    logger.info("🎯 Test Results:")
    for test_case in test_cases:
        df = pd.DataFrame([test_case["data"]])
        prediction = model.predict(df)[0]
        logger.info(f"   {test_case['name']}: {prediction:.2f} kWh")
    
    logger.info("✅ Model API testing completed!")

if __name__ == "__main__":
    # Create production model
    model_path, deployment_info = create_production_model()
    
    # Test model API
    test_model_api()
    
    print("\n🎉 Helios-Grid Production Model Ready!")
    print(f"📁 Model Location: {model_path}")
    print(f"📊 Model Performance: R² = {deployment_info['metrics']['r2']:.4f}")
    print(f"🌐 Ready for Azure deployment!")