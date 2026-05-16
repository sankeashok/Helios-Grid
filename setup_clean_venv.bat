@echo off
echo ========================================
echo   Helios-Grid Clean Virtual Environment Setup
echo ========================================
echo.

echo 🧹 Setting up clean virtual environment...
echo.

REM Check if virtual environment exists
if not exist "helios-grid-env" (
    echo 🔧 Creating new virtual environment...
    python -m venv helios-grid-env
) else (
    echo ✅ Virtual environment already exists
)

echo.
echo 📦 Installing packages ONLY in virtual environment...
echo.

echo 🔧 Upgrading pip in virtual environment...
helios-grid-env\Scripts\python.exe -m pip install --upgrade pip

echo.
echo 📊 Installing core ML packages in virtual environment...
helios-grid-env\Scripts\pip.exe install pandas numpy scikit-learn

echo.
echo 🚀 Installing API packages in virtual environment...
helios-grid-env\Scripts\pip.exe install fastapi uvicorn pydantic

echo.
echo 🌐 Installing Streamlit packages in virtual environment...
helios-grid-env\Scripts\pip.exe install streamlit plotly

echo.
echo 🤖 Installing ML packages in virtual environment...
helios-grid-env\Scripts\pip.exe install xgboost lightgbm optuna mlflow

echo.
echo 📡 Installing data source packages in virtual environment...
helios-grid-env\Scripts\pip.exe install kagglehub requests

echo.
echo ✅ Installation complete! All packages installed in virtual environment only.
echo.
echo 🔍 Verifying installation...
call check_venv.bat

echo.
echo 🎯 Ready to use! Run: run_streamlit.bat
echo.

pause