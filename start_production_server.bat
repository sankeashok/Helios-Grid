@echo off
echo 🚀 Helios-Grid Production MLOps Server Setup
echo ==========================================

echo.
echo 📦 Installing production dependencies...
pip install -r requirements-production.txt

echo.
echo 🤖 Training models with MLflow tracking...
python mlflow_training.py

echo.
echo 📊 Starting MLflow UI (in background)...
start /B mlflow ui --host 0.0.0.0 --port 5000

echo.
echo 🌐 Starting production server on http://localhost:3002...
echo.
echo 📊 MLflow UI: http://localhost:5000
echo 🌐 API Server: http://localhost:3002
echo 📚 API Docs: http://localhost:3002/docs
echo.
echo ✅ Server is now accessible to users worldwide!
echo.

python production_server.py