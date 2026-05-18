@echo off
echo.
echo ========================================
echo 🚀 Helios-Grid Production MLOps Setup
echo ========================================
echo.

echo 📋 This will set up:
echo    ✅ Production FastAPI server (localhost:3002)
echo    ✅ MLflow experiment tracking (localhost:5000)
echo    ✅ DagsHub integration (optional)
echo    ✅ Public API access for users
echo    ✅ Real-time ML model inference
echo.

pause

echo.
echo 📦 Step 1: Installing production dependencies...
echo ==========================================
pip install -r requirements-production.txt

echo.
echo 📊 Step 2: Installing DagsHub integration (optional)...
echo ====================================================
pip install dagshub

echo.
echo 🤖 Step 3: Training models with MLflow tracking...
echo ===============================================
python mlflow_training.py

echo.
echo 🔧 Step 4: Testing DagsHub integration...
echo ======================================
python dagshub_integration.py

echo.
echo 📊 Step 5: Starting MLflow UI (background process)...
echo =================================================
echo Starting MLflow UI on http://localhost:5000...
start /B mlflow ui --host 0.0.0.0 --port 5000

echo Waiting for MLflow UI to start...
timeout /t 3 /nobreak > nul

echo.
echo 🌐 Step 6: Starting production server...
echo =====================================
echo.
echo 🎉 SUCCESS! Your Helios-Grid MLOps platform is ready!
echo.
echo 📊 Access Points:
echo    🌐 API Server:     http://localhost:3002
echo    📊 MLflow UI:      http://localhost:5000  
echo    📚 API Docs:       http://localhost:3002/docs
echo    🔍 Health Check:   http://localhost:3002/health
echo    📈 DagsHub Status: http://localhost:3002/dagshub/status
echo.
echo 🧪 Test API:
echo    curl -X POST "http://localhost:3002/predict" ^
echo      -H "Content-Type: application/json" ^
echo      -d "{\"temperature\": 25, \"humidity\": 60, \"wind_speed\": 10, \"solar_radiation\": 800, \"hour\": 14, \"day_of_week\": 2, \"month\": 7, \"is_weekend\": 0}"
echo.
echo 🌍 Public Access:
echo    - Local: http://localhost:3002
echo    - Network: http://[YOUR_IP]:3002 (find IP with 'ipconfig')
echo    - Mobile: Connect to same WiFi, use computer's IP
echo.
echo 📊 DagsHub Integration:
echo    - View experiments: https://dagshub.com/sankeashok/Helios-Grid
echo    - Set DAGSHUB_TOKEN environment variable for full integration
echo.
echo ✅ Server starting now... Press Ctrl+C to stop
echo.

python production_server.py