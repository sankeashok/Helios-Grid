@echo off
echo ========================================
echo    Helios-Grid Streamlit Deployment
echo ========================================
echo.

echo 🔧 Activating virtual environment...
call helios-grid-env\Scripts\activate.bat

echo 📦 Installing Streamlit requirements in virtual environment...
helios-grid-env\Scripts\pip.exe install -r requirements_streamlit.txt

echo 🚀 Starting Helios-Grid Streamlit App...
echo.
echo 🌐 The app will open in your browser at: http://localhost:8501
echo 🛑 Press Ctrl+C to stop the server
echo.

helios-grid-env\Scripts\streamlit.exe run streamlit_app.py

pause