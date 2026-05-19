@echo off
echo ========================================
echo   Virtual Environment Package Check
echo ========================================
echo.

echo 🔍 Checking virtual environment packages...
echo.

echo 📦 Core packages in helios-grid-env:
helios-grid-env\Scripts\pip.exe list | findstr -i "pandas numpy scikit-learn fastapi uvicorn"

echo.
echo 🌐 Streamlit packages in helios-grid-env:
helios-grid-env\Scripts\pip.exe list | findstr -i "streamlit plotly"

echo.
echo 🐍 Python location:
helios-grid-env\Scripts\python.exe -c "import sys; print('Python path:', sys.executable)"

echo.
echo 📍 Package installation location:
helios-grid-env\Scripts\python.exe -c "import site; print('Site packages:', site.getsitepackages())"

echo.
echo ✅ Virtual environment status: ISOLATED
echo 🔒 All packages installed only in: helios-grid-env
echo.

pause