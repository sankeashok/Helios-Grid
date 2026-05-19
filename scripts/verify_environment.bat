@echo off
REM Helios-Grid Environment Verification Script

echo ☀️ Helios-Grid Environment Status Check
echo ========================================

REM Activate virtual environment
call helios-grid-env\Scripts\activate.bat

echo 🔍 Checking Python and core packages...
echo.

REM Check Python version
echo Python Version:
python --version
echo.

REM Check pip version
echo Pip Version:
pip --version
echo.

REM Check installed packages
echo 📦 Core ML Packages Status:
echo.

python -c "
import sys
packages = [
    ('pandas', 'Data manipulation'),
    ('numpy', 'Numerical computing'),
    ('scikit-learn', 'Machine learning'),
    ('xgboost', 'Gradient boosting'),
    ('lightgbm', 'Light gradient boosting'),
    ('fastapi', 'API framework'),
    ('uvicorn', 'ASGI server'),
    ('mlflow', 'ML experiment tracking'),
    ('kagglehub', 'Kaggle data access'),
    ('optuna', 'Hyperparameter optimization'),
    ('pydantic', 'Data validation')
]

print('Package Status:')
print('=' * 50)
for package, description in packages:
    try:
        __import__(package)
        print(f'✅ {package:<15} - {description}')
    except ImportError:
        print(f'❌ {package:<15} - {description} (NOT INSTALLED)')
        
print()
print('🎯 Environment Summary:')
print(f'   Python: {sys.version.split()[0]}')
print(f'   Platform: {sys.platform}')
print(f'   Virtual Env: Active')
"

echo.
echo 🚀 Quick Test Commands:
echo    python run_energy_pipeline.py --help
echo    python -c "import kagglehub; print('Kaggle Hub ready!')"
echo    python -c "import mlflow; print('MLflow ready!')"
echo.

pause