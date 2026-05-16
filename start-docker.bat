@echo off
echo Starting Helios-Grid Docker Environment...
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop and make sure it's running
    pause
    exit /b 1
)

echo Docker is available, proceeding with deployment...
echo.

REM Stop any existing containers
echo Stopping existing containers...
docker-compose -f docker-compose.local.yml down

REM Build and start the services
echo Building and starting Helios-Grid services...
docker-compose -f docker-compose.local.yml up --build -d

REM Wait a moment for services to start
echo Waiting for services to initialize...
timeout /t 10 /nobreak >nul

REM Check service status
echo.
echo Checking service status...
docker-compose -f docker-compose.local.yml ps

echo.
echo ========================================
echo Helios-Grid Services are now running!
echo ========================================
echo.
echo Web Interfaces:
echo - Main Dashboard:    http://localhost:8000
echo - API Documentation: http://localhost:8000/docs
echo - MLflow Tracking:   http://localhost:5000
echo - Jupyter Lab:       http://localhost:8888 (token: helios123)
echo - Grafana Dashboard: http://localhost:3000 (admin/helios123)
echo - Prometheus:        http://localhost:9090
echo.
echo To stop all services: docker-compose -f docker-compose.local.yml down
echo To view logs: docker-compose -f docker-compose.local.yml logs -f
echo.
pause