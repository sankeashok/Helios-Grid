"""
Quick test script to verify Helios-Grid production deployment
"""

import requests
import json
import time


def test_production_server():
    """Test the production server endpoints"""

    base_url = "http://localhost:3002"

    print("🧪 Testing Helios-Grid Production Server...")
    print("=" * 50)

    # Test 1: Health Check
    try:
        print("1. Testing health endpoint...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Health: {health_data['status']}")
            print(f"   📊 Model Version: {health_data['model_version']}")
            print(f"   ⏱️ Uptime: {health_data['uptime_seconds']:.1f}s")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        print("   💡 Make sure to run: python production_server.py")
        return False

    # Test 2: Model Info
    try:
        print("\n2. Testing model info endpoint...")
        response = requests.get(f"{base_url}/model/info", timeout=5)
        if response.status_code == 200:
            model_data = response.json()
            print(f"   ✅ Model loaded: {model_data['model_metadata']['type']}")
            print(
                f"   📈 Total predictions: {model_data['api_stats']['total_predictions']}"
            )
            print(
                f"   🔗 MLflow tracking: {model_data['mlflow_info']['dagshub_enabled']}"
            )
        else:
            print(f"   ❌ Model info failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Model info error: {e}")

    # Test 3: Prediction
    try:
        print("\n3. Testing prediction endpoint...")
        test_data = {
            "temperature": 25.5,
            "humidity": 60.0,
            "wind_speed": 8.2,
            "solar_radiation": 750.0,
            "hour": 14,
            "day_of_week": 2,
            "month": 7,
            "is_weekend": 0,
        }

        start_time = time.time()
        response = requests.post(f"{base_url}/predict", json=test_data, timeout=10)
        response_time = (time.time() - start_time) * 1000

        if response.status_code == 200:
            pred_data = response.json()
            print(f"   ✅ Prediction: {pred_data['prediction']:.2f} kWh")
            print(f"   ⚡ Response time: {response_time:.1f}ms")
            print(f"   🎯 Model version: {pred_data['model_version']}")
        else:
            print(f"   ❌ Prediction failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Prediction error: {e}")

    # Test 4: DagsHub Status
    try:
        print("\n4. Testing DagsHub integration...")
        response = requests.get(f"{base_url}/dagshub/status", timeout=5)
        if response.status_code == 200:
            dagshub_data = response.json()
            print(f"   📊 DagsHub status: {dagshub_data['status']}")
            if dagshub_data["status"] == "active":
                print(f"   🔗 Repository: {dagshub_data['repository']}")
                print(f"   📈 Models tracked: {dagshub_data['models_tracked']}")
            else:
                print(f"   💡 Message: {dagshub_data['message']}")
        else:
            print(f"   ❌ DagsHub status failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ DagsHub status error: {e}")

    print("\n🎉 Production server test completed!")
    print("\n📊 Access your MLOps platform:")
    print(f"   🌐 API Server: {base_url}")
    print(f"   📚 API Docs: {base_url}/docs")
    print(f"   📊 MLflow UI: http://localhost:5000")
    print(f"   🔍 Health Check: {base_url}/health")

    return True


if __name__ == "__main__":
    test_production_server()
