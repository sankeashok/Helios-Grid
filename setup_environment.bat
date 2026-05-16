@echo off
REM Helios-Grid Environment Setup Script
REM This script activates the virtual environment and installs dependencies

echo ☀️ Helios-Grid Environment Setup
echo ================================

REM Check if virtual environment exists
if not exist "helios-grid-env\Scripts\activate.bat" (
    echo 🔧 Creating virtual environment...
    python -m venv helios-grid-env
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created successfully
) else (
    echo 📁 Virtual environment already exists
)

REM Activate virtual environment
echo 🚀 Activating Helios-Grid environment...
call helios-grid-env\Scripts\activate.bat

REM Upgrade pip
echo 📦 Upgrading pip...
python -m pip install --upgrade pip

REM Install core dependencies
echo 🔧 Installing core dependencies...
pip install wheel setuptools

REM Install project dependencies
echo 📋 Installing Helios-Grid dependencies...
pip install -r requirements.txt

REM Install additional ML and development tools
echo 🤖 Installing additional ML tools...
pip install kagglehub
pip install jupyter
pip install notebook
pip install ipywidgets

REM Install development and testing tools
echo 🧪 Installing development tools...
pip install pytest-cov
pip install black
pip install flake8
pip install mypy
pip install pre-commit

REM Install monitoring and visualization tools
echo 📊 Installing monitoring tools...
pip install streamlit
pip install plotly
pip install seaborn

echo.
echo ✅ Helios-Grid environment setup completed!
echo.
echo 🎯 Environment Details:
python --version
echo 📍 Virtual Environment: %CD%\helios-grid-env
echo.
echo 🚀 To activate this environment in the future, run:
echo    helios-grid-env\Scripts\activate.bat
echo.
echo 💡 Quick Start Commands:
echo    python run_energy_pipeline.py          # Run complete pipeline
echo    python src/api/enhanced_main.py        # Start API server
echo    jupyter notebook                       # Launch Jupyter
echo.
echo ☀️ Helios-Grid is ready for energy analytics!

pause